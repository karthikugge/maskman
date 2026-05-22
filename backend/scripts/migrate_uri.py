import psycopg2
import os
import sys
import urllib.parse

# Add project root to path
sys.path.append(os.getcwd())

from backend.config import settings

def run_migration_uri():
    print(f"Starting URI-based Migration Attempt...")
    
    # Use the EXACT URI from .env but ensure it's psycopg2 compatible
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Add sslmode=require if not present
    if "sslmode=" not in db_url:
        if "?" in db_url:
            db_url += "&sslmode=require"
        else:
            db_url += "?sslmode=require"

    print(f"Attempting connection with full URI (masked password)...")
    # Mask password for logs
    # format: postgresql://user:password@host:port/dbname
    try:
        conn = psycopg2.connect(db_url)
        print("CONNECTED SUCCESSFULY!")
        
        conn.autocommit = True
        cur = conn.cursor()
        
        commands = [
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS image_gallery TEXT[] DEFAULT '{}';",
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS lowest_price_all_time NUMERIC(12,2);"
        ]
        
        for cmd in commands:
            print(f"Executing: {cmd}")
            cur.execute(cmd)
            
        print("MIGRATION FINISHED SUCCESSFULLY!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"URI Connection Failed: {e}")

if __name__ == "__main__":
    run_migration_uri()
