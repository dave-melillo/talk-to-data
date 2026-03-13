"""Table management endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.table import Table

router = APIRouter()


@router.get("/", response_model=dict[str, Any])
async def list_tables(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List all normalized tables."""
    tables = db.query(Table).all()
    return {
        "tables": [
            {
                "id": str(t.id),
                "normalized_name": t.normalized_name,
                "original_name": t.original_name,
                "source_id": str(t.source_id),
                "row_count": t.row_count,
                "column_count": len(t.columns) if t.columns else 0,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tables
        ],
        "total": len(tables),
    }


@router.get("/{table_id}", response_model=dict[str, Any])
async def get_table(
    table_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific table with full details."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    return {
        "id": str(table.id),
        "normalized_name": table.normalized_name,
        "original_name": table.original_name,
        "source_id": str(table.source_id),
        "row_count": table.row_count,
        "columns": table.columns,
        "description": table.description,
        "data_semantic": table.data_semantic,
        "biz_semantic": table.biz_semantic,
        "created_at": table.created_at.isoformat() if table.created_at else None,
        "updated_at": table.updated_at.isoformat() if table.updated_at else None,
    }


@router.get("/{table_id}/data")
async def get_table_data(
    table_id: UUID,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get data from a table."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    try:
        result = db.execute(
            text(f'SELECT * FROM "{table.normalized_name}" LIMIT :limit OFFSET :offset'),
            {"limit": limit, "offset": offset},
        )
        
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result]
        
        return {
            "table_id": str(table_id),
            "table_name": table.normalized_name,
            "columns": columns,
            "data": rows,
            "limit": limit,
            "offset": offset,
            "total_rows": table.row_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e}")


@router.delete("/{table_id}")
async def delete_table(
    table_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a table."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Drop the PostgreSQL table
    db.execute(text(f'DROP TABLE IF EXISTS "{table.normalized_name}" CASCADE'))
    
    # Delete the record
    db.delete(table)
    db.commit()
    
    return {"status": "deleted", "table": table.normalized_name}
