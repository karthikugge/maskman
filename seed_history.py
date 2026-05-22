import asyncio
import os
import random
import datetime
from supabase import create_client
from dotenv import load_dotenv

async def seed_history():
    load_dotenv()
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    supabase = create_client(url, key)
    
    # Get a few products to seed
    res = supabase.table("products").select("id, discounted_price").limit(5).execute()
    products = res.data
    
    if not products:
        print("No products found to seed history.")
        return
        
    for p in products:
        pid = p["id"]
        base_price = float(p["discounted_price"] or 1000)
        
        print(f"Seeding history for product {pid}...")
        
        # Add 10 historical points
        history_data = []
        for i in range(10):
            # Price varies slightly over the last 10 days
            variation = random.uniform(-0.1, 0.1)
            hist_price = base_price * (1 + variation)
            date = (datetime.datetime.now() - datetime.timedelta(days=10-i)).isoformat()
            
            history_data.append({
                "product_id": pid,
                "price": round(hist_price, 2),
                "recorded_at": date
            })
            
        # Clear old history first to ensure a clean graph for testing
        supabase.table("price_history").delete().eq("product_id", pid).execute()
        
        # Insert new history
        supabase.table("price_history").insert(history_data).execute()
        
    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_history())
