"""Source management endpoints - stub for PR1."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_sources():
    """List all data sources."""
    return {"sources": [], "total": 0}
