from sqlalchemy import text
from typing import List, Dict, Any, Optional
from backend.db.session import get_db_session

class ProductRepository:
    """Data Access Object for Products using Async SQLAlchemy."""
    
    @staticmethod
    async def get_products(
        session, page_id: Optional[str] = None, status: Optional[str] = None, 
        limit: int = 20, offset: int = 0
    ) -> Tuple[List[Dict], int]:
        
        # We manually construct nested JSON to match Supabase response format perfectly
        base_query = """
        SELECT
            p.*,
            json_build_object(
                'name', pg.name,
                'slug', pg.slug,
                'categories', json_build_object('name', c.name)
            ) as pages
        FROM products p
        LEFT JOIN pages pg ON p.page_id = pg.id
        LEFT JOIN categories c ON pg.category_id = c.id
        WHERE 1=1
        """
        params = {"limit": limit, "offset": offset}
        
        if page_id:
            # Check if UUID or Slug
            if "-" in page_id and len(page_id) == 36:
                base_query += " AND p.page_id = :page_id"
                params["page_id"] = page_id
            else:
                base_query += " AND pg.slug = :page_slug"
                params["page_slug"] = page_id
                
        if status:
            base_query += " AND p.scrape_status = :status"
            params["status"] = status
            
        # Count total
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS count_query"
        total_res = await session.execute(text(count_query), params)
        total_count = total_res.scalar() or 0
        
        # Paginate
        base_query += " ORDER BY p.created_at DESC LIMIT :limit OFFSET :offset"
        res = await session.execute(text(base_query), params)
        
        # Format results exactly like Supabase
        products = []
        for row in res.mappings():
            d = dict(row)
            d["id"] = str(d["id"])
            if d.get("page_id"): d["page_id"] = str(d["page_id"])
            products.append(d)
            
        return products, total_count

    @staticmethod
    async def get_product_detail(session, product_id: str) -> Optional[Dict]:
        query = """
        SELECT
            p.*,
            json_build_object(
                'name', pg.name,
                'slug', pg.slug,
                'categories', json_build_object('name', c.name)
            ) as pages
        FROM products p
        LEFT JOIN pages pg ON p.page_id = pg.id
        LEFT JOIN categories c ON pg.category_id = c.id
        WHERE p.id = :product_id
        """
        res = await session.execute(text(query), {"product_id": product_id})
        row = res.mappings().first()
        if not row:
            return None
        
        d = dict(row)
        d["id"] = str(d["id"])
        return d
        
    @staticmethod
    async def delete_product(session, product_id: str):
        query = "DELETE FROM products WHERE id = :pid"
        await session.execute(text(query), {"pid": product_id})
        await session.commit()
