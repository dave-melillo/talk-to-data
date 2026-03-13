"""
BIZ SEMANTIC layer service.

Manages user-provided business context:
- Glossary: Business term definitions
- KPIs: Metric definitions with SQL
- Terminology: Preferred language
- Caveats: Data quality warnings
"""

from datetime import datetime, timezone
from typing import Any

import yaml
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.table import Table


class GlossaryTerm(BaseModel):
    """A business term definition."""

    term: str
    definition: str
    sql_hint: str | None = Field(None, description="SQL fragment for this term")
    related_columns: list[str] = Field(default_factory=list)


class KPIDefinition(BaseModel):
    """A KPI/metric definition."""

    name: str
    description: str
    sql: str = Field(..., description="SQL expression for this KPI")
    unit: str | None = None


class TerminologyRule(BaseModel):
    """Preferred terminology mapping."""

    use: str = Field(..., description="Preferred term")
    instead_of: str = Field(..., description="Term to replace")


class Caveat(BaseModel):
    """Data quality warning."""

    message: str
    severity: str = Field("info", description="info, warning, critical")
    affected_tables: list[str] = Field(default_factory=list)
    affected_columns: list[str] = Field(default_factory=list)


class BizSemantic(BaseModel):
    """Complete BIZ SEMANTIC structure."""

    version: str = "1.0"
    updated_at: str | None = None
    business_name: str | None = None
    description: str | None = None
    
    glossary: dict[str, str] = Field(default_factory=dict)
    kpis: dict[str, str] = Field(default_factory=dict)
    terminology: list[dict[str, str]] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    
    # Extended format
    glossary_extended: list[GlossaryTerm] = Field(default_factory=list)
    kpis_extended: list[KPIDefinition] = Field(default_factory=list)
    terminology_extended: list[TerminologyRule] = Field(default_factory=list)
    caveats_extended: list[Caveat] = Field(default_factory=list)


def parse_biz_semantic_yaml(yaml_content: str) -> BizSemantic:
    """Parse BIZ SEMANTIC from YAML string."""
    try:
        data = yaml.safe_load(yaml_content) or {}
        return BizSemantic(**data)
    except Exception as e:
        raise ValueError(f"Invalid YAML: {e}")


def biz_semantic_to_yaml(semantic: BizSemantic) -> str:
    """Convert BIZ SEMANTIC to YAML string."""
    data = semantic.model_dump(exclude_none=True, exclude_defaults=True)
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def get_default_biz_semantic() -> BizSemantic:
    """Get a default BIZ SEMANTIC template."""
    return BizSemantic(
        version="1.0",
        business_name="My Business",
        description="Business context for data queries",
        glossary={
            "active_customer": "Customer with at least one order in last 90 days",
            "high_value": "Revenue > $1000",
        },
        kpis={
            "total_revenue": "SUM(order_total) WHERE status = 'completed'",
            "customer_count": "COUNT(DISTINCT customer_id)",
        },
        terminology=[
            {"use": "customer", "instead_of": "user"},
            {"use": "order", "instead_of": "purchase"},
        ],
        caveats=[
            "Data before 2024-01-01 was migrated from legacy system",
            "Refunds are stored as negative order_total values",
        ],
    )


def update_table_biz_semantic(
    db: Session,
    table: Table,
    biz_semantic: BizSemantic | dict[str, Any],
) -> Table:
    """Update the BIZ SEMANTIC for a table."""
    if isinstance(biz_semantic, BizSemantic):
        data = biz_semantic.model_dump(exclude_none=True)
    else:
        data = biz_semantic
    
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    table.biz_semantic = data
    db.commit()
    db.refresh(table)
    
    return table


def merge_biz_semantics(
    base: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge BIZ SEMANTIC updates into existing data."""
    merged = base.copy()
    
    for key, value in updates.items():
        if key in ("glossary", "kpis") and isinstance(value, dict):
            # Merge dictionaries
            merged[key] = {**merged.get(key, {}), **value}
        elif key in ("terminology", "caveats") and isinstance(value, list):
            # Append to lists (dedupe)
            existing = merged.get(key, [])
            for item in value:
                if item not in existing:
                    existing.append(item)
            merged[key] = existing
        else:
            merged[key] = value
    
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    return merged


def format_biz_semantic_for_context(semantic: dict[str, Any]) -> str:
    """Format BIZ SEMANTIC for inclusion in LLM context."""
    lines = ["## Business Context\n"]
    
    if semantic.get("business_name"):
        lines.append(f"**Business:** {semantic['business_name']}\n")
    
    if semantic.get("description"):
        lines.append(f"{semantic['description']}\n")
    
    # Glossary
    glossary = semantic.get("glossary", {})
    if glossary:
        lines.append("### Business Glossary")
        for term, definition in glossary.items():
            lines.append(f"- **{term}**: {definition}")
        lines.append("")
    
    # KPIs
    kpis = semantic.get("kpis", {})
    if kpis:
        lines.append("### KPI Definitions")
        for name, sql in kpis.items():
            lines.append(f"- **{name}**: `{sql}`")
        lines.append("")
    
    # Terminology
    terminology = semantic.get("terminology", [])
    if terminology:
        lines.append("### Preferred Terminology")
        for rule in terminology:
            if isinstance(rule, dict):
                lines.append(f"- Use \"{rule.get('use')}\" instead of \"{rule.get('instead_of')}\"")
        lines.append("")
    
    # Caveats
    caveats = semantic.get("caveats", [])
    if caveats:
        lines.append("### Important Caveats")
        for caveat in caveats:
            if isinstance(caveat, str):
                lines.append(f"- ⚠️ {caveat}")
            elif isinstance(caveat, dict):
                lines.append(f"- ⚠️ {caveat.get('message', caveat)}")
        lines.append("")
    
    return "\n".join(lines)
