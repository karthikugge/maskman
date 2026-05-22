import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
sys.path.append(os.getcwd())

from backend.config import settings

async def run_migration():
    print(f"Starting Database Migration to support PDP...")
    
    # Ensure the URL is compatible with asyncpg
    db_url = settings.DATABASE_URL
    if "postgresql://" in db_url and "postgresql+asyncpg://" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"Connecting to database...")
    engine = create_async_engine(db_url)
    
    sql_commands = [
        "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS image_gallery TEXT[] DEFAULT '{}';",
        "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS lowest_price_all_time NUMERIC(12,2);"
    ]
    
    try:
        async with engine.begin() as conn:
            for cmd in sql_commands:
                print(f"  Executing: {cmd}")
                await conn.execute(text(cmd))
        print("Migration Successful!")
    except Exception as e:
        print(f"Migration Failed: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
