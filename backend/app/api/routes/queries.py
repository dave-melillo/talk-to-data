"""Query endpoints - stub for PR1."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/history")
def query_history():
    """Get query history."""
    return {"queries": [], "total": 0}
