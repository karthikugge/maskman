import psycopg2
import urllib.parse
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())
from backend.config import settings

def run_direct_migration():
    print("🚀 Running DIRECT Schema Migration...")
    try:
        db_url = settings.DATABASE_URL
        parsed = urllib.parse.urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            database=parsed.path[1:],
            user=parsed.username,
            password=urllib.parse.unquote(parsed.password),
            port=parsed.port or 6543,
            sslmode='require'
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        commands = [
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS image_gallery TEXT[] DEFAULT '{}';",
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS lowest_price_all_time NUMERIC(12,2);",
            "ALTER TABLE public.price_history ADD COLUMN IF NOT EXISTS discounted_price NUMERIC(12,2);"
        ]
        
        for cmd in commands:
            try:
                cur.execute(cmd)
                print(f"✅ Success: {cmd[:50]}...")
            except Exception as e:
                print(f"⚠️ Warning: {cmd[:50]}... failed: {e}")
                
        cur.close()
        conn.close()
        print("🏁 Migration completed.")
    except Exception as e:
        print(f"🔥 Critical Failure: {e}")

if __name__ == "__main__":
    run_direct_migration()
