"""BIZ SEMANTIC management endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.table import Table
from app.services.biz_semantic import (
    BizSemantic,
    format_biz_semantic_for_context,
    get_default_biz_semantic,
    merge_biz_semantics,
    parse_biz_semantic_yaml,
    update_table_biz_semantic,
)

router = APIRouter()


class GlossaryUpdate(BaseModel):
    """Update glossary terms."""

    terms: dict[str, str] = Field(..., description="Term -> Definition mapping")


class KPIUpdate(BaseModel):
    """Update KPI definitions."""

    kpis: dict[str, str] = Field(..., description="KPI name -> SQL mapping")


class TerminologyUpdate(BaseModel):
    """Update terminology rules."""

    rules: list[dict[str, str]] = Field(
        ...,
        description="List of {use: term, instead_of: term}",
    )


class CaveatUpdate(BaseModel):
    """Update caveats."""

    caveats: list[str] = Field(..., description="List of caveat messages")


class YAMLUpdate(BaseModel):
    """Update from raw YAML."""

    yaml_content: str


@router.get("/template")
async def get_biz_semantic_template() -> dict[str, Any]:
    """Get a BIZ SEMANTIC template with examples."""
    template = get_default_biz_semantic()
    return {
        "template": template.model_dump(),
        "description": "Use this as a starting point for your BIZ SEMANTIC configuration",
    }


@router.get("/{table_id}")
async def get_table_biz_semantic(
    table_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get the BIZ SEMANTIC for a table."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    return {
        "table_id": str(table_id),
        "table_name": table.normalized_name,
        "biz_semantic": table.biz_semantic or {},
        "formatted": format_biz_semantic_for_context(table.biz_semantic or {}),
    }


@router.put("/{table_id}")
async def set_table_biz_semantic(
    table_id: UUID,
    semantic: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Set the complete BIZ SEMANTIC for a table.
    
    Replaces existing BIZ SEMANTIC.
    """
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    try:
        # Validate structure
        validated = BizSemantic(**semantic)
        update_table_biz_semantic(db, table, validated)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid BIZ SEMANTIC: {e}")
    
    return {
        "status": "updated",
        "table_id": str(table_id),
        "biz_semantic": table.biz_semantic,
    }


@router.patch("/{table_id}")
async def update_table_biz_semantic_partial(
    table_id: UUID,
    updates: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Partially update BIZ SEMANTIC for a table.
    
    Merges updates with existing data.
    """
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    existing = table.biz_semantic or {}
    merged = merge_biz_semantics(existing, updates)
    
    table.biz_semantic = merged
    db.commit()
    db.refresh(table)
    
    return {
        "status": "merged",
        "table_id": str(table_id),
        "biz_semantic": table.biz_semantic,
    }


@router.post("/{table_id}/glossary")
async def add_glossary_terms(
    table_id: UUID,
    update: GlossaryUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Add or update glossary terms."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    existing = table.biz_semantic or {}
    glossary = existing.get("glossary", {})
    glossary.update(update.terms)
    
    merged = merge_biz_semantics(existing, {"glossary": glossary})
    table.biz_semantic = merged
    db.commit()
    
    return {"status": "updated", "glossary": glossary}


@router.post("/{table_id}/kpis")
async def add_kpis(
    table_id: UUID,
    update: KPIUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Add or update KPI definitions."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    existing = table.biz_semantic or {}
    kpis = existing.get("kpis", {})
    kpis.update(update.kpis)
    
    merged = merge_biz_semantics(existing, {"kpis": kpis})
    table.biz_semantic = merged
    db.commit()
    
    return {"status": "updated", "kpis": kpis}


@router.post("/{table_id}/caveats")
async def add_caveats(
    table_id: UUID,
    update: CaveatUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Add caveats."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    existing = table.biz_semantic or {}
    caveats = existing.get("caveats", [])
    for caveat in update.caveats:
        if caveat not in caveats:
            caveats.append(caveat)
    
    merged = merge_biz_semantics(existing, {"caveats": caveats})
    table.biz_semantic = merged
    db.commit()
    
    return {"status": "updated", "caveats": caveats}


@router.post("/{table_id}/yaml")
async def update_from_yaml(
    table_id: UUID,
    update: YAMLUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Update BIZ SEMANTIC from raw YAML.
    
    Useful for bulk editing or importing from external sources.
    """
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    try:
        parsed = parse_biz_semantic_yaml(update.yaml_content)
        update_table_biz_semantic(db, table, parsed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "status": "updated",
        "table_id": str(table_id),
        "biz_semantic": table.biz_semantic,
    }
