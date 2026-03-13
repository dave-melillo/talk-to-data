"""Source management endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate

router = APIRouter()


@router.get("/", response_model=dict[str, Any])
async def list_sources(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List all data sources."""
    sources = db.query(Source).all()
    return {
        "sources": [
            {
                "id": str(s.id),
                "source_name": s.source_name,
                "source_type": s.source_type.value,
                "original_filename": s.original_filename,
                "file_size_bytes": s.file_size_bytes,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "table_count": len(s.tables),
            }
            for s in sources
        ],
        "total": len(sources),
    }


@router.get("/{source_id}", response_model=dict[str, Any])
async def get_source(
    source_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific source."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    return {
        "id": str(source.id),
        "source_name": source.source_name,
        "source_type": source.source_type.value,
        "description": source.description,
        "original_filename": source.original_filename,
        "file_size_bytes": source.file_size_bytes,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
        "tables": [
            {
                "id": str(t.id),
                "normalized_name": t.normalized_name,
                "row_count": t.row_count,
            }
            for t in source.tables
        ],
    }


@router.patch("/{source_id}", response_model=dict[str, Any])
async def update_source(
    source_id: UUID,
    update: SourceUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update a source."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    if update.source_name:
        source.source_name = update.source_name
    if update.description:
        source.description = update.description
    
    db.commit()
    db.refresh(source)
    
    return {
        "id": str(source.id),
        "source_name": source.source_name,
        "source_type": source.source_type.value,
        "description": source.description,
    }


@router.delete("/{source_id}")
async def delete_source(
    source_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a source and its tables."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    db.delete(source)
    db.commit()
    
    return {"status": "deleted", "source_id": str(source_id)}
