import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "TheMaskMan API"
    API_V1_STR: str = "/api"
    
    # DB Settings (Required)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/postgres" 
    )
    
    # Supabase (for REST API if needed, though we use direct DB primarily)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://qgetnkxrpzwimpqsrklx.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Redis Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Auth Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 1 week

    class Config:
        env_file = ".env"

settings = Settings()
