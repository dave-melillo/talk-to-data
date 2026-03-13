"""API route registration."""

from fastapi import APIRouter

from app.api.routes import (
    health,
    sources,
    tables,
    queries,
    upload,
    normalize,
    semantic,
    biz_semantic,
)

api_router = APIRouter()

# Health check (no prefix)
api_router.include_router(health.router, tags=["health"])

# Resource routes
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(tables.router, prefix="/tables", tags=["tables"])
api_router.include_router(queries.router, prefix="/queries", tags=["queries"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(normalize.router, prefix="/normalize", tags=["normalize"])
api_router.include_router(semantic.router, prefix="/semantic", tags=["data-semantic"])
api_router.include_router(biz_semantic.router, prefix="/biz-semantic", tags=["biz-semantic"])
