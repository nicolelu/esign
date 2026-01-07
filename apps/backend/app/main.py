"""Main FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import get_settings
from app.models import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()

    # Ensure storage directories exist
    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    description="AI-powered document signing platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


# Serve static files (page images, etc.)
@app.get("/api/v1/files/{file_path:path}")
async def serve_file(file_path: str):
    """Serve static files from storage."""
    full_path = Path(settings.storage_path) / file_path
    if not full_path.exists():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="File not found")

    # Determine content type
    suffix = full_path.suffix.lower()
    content_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
    }
    content_type = content_types.get(suffix, "application/octet-stream")

    return FileResponse(full_path, media_type=content_type)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
