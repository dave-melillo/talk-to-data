"""Semantic layer management endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.table import Table
from app.services.data_semantic import (
    generate_data_semantic,
    generate_schema_summary,
    update_table_semantic,
)

router = APIRouter()


@router.post("/{table_id}/generate")
async def generate_table_semantic(
    table_id: UUID,
    use_llm: bool = Query(True, description="Use LLM for descriptions"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate DATA SEMANTIC for a specific table.
    
    Uses LLM to generate table and column descriptions based on
    schema analysis and sample data.
    """
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    semantic = generate_data_semantic(db, table, use_llm=use_llm)
    
    # Save to table
    table.data_semantic = semantic
    table.description = semantic["table"]["description"]
    db.commit()
    
    return {
        "table_id": str(table_id),
        "semantic": semantic,
    }


@router.get("/{table_id}")
async def get_table_semantic(
    table_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get the DATA SEMANTIC for a table."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    if not table.data_semantic:
        raise HTTPException(
            status_code=404,
            detail="Semantic not generated. Call POST /{table_id}/generate first.",
        )
    
    return {
        "table_id": str(table_id),
        "semantic": table.data_semantic,
    }


@router.post("/generate-all")
async def generate_all_semantics(
    use_llm: bool = Query(True, description="Use LLM for descriptions"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate DATA SEMANTIC for all tables.
    """
    tables = db.query(Table).all()
    
    if not tables:
        return {"message": "No tables found", "generated": 0}
    
    results = []
    for table in tables:
        try:
            update_table_semantic(db, table, use_llm=use_llm)
            results.append({
                "table_id": str(table.id),
                "table_name": table.normalized_name,
                "status": "success",
            })
        except Exception as e:
            results.append({
                "table_id": str(table.id),
                "table_name": table.normalized_name,
                "status": "error",
                "error": str(e),
            })
    
    return {
        "generated": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results,
    }


@router.get("/schema-summary")
async def get_schema_summary(
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Get a text summary of the entire schema.
    
    This is the format used as context for the query engine.
    """
    tables = db.query(Table).all()
    
    if not tables:
        return {"summary": "No tables loaded."}
    
    summary = generate_schema_summary(db, tables)
    return {"summary": summary}
