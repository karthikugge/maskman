import asyncio
import sys
import os
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.getcwd())

from backend.supabase_lib import supabase
from backend.scraper import scrape_product_data

async def fix_products(mode="missing", limit=50):
    """
    Modes:
    - missing: Only products with scrape_status != 'success'
    - refresh: All products (to update prices/images)
    """
    print(f"--- TMM Product Fixer Start (Mode: {mode}) ---")
    
    # 1. Fetch targeted products
    query = supabase.table("products").select("id, link, name")
    
    if mode == "missing":
        query = query.neq("scrape_status", "success")
    
    res = query.limit(limit).execute()
    products = res.data
    
    if not products:
        print("No products found needing fixes.")
        return

    print(f"Found {len(products)} products to process.")

    # 2. Process with concurrency limit (semaphore)
    sem = asyncio.Semaphore(3) # Max 3 concurrent scrapers to avoid bot blocks

    async def process_one(p):
        async with sem:
            p_id = p["id"]
            url = p["link"]
            print(f"[{p_id}] Scraping: {url}")
            
            data = await scrape_product_data(url)
            
            # Determine status
            # If price > 0, we consider it a success
            status = "success" if data.get("price", 0) > 0 or data.get("discounted_price", 0) > 0 else "failed"
            
            update_data = {
                "name": data.get("title", p.get("name", "Unknown Product")),
                "description": data.get("description", ""),
                "image_url": data.get("image_url", ""),
                "price": data.get("price"),
                "discounted_price": data.get("discounted_price"),
                "scrape_status": status,
                "last_checked": datetime.now().isoformat()
            }
            
            try:
                supabase.table("products").update(update_data).eq("id", p_id).execute()
                print(f"[{p_id}] Done. Status: {status}")
            except Exception as e:
                print(f"[{p_id}] Update failed: {e}")

    # Run tasks
    tasks = [process_one(p) for p in products]
    await asyncio.gather(*tasks)
    
    print("--- TMM Product Fixer Finished ---")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix or refresh product data.")
    parser.add_argument("--mode", choices=["missing", "refresh"], default="missing", help="missing (pending/failed) or refresh (all)")
    parser.add_argument("--limit", type=int, default=10, help="Max products to process")
    
    args = parser.parse_args()
    
    asyncio.run(fix_products(mode=args.mode, limit=args.limit))
