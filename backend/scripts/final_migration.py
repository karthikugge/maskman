import psycopg2
import os
import sys
import urllib.parse

# Add project root to path
sys.path.append(os.getcwd())

from backend.config import settings

def run_migration_psycopg2_direct():
    print(f"Starting Final Migration Attempt (psycopg2 direct)...")
    
    db_url = settings.DATABASE_URL
    parsed = urllib.parse.urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    
    # Try Port 5432 on the same host
    host = parsed.hostname
    user = parsed.username
    password = urllib.parse.unquote(parsed.password)
    dbname = parsed.path[1:]
    
    print(f"User: {user}")
    print(f"Host: {host}")
    print(f"DB: {dbname}")
    
    # Port 5432 (Standard Postgres)
    try:
        print(f"Attempting Port 5432 (SSL Require)...")
        conn = psycopg2.connect(
            host=host,
            database=dbname,
            user=user,
            password=password,
            port=5432,
            sslmode='require'
        )
        print("Connected on 5432!")
    except Exception as e5432:
        print(f"5432 Failed: {e5432}")
        print(f"Attempting Port 6543 (Pooler) with fallback params...")
        try:
            # For pooler, sometimes user needs project id prefix, which we have (postgres.qgetnkxrpzw...)
            conn = psycopg2.connect(
                host=host,
                database=dbname,
                user=user,
                password=password,
                port=6543,
                sslmode='require'
            )
            print("Connected on 6543!")
        except Exception as e6543:
            print(f"6543 Failed: {e6543}")
            return

    try:
        conn.autocommit = True
        cur = conn.cursor()
        
        commands = [
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS image_gallery TEXT[] DEFAULT '{}';",
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS lowest_price_all_time NUMERIC(12,2);"
        ]
        
        for cmd in commands:
            print(f"Executing: {cmd}")
            cur.execute(cmd)
            
        print("MIGRATION SUCCESSFUL!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Execution Error: {e}")

if __name__ == "__main__":
    run_migration_psycopg2_direct()
