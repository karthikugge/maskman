import os
import sys
import asyncio

sys.path.append(os.getcwd())

from backend.supabase_lib import supabase
from backend.scripts.price_history import seed_history

def reseed_all_history():
    print("--- Deleting ALL existing price history ---")
    
    # We delete by simply fetching products and deleting their history, or deleting all rows.
    # Supabase might not allow bulk delete without a filter, so we filter by product_id not null
    supabase.table("price_history").delete().neq("product_id", "00000000-0000-0000-0000-000000000000").execute()
    print("Deleted all price history.")

    print("--- Reseeding price history for all success products ---")
    p_res = supabase.table("products").select("id, name").eq("scrape_status", "success").execute()
    products = p_res.data
    
    print(f"Found {len(products)} products to reseed.")
    
    for p in products:
        try:
            seed_history(p["id"], points=6) # 6 points is a good realistic curve length
            print(f"  ✓ Reseeded {p['name'][:30]}")
        except Exception as e:
            print(f"  x Failed for {p['id']}: {e}")
            
    print("Done!")

if __name__ == "__main__":
    reseed_all_history()
