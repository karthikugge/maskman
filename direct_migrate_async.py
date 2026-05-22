import asyncio
import asyncpg
import os
import sys

sys.path.append(os.getcwd())
from backend.config import settings

async def run_async_migration():
    print("🚀 Running Schema UPDATE via Port 5432...")
    try:
        db_url = settings.DATABASE_URL
        url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Replace 6543 with 5432 for session pooler / direct connection to avoid PgBouncer auth issues
        url = url.replace(":6543/", ":5432/")
        
        print(f"Connecting to: {url.split('@')[1]}")
        
        conn = await asyncpg.connect(url)
        
        commands = [
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS image_gallery TEXT[] DEFAULT '{}';",
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS lowest_price_all_time NUMERIC(12,2);",
            "ALTER TABLE public.price_history ADD COLUMN IF NOT EXISTS discounted_price NUMERIC(12,2);"
        ]
        
        for cmd in commands:
            try:
                await conn.execute(cmd)
                print(f"✅ Success: {cmd[:50]}...")
            except Exception as e:
                print(f"⚠️ Error on {cmd[:50]}: {e}")
                
        await conn.close()
        print("🏁 Schema Update completed.")
    except Exception as e:
        print(f"🔥 Critical Failure: {e}")

if __name__ == "__main__":
    asyncio.run(run_async_migration())
