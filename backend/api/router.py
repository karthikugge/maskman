from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config import settings
import httpx
import re
import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel
import math
import uuid

def is_valid_uuid(val: str):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

from backend.supabase_lib import supabase
from backend.api.security import get_current_user

router = APIRouter()

async def log_admin_activity(admin_id: str, action_type: str, target_name: str = None, details: str = None):
    """Utility to log admin actions to the registry."""
    try:
        supabase.table("admin_activity_logs").insert({
            "admin_id": admin_id,
            "action_type": action_type,
            "target_name": target_name,
            "details": details
        }).execute()
    except Exception as e:
        print(f"FAILED TO LOG ACTIVITY: {e}")

@router.get("/categories")
async def get_categories():
    try:
        response = supabase.table("categories").select("*").execute()
        return [{"id": str(c["id"]), "name": c["name"]} for c in response.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/subcategories")
@router.get("/pages")
async def get_pages():
    try:
        # Join with categories to get parent name
        # We also want to get at least one product image and the product count per page
        response = supabase.table("pages").select("*, categories(name)").execute()
        pages = response.data
        
        result = []
        for p in pages:
            # Fetch latest product for this page to get an image
            prod_res = supabase.table("products").select("image_url, discounted_price")\
                .eq("page_id", p["id"]).order("created_at", desc=True).limit(5).execute()
            
            latest_image = None
            starting_price = None
            product_count = 0
            
            if prod_res.data:
                latest_image = next((item["image_url"] for item in prod_res.data if item.get("image_url")), None)
                prices = [item["discounted_price"] for item in prod_res.data if item.get("discounted_price")]
                if prices:
                    starting_price = min(prices)
            
            # Get actual count
            count_res = supabase.table("products").select("id", count="exact").eq("page_id", p["id"]).execute()
            product_count = count_res.count or 0
            
            result.append({
                "id": str(p["id"]), 
                "name": p["name"], 
                "slug": p["slug"],
                "category_id": str(p["category_id"]),
                "parent_name": p.get("categories", {}).get("name", "General"),
                "image_url": latest_image,
                "starting_price": starting_price,
                "product_count": product_count
            })
        return result
    except Exception as e:
        return []

@router.get("/products")
async def get_products(
    category_id: Optional[str] = None,
    page_id: Optional[str] = None,
    size: int = 20,
    limit: Optional[int] = None,
    page: int = 1,
    status: Optional[str] = None
):
    try:
        actual_size = limit if limit is not None else size
        # Base select
        select_query = "*, pages(name, slug, categories(name))"
        if page_id and not is_valid_uuid(page_id):
            select_query = "*, pages!inner(name, slug, categories(name))"
        
        query = supabase.table("products").select(select_query)
        
        if page_id:
            if is_valid_uuid(page_id):
                query = query.eq("page_id", page_id)
            else:
                query = query.eq("pages.slug", page_id)
        
        if status:
            query = query.eq("scrape_status", status)
        
        # Count total
        if page_id and not is_valid_uuid(page_id):
            count_res = supabase.table("products").select("id, pages!inner(slug)", count="exact").eq("pages.slug", page_id)
        else:
            count_res = supabase.table("products").select("id", count="exact")
            if page_id: count_res = count_res.eq("page_id", page_id)
        
        if status: count_res = count_res.eq("scrape_status", status)
        total_count = count_res.execute().count or 0

        # Pagination
        start = (page - 1) * actual_size
        end = start + actual_size - 1
        response = query.range(start, end).order("created_at", desc=True).execute()
        
        products = response.data
        items = []
        for p in products:
            pg = p.get("pages") or {}
            items.append({
                "id": str(p["id"]),
                "name": p.get("name") or "Pending Scrape...",
                "title": p.get("name") or "Pending Scrape...",
                "description": p.get("description", ""),
                "deal_url": p["link"],
                "image_src": p.get("image_url", ""),
                "image_url": p.get("image_url", ""),
                "price": p.get("price"),
                "discounted_price": p.get("discounted_price"),
                "price_new": f'₹{p.get("discounted_price")}' if p.get("discounted_price") else "",
                "discount_pct": p.get("discount_pct", 0),
                "discount_percentage": p.get("discount_pct", 0),
                "scrape_status": p.get("scrape_status", "pending"),
                "last_checked": p.get("last_checked"),
                "page_name": pg.get("name", ""),
                "page_slug": pg.get("slug", ""),
                "image_gallery": p.get("image_gallery", []),
                "lowest_price": float(p.get("lowest_price_all_time") or p.get("discounted_price") or 0)
            })
            
        return {"items": items, "page": page, "size": actual_size, "total": total_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/products/{product_id}")
async def get_product_detail(product_id: str):
    try:
        response = supabase.table("products").select("*, pages(name, slug, categories(name))").eq("id", product_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Product not found")
        
        p = response.data[0]
        pg = p.get("pages") or {}
        discount = p.get("discount_pct", 0)
        
        return {
            "id": str(p["id"]),
            "title": p.get("name"),
            "name": p.get("name"),
            "description": p.get("description", ""),
            "category": pg.get("categories", {}).get("name") or pg.get("name") or "Deals",
            "image_src": p.get("image_url", ""),
            "image_gallery": p.get("image_gallery", []),
            "price_new": f'₹{float(p.get("discounted_price", 0)):,.0f}' if p.get("discounted_price") else "N/A",
            "price_old": f'₹{float(p.get("price", 0)):,.0f}' if p.get("price") else None,
            "price_discount": f"{int(p.get('discount_pct', 0))}% OFF" if p.get("discount_pct") else None,
            "deal_url": p["link"],
            "lowest_price": p.get("lowest_price_all_time")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/products/{product_id}/price-history")
async def get_price_history(product_id: str):
    try:
        ph_res = supabase.table("price_history").select("*").eq("product_id", product_id).order("recorded_at").execute()
        return [
            {"date": h["recorded_at"][:10], "price": float(h["discounted_price"] or h["price"] or 0)} 
            for h in ph_res.data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/search")
async def search_products(q: str):
    try:
        response = supabase.table("products").select("*, pages(name, slug)").ilike("name", f"%{q}%").limit(20).execute()
        products = response.data
        
        items = []
        for p in products:
            items.append({
                "id": str(p["id"]),
                "name": p["name"],
                "description": p.get("description", ""),
                "image_src": p.get("image_url", ""),
                "image_url": p.get("image_url", ""),
                "price": p.get("price"),
                "discounted_price": p.get("discounted_price"),
                "price_new": f'₹{p.get("discounted_price")}' if p.get("discounted_price") else "",
                "deal_url": p["link"]
            })
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/similar/{product_id}")
async def get_similar(product_id: str):
    return []

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_bot(req: ChatRequest):
    # STEP 2 — INPUT VALIDATION
    msg = req.message.strip()
    if not msg:
        return {
            "text": "Please enter a valid message.",
            "products": [],
            "sources": [],
            "suggestions": ["Show deals", "Best budget phones"]
        }
    
    if len(msg) > 500:
        return {
            "text": "Your message is a bit too long. Could you shorten it to under 500 characters?",
            "products": [],
            "sources": [],
            "suggestions": ["Find phones under 20k", "Show trending deals"]
        }

    try:
        from backend.services.ai_agent import chatbot_agent
        reply = chatbot_agent.respond(msg)
        return reply
    except Exception as e:
        print(f"Chatbot error: {e}")
        return {
            "text": "I'm having trouble thinking right now. Please try again later!",
            "products": [],
            "sources": [],
            "suggestions": ["Refresh the page", "Try again"]
        }

# --- ADMIN ENDPOINTS ---

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/stats")
async def get_stats():
    try:
        res = supabase.table("products").select("id", count="exact").execute()
        total = res.count or 0
        return {"total": total, "success": total, "pending": 0, "failed": 0}
    except Exception:
        return {"total": 0, "success": 0, "pending": 0, "failed": 0}

class AddProductReq(BaseModel):
    link: str
    page_slug: str  # This matches p_page_slug in RPC

@router.post("/products/add")
async def add_product(
    req: AddProductReq, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    try:
        # Call add_product_internal to auto-create missing pages
        res = await add_product_internal(req.link, req.page_slug, background_tasks)
        if not res.get("success"):
            raise Exception("Failed to add product")
        prod_id = res["id"]


        # Log the activity
        await log_admin_activity(
            admin_id=current_user["id"],
            action_type="PRODUCT_ADD",
            target_name=req.link[:100],
            details=f"Added product from {req.link[:50]}... to {req.page_slug}"
        )
        
        return {"success": True, "id": prod_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def add_product_internal(link: str, page_slug: str, background_tasks: BackgroundTasks):
    # Check if exists
    existing = supabase.table("products").select("id").eq("link", link).execute()
    if existing.data:
        return {"success": True, "note": "Exists", "id": existing.data[0]["id"]}

    # Resolve IDs
    target_slug = page_slug.lower().replace(" ", "_").strip()
    if not target_slug: target_slug = "general"
    
    # 1. Look for existing page
    page_res = supabase.table("pages").select("id, category_id, name").eq("slug", target_slug).execute()
    
    if page_res.data:
        page_id = page_res.data[0]["id"]
        cat_id = page_res.data[0]["category_id"]
    else:
        # 2. No page? Find or create 'general' Category
        cat_res = supabase.table("categories").select("id").eq("name", "general").execute()
        if cat_res.data:
            cat_id = cat_res.data[0]["id"]
        else:
            new_cat = supabase.table("categories").insert({"name": "general"}).execute()
            cat_id = new_cat.data[0]["id"]
        
        # 3. Create the new page under 'general'
        new_page = supabase.table("pages").insert({
            "name": target_slug.replace("_", " ").title(), 
            "slug": target_slug, 
            "category_id": cat_id
        }).execute()
        page_id = new_page.data[0]["id"]

    new_prod = {
        "name": "Fetching...",
        "link": link,
        "page_id": page_id,
        "scrape_status": "pending"
    }
    res = supabase.table("products").insert(new_prod).execute()
    prod_id = res.data[0]["id"]
    
    background_tasks.add_task(scrape_product_job, prod_id, link)
    return {"success": True, "id": prod_id}

@router.post("/products/bulk")
async def add_products_bulk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        content = await file.read()
        text = content.decode("utf-8")
        lines = text.splitlines()
        
        added = 0
        skipped = 0
        
        for line in lines:
            if not line.strip() or "," not in line: continue
            parts = line.split(",")
            if len(parts) < 2: continue
            
            link = parts[0].strip()
            subcat_slug = parts[1].strip()
            
            if not link or not subcat_slug: continue
            
            # Using internal hook for bulk
            try:
                res = await add_product_internal(link, subcat_slug, background_tasks)
                if res.get("success"):
                    added += 1
                else:
                    skipped += 1
            except:
                skipped += 1
                    
        # Log the activity
        await log_admin_activity(
            admin_id=current_user["id"],
            action_type="BULK_IMPORT",
            target_name=file.filename,
            details=f"Imported {added} products, skipped {skipped} duplicates."
        )
                
        return {"success": True, "added": added, "skipped": skipped}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def scrape_product_job(product_id: str, url: str):
    try:
        from backend.scraper import scrape_product_data
        
        # Fetch existing product data for comparison (e.g. lowest price)
        p_res = supabase.table("products").select("lowest_price_all_time").eq("id", product_id).execute()
        current_lowest = p_res.data[0].get("lowest_price_all_time") if p_res.data else None
        
        result = await scrape_product_data(url)
        name = result["title"][:250] if result.get("title") else "Unknown Product"
        new_sale = result.get("discounted_price", 0.0)
        
        # Calculate new "all-time lowest"
        updated_lowest = new_sale
        if current_lowest is not None and current_lowest > 0:
            updated_lowest = min(current_lowest, new_sale) if new_sale > 0 else current_lowest
        elif new_sale <= 0:
            updated_lowest = current_lowest

        supabase.table("products").update({
            "name": name,
            "description": result.get("description", ""),
            "price": result.get("price", 0.0),
            "discounted_price": new_sale,
            "image_url": result.get("image_url", ""),
            "image_gallery": result.get("image_gallery", []),
            "lowest_price_all_time": updated_lowest,
            "scrape_status": "success",
            "last_checked": datetime.datetime.utcnow().isoformat()
        }).eq("id", product_id).execute()
        
        # NOTE: Price History is now handled by DB trigger (trg_products_price_history)
        # and Offers are managed by admins, so we don't automatically insert them here anymore.
            
    except Exception as e:
        print(f"Scrape failed for {url}: {e}")
        supabase.table("products").update({
            "scrape_status": "failed",
            "last_checked": datetime.datetime.utcnow().isoformat()
        }).eq("id", product_id).execute()

@router.post("/products/rescrape/{product_id}")
async def rescrape_product(
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        supabase.table("products").update({"scrape_status": "pending"}).eq("id", product_id).execute()
        
        # Log the activity
        await log_admin_activity(
            admin_id=current_user["id"],
            action_type="PRODUCT_RESCRAPE",
            target_name=product_id,
            details=f"Triggered manual re-scrape for product {product_id}"
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str, 
    current_user: dict = Depends(get_current_user)
):
    try:
        supabase.table("products").delete().eq("id", product_id).execute()
        
        # Log the activity
        await log_admin_activity(
            admin_id=current_user["id"],
            action_type="PRODUCT_DELETE",
            target_name=product_id,
            details=f"Deleted product {product_id}"
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/pages/{page_id}")
async def delete_page(
    page_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a page and all its associated products."""
    try:
        # Get page name for logging
        page_res = supabase.table("pages").select("name").eq("id", page_id).execute()
        page_name = page_res.data[0]["name"] if page_res.data else "Unknown"

        # Delete all products under this page first (FK constraint)
        supabase.table("products").delete().eq("page_id", page_id).execute()
        
        # Delete the page
        supabase.table("pages").delete().eq("id", page_id).execute()
        
        # Log the activity
        await log_admin_activity(
            admin_id=current_user["id"],
            action_type="PAGE_DELETE",
            target_name=page_name,
            details=f"Deleted page '{page_name}' and all associated products"
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/products/{product_id}/compare")
async def compare_product_prices(
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Trigger AI discovery to find similar products on other sites."""
    try:
        from backend.services.discovery_agent import discovery_agent
        from backend.services.matching_agent import matching_agent
        from backend.scraper import scrape_product_data
        
        # 1. Fetch source product
        p_res = supabase.table("products").select("*").eq("id", product_id).execute()
        if not p_res.data:
            raise HTTPException(status_code=404, detail="Product not found")
        
        source = p_res.data[0]
        source_name = source["name"]
        
        # 2. Discover potential links
        candidates = await discovery_agent.discover_all(source_name)
        
        matches_found = 0
        for cand in candidates:
            # 3. Scrape candidate details
            # We use the existing scrape_product_data which handles all sites
            data = await scrape_product_data(cand["url"])
            if not data or data.get("price", 0) <= 0: continue
            
            # 4. Check similarity
            score = matching_agent.get_similarity(source_name, data.get("title", ""))
            
            # 5. Store if similar enough (threshold 0.7)
            if score >= 0.7:
                supabase.table("product_comparisons").upsert({
                    "product_id": product_id,
                    "competitor_url": cand["url"],
                    "competitor_name": cand["source"],
                    "competitor_price": data.get("discounted_price") or data.get("price"),
                    "competitor_image_url": data.get("image_url"),
                    "similarity_score": score,
                    "last_updated": datetime.datetime.now().isoformat()
                }).execute()
                matches_found += 1
                
        # Log the activity
        await log_admin_activity(
            admin_id=current_user["id"],
            action_type="PRICE_COMPARISON",
            target_name=source_name,
            details=f"AI Agent discovered {matches_found} matches for price comparison."
        )
        
        return {"success": True, "matches_found": matches_found}
    except Exception as e:
        print(f"Comparison Loop Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products/{product_id}/comparisons")
async def get_comparisons(
    product_id: str
):
    """Fetch external price comparisons for a product (Public)."""
    try:
        res = supabase.table("product_comparisons").select("*")\
            .eq("product_id", product_id)\
            .order("similarity_score", desc=True)\
            .execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/logs")
async def get_admin_logs(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Fetch recent admin activity logs."""
    try:
        # Join with admin_users to get full_name
        response = supabase.table("admin_activity_logs")\
            .select("*, admin_users(full_name)")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        logs = []
        for l in response.data:
            admin = l.get("admin_users") or {}
            logs.append({
                "id": str(l["id"]),
                "timestamp": l["created_at"],
                "action_type": l["action_type"],
                "target_name": l["target_name"],
                "administrator": admin.get("full_name", "System Admin"),
                "details": l["details"]
            })
            
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/products/{product_id}/price-history")
async def get_price_history(product_id: str):
    """Fetch historical price points for a product."""
    try:
        res = supabase.table("price_history")\
            .select("price, recorded_at")\
            .eq("product_id", product_id)\
            .order("recorded_at", desc=False)\
            .execute()
        
        # Format for Chart.js
        return [{"price": float(p["price"]), "date": p["recorded_at"].split("T")[0]} for p in res.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products/{product_id}/stats")
async def get_product_stats(product_id: str):
    """Fetch analytics like lowest price all-time for a product."""
    try:
        res = supabase.table("products").select("lowest_price_all_time, price, discounted_price").eq("id", product_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Product not found")
        
        p = res.data[0]
        return {
            "lowest_all_time": float(p.get("lowest_price_all_time") or 0),
            "current_sale": float(p.get("discounted_price") or 0),
            "original_mrp": float(p.get("price") or 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
import psycopg2
from sqlalchemy.pool import NullPool

@router.post("/admin/migrate-pdp")
async def migrate_pdp_db():
    """Temporary endpoint to run PDP database migrations."""
    # Using psycopg2 for more direct control over one-off migrations
    try:
        # Extract credentials from DATABASE_URL
        # URL format: postgresql://user:pass@host:port/dbname
        db_url = settings.DATABASE_URL
        # Simple extraction for Supabase
        # postgres.qgetnkxrpzwimpqsrklx:Karthik%40123@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
        
        # We'll use the pooler host from the URL
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
        
        host = parsed.hostname
        port = parsed.port or 6543
        
        print(f"Connecting to {host}:{port}...")
        
        conn = psycopg2.connect(
            host=host,
            database=parsed.path[1:],
            user=parsed.username,
            password=urllib.parse.unquote(parsed.password),
            port=port,
            sslmode='require'
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        commands = [
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS image_gallery TEXT[] DEFAULT '{}';",
            "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS lowest_price_all_time NUMERIC(12,2);",
            "ALTER TABLE public.price_history ADD COLUMN IF NOT EXISTS discounted_price NUMERIC(12,2);"
        ]
        
        results = []
        for cmd in commands:
            cur.execute(cmd)
            results.append(f"Executed OK: {cmd.split('ADD')[0]}")
            
        cur.close()
        conn.close()
        return {"success": True, "details": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
