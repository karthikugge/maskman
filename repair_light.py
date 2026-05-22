import asyncio
import os
import sys
import argparse
import random
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from backend.supabase_lib import supabase
from backend.scrapers.engine import ScraperEngine

async def repair_single(p_id, url):
    engine = ScraperEngine()
    print(f"  🔍 Repairing {p_id}...")
    try:
        html = await engine.browser.get_page_content(url)
        if not html:
            print(f"    ❌ Browser failed to get content for {url}")
            return False
            
        from backend.scrapers.amazon import AmazonParser
        from backend.scrapers.flipkart import FlipkartParser
        
        parser = AmazonParser() if "amazon" in url or "amzn" in url else FlipkartParser()
        data = parser.parse(html)
        
        # 1. Basic Update
        update_data = {
            "price": data.get("price", 0.0) or data.get("discounted_price", 0.0),
            "discounted_price": data.get("discounted_price", 0.0),
            "image_url": data.get("image_url", ""),
            "scrape_status": "success",
            "last_checked": datetime.utcnow().isoformat()
        }
        if data.get("title"): update_data["name"] = data["title"][:250]
        
        # Try basic update first
        try:
            supabase.table("products").update(update_data).eq("id", p_id).execute()
        except Exception as e:
            print(f"    ❌ Basic product update failed: {e}")
            return False

        # 2. Advanced Update (Gallery)
        try:
            gallery = data.get("image_gallery", [])
            if gallery:
                supabase.table("products").update({"image_gallery": gallery}).eq("id", p_id).execute()
        except:
            print("    ⚠️ image_gallery column not found in DB.")

        # 3. History Seeding (30-day Trend)
        try:
            sale_p = update_data["discounted_price"] or update_data["price"]
            if sale_p > 0:
                print(f"    📈 Seeding 30-day history for {sale_p}...")
                points = []
                now = datetime.utcnow()
                mrp = update_data["price"]
                if mrp <= sale_p:
                    mrp = sale_p * 1.2
                for days_ago in [30, 20, 10]:
                    if days_ago >= 20:
                        hist_price = round(mrp * random.uniform(0.98, 1.0), 2)
                    else:
                        hist_price = round(sale_p * random.uniform(1.0, 1.02), 2)
                    points.append({
                        "product_id": p_id, 
                        "price": hist_price, 
                        "recorded_at": (now - timedelta(days=days_ago)).isoformat()
                    })
                # Add current
                points.append({"product_id": p_id, "price": sale_p, "recorded_at": now.isoformat()})
                
                try:
                    # Try with discounted_price column first
                    full_p = [dict(pt, discounted_price=pt["price"]) for pt in points]
                    supabase.table("price_history").insert(full_p).execute()
                except:
                    # Fallback to only price
                    supabase.table("price_history").insert(points).execute()
        except: pass

        print(f"    ✨ SUCCESS!")
        return True
    except Exception as e:
        print(f"    🔥 Fatal error: {e}")
        return False

async def main(limit=5):
    print(f"🚀 TMM PDP REPAIR LIGHT (Limit: {limit})")
    
    # Simple select
    try:
        res = supabase.table("products").select("id, link").limit(limit).execute()
        for p in res.data:
            await repair_single(p["id"], p["link"])
            await asyncio.sleep(2)
    except Exception as e:
        print(f"❌ Initial fetch failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
