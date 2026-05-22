from fastapi import FastAPI # Reload Test 2
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from backend.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="TheMaskMan AI Product Intelligence Platform API"
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.1", "updated": True}

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since frontend and backend might run on different ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.api.router import router as api_router
from backend.api.auth import router as auth_router
from backend.api.admins import router as admins_router


app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admins_router, prefix="/api/admins", tags=["Admins / Employees"])

# Serve static files from the root directory
# We mount this AFTER the API routes so API take precedence
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def read_index():
    return FileResponse("user_login.html")

@app.get("/{path:path}")
async def catch_all(path: str):
    # If the file exists in the root, serve it
    if os.path.isfile(path):
        return FileResponse(path)
    # Otherwise, you might want to return index.html for SPA behavior, 
    # but for this multi-page app, we just let it 404 if not found specifically.
    return FileResponse("index.html")
