import os
import sys
import datetime
import random
from uuid import UUID

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.supabase_lib import supabase

def is_valid_uuid(val):
    try:
        UUID(str(val))
        return True
    except ValueError:
        return False

def seed_history(product_id, points=10):
    """Generate fake price history for testing."""
    print(f"--- Seeding Price History for {product_id} ---")
    
    # 1. Fetch current price
    p_res = supabase.table("products").select("name, price, discounted_price").eq("id", product_id).execute()
    if not p_res.data:
        print("Product not found.")
        return
    
    source = p_res.data[0]
    base_price = float(source.get("price") or 1000)
    current_sale = float(source.get("discounted_price") or base_price * 0.9)
    
    print(f"Product: {source['name']}")
    
    # Clear old history for this product
    supabase.table("price_history").delete().eq("product_id", product_id).execute()
    
    # Generate points
    history_data = []
    now = datetime.datetime.now()
    
    for i in range(points):
        # Go back in time
        days_ago = (points - i - 1) * 3
        date = now - datetime.timedelta(days=days_ago)
        
        # Realistic pattern: older points at MRP, recent points at sale price
        if i < points // 2:
            base = base_price
            noise = random.uniform(0.98, 1.0)
        else:
            base = current_sale if current_sale else base_price
            noise = random.uniform(1.0, 1.02)
            
        hist_price = base * noise
        hist_sale = current_sale * noise if current_sale else None
        
        history_data.append({
            "product_id": product_id,
            "price": round(hist_price, 2),
            "discounted_price": round(hist_sale, 2) if hist_sale else None,
            "recorded_at": date.isoformat()
        })
    
    # Insert
    res = supabase.table("price_history").insert(history_data).execute()
    print(f"Sucessfully seeded {len(res.data)} price points.")

def backfill_all():
    """Initial price point for all products without history."""
    print("--- Backfilling Price History for all products ---")
    prods = supabase.table("products").select("id, price, discounted_price, scrape_status").execute()
    
    count = 0
    for p in prods.data:
        if p["scrape_status"] != 'success': continue
        
        # Check if history exists
        h_res = supabase.table("price_history").select("id", count="exact").eq("product_id", p["id"]).execute()
        if h_res.count == 0:
            supabase.table("price_history").insert({
                "product_id": p["id"],
                "price": p["price"],
                "discounted_price": p["discounted_price"],
                "recorded_at": datetime.datetime.now().isoformat()
            }).execute()
            count += 1
            
    print(f"Created initial history point for {count} products.")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python price_history.py seed <product_id> [points]")
        print("  python price_history.py backfill")
        return

    cmd = sys.argv[1]
    if cmd == "seed":
        if len(sys.argv) < 3:
            print("Error: Missing product_id")
            return
        pid = sys.argv[2]
        pts = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        seed_history(pid, pts)
    elif cmd == "backfill":
        backfill_all()
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
