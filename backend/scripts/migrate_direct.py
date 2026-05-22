import asyncio
import asyncpg
import ssl
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from backend.config import settings

async def run_migration_direct():
    print(f"Starting Direct Database Migration (asyncpg)...", flush=True)
    
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to Supabase (SSL Verify: False)...", flush=True)
    try:
        # Create an SSL context that doesn't verify
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        # Connect with SSL context
        conn = await asyncio.wait_for(asyncpg.connect(db_url, ssl=ssl_ctx), timeout=30.0)
        print("Connected!", flush=True)
        
        sql_commands = [
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS image_gallery TEXT[] DEFAULT '{}';",
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS lowest_price_all_time NUMERIC(12,2);"
        ]
        
        for cmd in sql_commands:
            print(f"  Executing: {cmd}", flush=True)
            await conn.execute(cmd)
            
        print("Migration Successful!", flush=True)
        await conn.close()
    except asyncio.TimeoutError:
        print("Error: Connection timed out.", flush=True)
    except Exception as e:
        print(f"Direct Migration Failed: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(run_migration_direct())
