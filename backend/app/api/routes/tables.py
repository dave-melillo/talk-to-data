"""Table management endpoints - stub for PR1."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_tables():
    """List all tables."""
    return {"tables": [], "total": 0}
