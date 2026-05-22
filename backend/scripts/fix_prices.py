import asyncio
import os
import sys
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from backend.supabase_lib import supabase
from backend.scraper import scrape_product_data
from backend.scrapers.engine import ScraperEngine

class PriceFixer:
    def __init__(self):
        self.engine = ScraperEngine()

    async def log_activity(self, action, target, details):
        try:
            supabase.table("admin_activity_logs").insert({
                "action_type": action,
                "target_name": target,
                "details": details
            }).execute()
        except: pass

    async def fix_prices(self, limit=50, concurrent=3, force_browser=False):
        print(f"\n💰 TMM PRICE REPAIR START (Limit: {limit}, Force Browser: {force_browser})")
        
        # 1. Fetch suspicious products
        # Logic: Price == 0 OR Sale == 0 OR (Price == Sale AND store is Amazon/Flipkart)
        # We'll just fetch all where Price == Sale or Price/Sale is 0
        query = supabase.table("products").select("id, link, name, price, discounted_price")
        query = query.or_("price.eq.0,discounted_price.eq.0,price.eq.discounted_price")
        
        res = query.order("created_at", desc=True).limit(limit).execute()
        products = res.data
        
        if not products:
            print("✅ No suspicious prices found.")
            return

        print(f"📦 Found {len(products)} products with potential price issues.")
        stats = {"fixed": 0, "verified": 0, "failed": 0}
        sem = asyncio.Semaphore(concurrent)

        async def process_one(p):
            async with sem:
                p_id = p["id"]
                url = p["link"]
                old_p = p.get("price")
                old_s = p.get("discounted_price")
                
                print(f"  🔍 Checking: {p['name'][:30]}... (Current: ₹{old_s}/₹{old_p})")
                
                try:
                    # If force_browser is set, we bypass the generic scraper and use BrowserEngine directly
                    if force_browser:
                        data = await self.engine.browser.get_page_content(url)
                        # We need to parse it
                        parser = self.engine._get_parser(url)
                        if parser:
                            result = parser.parse(data)
                        else:
                            result = {"price": 0, "discounted_price": 0}
                    else:
                        result = await scrape_product_data(url)

                    if not result or (result.get("price", 0) == 0 and result.get("discounted_price", 0) == 0):
                        print(f"  ❌ Scrape failed for {p_id}")
                        stats["failed"] += 1
                        return

                    new_p = result.get("price", 0)
                    new_s = result.get("discounted_price", 0)

                    # Update only if we got better data or it's verified same
                    changed = (new_p != old_p or new_s != old_s) and (new_p > 0 or new_s > 0)
                    
                    if changed:
                        update_data = {
                            "price": new_p,
                            "discounted_price": new_s,
                            "scrape_status": "success",
                            "last_checked": datetime.now().isoformat()
                        }
                        # Also update name/img if they were missing
                        if result.get("title"): update_data["name"] = result["title"][:250]
                        if result.get("image_url"): update_data["image_url"] = result["image_url"]

                        supabase.table("products").update(update_data).eq("id", p_id).execute()
                        stats["fixed"] += 1
                        print(f"  ✨ FIXED: ₹{new_s} (MRP: ₹{new_p})")
                    else:
                        stats["verified"] += 1
                        print(f"  ✔ Verified correct (or no change found).")

                except Exception as e:
                    print(f"  🔥 Error: {e}")
                    stats["failed"] += 1

        await asyncio.gather(*[process_one(p) for p in products])
        
        summary = f"Price Repair Finished. Fixed: {stats['fixed']}, Verified: {stats['verified']}, Failed: {stats['failed']}"
        print(f"\n🏁 {summary}")
        await self.log_activity("PRICE_REPAIR", "Bulk Fix", summary)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TMM Price Repair Tool")
    parser.add_argument("--limit", type=int, default=20, help="Max products")
    parser.add_argument("--concurrent", type=int, default=3, help="Parallel scrapers")
    parser.add_argument("--force-browser", action="store_true", help="Always use Playwright")
    
    args = parser.parse_args()
    
    fixer = PriceFixer()
    asyncio.run(fixer.fix_prices(limit=args.limit, concurrent=args.concurrent, force_browser=args.force_browser))
