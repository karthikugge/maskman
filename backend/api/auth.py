from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from backend.supabase_lib import supabase
from backend.api.security import verify_password, create_access_token
from backend.config import settings

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/login", response_model=Token)
async def login(req: LoginRequest):
    # 1. Find user via Supabase SDK
    try:
        response = supabase.table("admin_users").select("*").eq("email", str(req.email)).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        
        user_data = response.data[0]
        
        # 2. Verify password
        if not verify_password(req.password, user_data.get("hashed_password")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        
        # 3. Create token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user_data.get("email"), expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "email": user_data.get("email"),
                "full_name": user_data.get("full_name"),
                "role": user_data.get("role", "editor")
            }
        }
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
