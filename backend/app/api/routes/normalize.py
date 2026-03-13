"""Normalization endpoints for loading data into PostgreSQL."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.source import Source
from app.models.table import Table
from app.schemas.table import TableRead
from app.services.file_parser import infer_column_types, parse_file
from app.services.normalizer import (
    NormalizerError,
    detect_relationships,
    drop_normalized_table,
    normalize_source,
)

router = APIRouter()


@router.post("/{source_id}", response_model=TableRead)
async def normalize_source_endpoint(
    source_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Table:
    """
    Normalize an uploaded source into a PostgreSQL table.
    
    Re-uploads the file to parse and load into the database.
    """
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Check if already normalized
    existing_table = db.query(Table).filter(Table.source_id == source_id).first()
    if existing_table:
        raise HTTPException(
            status_code=400,
            detail="Source already normalized. Delete table first to re-normalize.",
        )
    
    # Parse file
    content = await file.read()
    try:
        df, metadata = parse_file(content, file.filename or source.original_filename or "data.csv")
        columns = infer_column_types(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")
    
    # Normalize
    try:
        table = normalize_source(db, source, df, columns)
        return table
    except NormalizerError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-normalize", response_model=TableRead)
async def upload_and_normalize(
    file: UploadFile = File(...),
    source_name: str | None = None,
    description: str | None = None,
    db: Session = Depends(get_db),
) -> Table:
    """
    One-step upload and normalization.
    
    Combines source creation, file parsing, and table normalization
    into a single operation.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    
    # Read and parse file
    content = await file.read()
    try:
        df, metadata = parse_file(content, file.filename)
        columns = infer_column_types(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")
    
    # Create source
    from app.models.source import SourceType
    
    source = Source(
        source_type=SourceType.CSV,
        source_name=source_name or file.filename,
        description=description,
        original_filename=file.filename,
        file_size_bytes=len(content),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    
    # Normalize
    try:
        table = normalize_source(db, source, df, columns)
        return table
    except NormalizerError as e:
        # Rollback source on failure
        db.delete(source)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-relationships")
async def detect_relationships_endpoint(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Detect relationships between all normalized tables.
    
    Returns list of detected relationships.
    """
    tables = db.query(Table).all()
    if len(tables) < 2:
        return {"relationships": [], "message": "Need at least 2 tables for relationship detection"}
    
    relationships = detect_relationships(db, tables)
    
    return {
        "relationships": [
            {
                "from_table": r.from_table.normalized_name,
                "from_column": r.from_column,
                "to_table": r.to_table.normalized_name,
                "to_column": r.to_column,
                "confidence": r.confidence,
            }
            for r in relationships
        ],
        "count": len(relationships),
    }


@router.delete("/{table_id}")
async def delete_normalized_table(
    table_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Delete a normalized table.
    
    Drops the PostgreSQL table and removes the ttd_tables record.
    """
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_name = table.normalized_name
    
    # Drop PostgreSQL table
    drop_normalized_table(db, table)
    
    # Delete record
    db.delete(table)
    db.commit()
    
    return {"status": "deleted", "table": table_name}
