from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Any, Optional
from pydantic import BaseModel, EmailStr
import uuid

from backend.supabase_lib import supabase
from backend.api.security import get_password_hash, get_current_user

router = APIRouter()

class AdminBase(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    full_name: str
    designation: Optional[str] = None
    role: str = "editor"

class AdminCreate(AdminBase):
    password: str

@router.get("/", response_model=List[dict])
async def list_admins(
    current_user: dict = Depends(get_current_user)
):
    try:
        response = supabase.table("admin_users").select("*").order("created_at", desc=True).execute()
        admins = response.data
        
        return [{
            "id": str(a.get("id")),
            "username": a.get("username"),
            "email": a.get("email"),
            "full_name": a.get("full_name"),
            "designation": a.get("designation"),
            "role": a.get("role"),
            "created_at": a.get("created_at")
        } for a in admins]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/", response_model=dict)
async def create_admin(
    req: AdminCreate, 
    current_user: dict = Depends(get_current_user)
):
    # Check if email exists
    try:
        existing = supabase.table("admin_users").select("id").eq("email", req.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        new_admin = {
            "id": str(uuid.uuid4()),
            "username": req.username,
            "email": req.email,
            "full_name": req.full_name,
            "designation": req.designation,
            "role": req.role,
            "hashed_password": get_password_hash(req.password)
        }
        
        response = supabase.table("admin_users").insert(new_admin).execute()
        return {"success": True, "id": new_admin["id"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{admin_id}")
async def delete_admin(
    admin_id: str, 
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check if admin exists
        existing = supabase.table("admin_users").select("id").eq("id", admin_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Admin not found")
        
        response = supabase.table("admin_users").delete().eq("id", admin_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
