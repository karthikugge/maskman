import os
import sys
import datetime
from uuid import UUID

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.supabase_lib import supabase

def seed_comparison(product_id):
    """Seed fake external price comparisons for a product."""
    print(f"--- Seeding External Comparisons for {product_id} ---")
    
    # 1. Fetch product
    p_res = supabase.table("products").select("name").eq("id", product_id).execute()
    if not p_res.data:
        print("Product not found.")
        return
    
    name = p_res.data[0]["name"]
    print(f"Product: {name}")

    # 2. Fake competitors
    competitors = [
        {
            "product_id": product_id,
            "competitor_url": "https://www.amazon.in/dp/B00EXAMPLE1",
            "competitor_name": "Amazon",
            "competitor_price": 4999.00,
            "competitor_image_url": "https://m.media-amazon.com/images/I/example.jpg",
            "similarity_score": 0.95,
            "last_updated": datetime.datetime.now().isoformat()
        },
        {
            "product_id": product_id,
            "competitor_url": "https://www.flipkart.com/example-shoe/p/itmexample2",
            "competitor_name": "Flipkart",
            "competitor_price": 5299.00,
            "competitor_image_url": "https://rukminim1.flixcart.com/image/example.jpg",
            "similarity_score": 0.88,
            "last_updated": datetime.datetime.now().isoformat()
        }
    ]

    # 3. Upsert
    for c in competitors:
        try:
            supabase.table("product_comparisons").upsert(c).execute()
            print(f"Seeded {c['competitor_name']} match.")
        except Exception as e:
            print(f"Failed to seed {c['competitor_name']}: {e}")
            print("TIP: Ensure you have run the SQL to create the 'product_comparisons' table first!")

def main():
    if len(sys.argv) < 2:
        print("Usage: python comparison_seed.py <product_id>")
        return
    
    pid = sys.argv[1]
    seed_comparison(pid)

if __name__ == "__main__":
    main()
