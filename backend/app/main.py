"""Talk To Data v3 - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.middleware.auth import APIKeyMiddleware
from app.models import Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create tables if they don't exist
    # In production, use Alembic migrations instead
    if settings.debug:
        Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Natural Language to SQL - Ask questions about your data in plain English",
    lifespan=lifespan,
)

# API Key authentication (optional, enable via REQUIRE_API_KEY=true)
app.add_middleware(APIKeyMiddleware)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Also mount at root for convenience
@app.get("/")
def root():
    """Root redirect to API."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "api": "/api/v1",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """Quick health check at root level."""
    return {"status": "ok", "version": settings.app_version}
