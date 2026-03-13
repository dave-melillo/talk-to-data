"""File upload endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.source import Source, SourceType
from app.schemas.source import SourceRead
from app.services.file_parser import (
    FileParseError,
    detect_file_type,
    infer_column_types,
    parse_file,
    preview_file,
)

router = APIRouter()
settings = get_settings()

# Max file size in bytes
MAX_FILE_SIZE = settings.max_upload_size_mb * 1024 * 1024


@router.post("/preview")
async def preview_upload(
    file: UploadFile = File(...),
    preview_rows: int = 10,
) -> dict[str, Any]:
    """
    Preview a file before importing.
    
    Returns column info and sample data without persisting.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    
    try:
        detect_file_type(file.filename)
    except FileParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Read content
    content = await file.read()
    
    # Check size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.max_upload_size_mb}MB",
        )
    
    try:
        preview = preview_file(content, file.filename, preview_rows)
        return preview
    except FileParseError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=SourceRead)
async def upload_file(
    file: UploadFile = File(...),
    source_name: str | None = None,
    description: str | None = None,
    db: Session = Depends(get_db),
) -> Source:
    """
    Upload and import a file as a new data source.
    
    The file is parsed, analyzed, and stored. A ttd_sources record
    is created with file metadata.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    
    try:
        detect_file_type(file.filename)
    except FileParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Read content
    content = await file.read()
    
    # Check size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.max_upload_size_mb}MB",
        )
    
    try:
        # Parse file to validate and get metadata
        df, metadata = parse_file(content, file.filename)
        
        # Get column types
        columns = infer_column_types(df)
        
        # Create source record
        source = Source(
            source_type=SourceType.CSV,
            source_name=source_name or file.filename,
            description=description,
            original_filename=file.filename,
            file_size_bytes=len(content),
            connection_info={
                "metadata": metadata,
                "columns": columns,
                "row_count": len(df),
            },
        )
        
        db.add(source)
        db.commit()
        db.refresh(source)
        
        return source
    
    except FileParseError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{source_id}/columns")
async def get_source_columns(
    source_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get column information for an uploaded source."""
    source = db.query(Source).filter(Source.id == source_id).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    if source.source_type != SourceType.CSV:
        raise HTTPException(
            status_code=400,
            detail="Column info only available for file sources",
        )
    
    conn_info = source.connection_info or {}
    return {
        "source_id": str(source.id),
        "source_name": source.source_name,
        "columns": conn_info.get("columns", []),
        "row_count": conn_info.get("row_count", 0),
    }
