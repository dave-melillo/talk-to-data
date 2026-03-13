"""
DATA SEMANTIC layer generation service.

Generates automatic metadata:
- Table descriptions
- Column descriptions
- Sample values
- Statistics (cardinality, distributions)
- Relationship confidence
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.table import Table
from app.services.llm import generate_column_description, generate_table_description


def generate_data_semantic(
    db: Session,
    table: Table,
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Generate the DATA SEMANTIC layer for a table.
    
    Returns a YAML-like structure with:
    - Table description
    - Column metadata with descriptions
    - Statistics
    - Sample values
    """
    semantic: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "table": {
            "name": table.normalized_name,
            "original_name": table.original_name,
            "row_count": table.row_count,
            "description": None,
        },
        "columns": [],
        "statistics": {},
    }
    
    # Get sample rows for context
    sample_rows = []
    try:
        result = db.execute(
            text(f'SELECT * FROM "{table.normalized_name}" LIMIT 5')
        )
        sample_rows = [dict(row._mapping) for row in result]
    except Exception:
        pass
    
    # Generate table description
    if use_llm and table.columns:
        try:
            semantic["table"]["description"] = generate_table_description(
                table.normalized_name,
                table.columns,
                sample_rows,
            )
        except Exception:
            semantic["table"]["description"] = f"Data table with {table.row_count} rows"
    else:
        semantic["table"]["description"] = f"Data table with {table.row_count} rows"
    
    # Process each column
    for col in table.columns or []:
        col_semantic = {
            "name": col.get("name"),
            "original_name": col.get("original_name", col.get("name")),
            "data_type": col.get("data_type"),
            "nullable": col.get("nullable", True),
            "is_primary_key": col.get("is_primary_key", False),
            "is_unique": col.get("is_unique", False),
            "description": None,
            "statistics": {},
            "sample_values": col.get("sample_values", [])[:10],
        }
        
        # Generate column description
        if use_llm:
            try:
                col_semantic["description"] = generate_column_description(
                    col.get("name", ""),
                    col.get("data_type", ""),
                    col.get("sample_values", []),
                    semantic["table"]["description"] or "",
                )
            except Exception:
                col_semantic["description"] = col.get("data_type", "Field")
        
        # Add statistics
        col_semantic["statistics"] = {
            "distinct_count": col.get("distinct_count"),
            "null_count": col.get("null_count"),
            "min_value": col.get("min_value"),
            "max_value": col.get("max_value"),
        }
        
        # Detect special column types
        name_lower = col.get("name", "").lower()
        if "email" in name_lower:
            col_semantic["format"] = "email"
        elif "phone" in name_lower:
            col_semantic["format"] = "phone"
        elif "url" in name_lower or "link" in name_lower:
            col_semantic["format"] = "url"
        elif "date" in name_lower or col.get("data_type") in ("TIMESTAMP", "DATE"):
            col_semantic["format"] = "datetime"
        
        semantic["columns"].append(col_semantic)
    
    # Table-level statistics
    semantic["statistics"] = {
        "row_count": table.row_count,
        "column_count": len(table.columns or []),
        "primary_key_columns": [
            c["name"] for c in (table.columns or []) if c.get("is_primary_key")
        ],
        "nullable_columns": [
            c["name"] for c in (table.columns or []) if c.get("nullable")
        ],
    }
    
    return semantic


def update_table_semantic(
    db: Session,
    table: Table,
    use_llm: bool = True,
) -> Table:
    """
    Generate and save DATA SEMANTIC for a table.
    """
    semantic = generate_data_semantic(db, table, use_llm=use_llm)
    
    table.data_semantic = semantic
    table.description = semantic["table"]["description"]
    
    db.commit()
    db.refresh(table)
    
    return table


def generate_schema_summary(
    db: Session,
    tables: list[Table],
) -> str:
    """
    Generate a text summary of the entire schema for LLM context.
    """
    lines = ["## Database Schema\n"]
    
    for table in tables:
        desc = table.description or "No description"
        lines.append(f"### {table.normalized_name}")
        lines.append(f"_{desc}_\n")
        lines.append(f"Rows: {table.row_count}\n")
        lines.append("| Column | Type | Description |")
        lines.append("|--------|------|-------------|")
        
        semantic = table.data_semantic or {}
        col_info = {c["name"]: c for c in semantic.get("columns", [])}
        
        for col in table.columns or []:
            name = col.get("name", "")
            dtype = col.get("data_type", "")
            col_desc = col_info.get(name, {}).get("description", "")
            lines.append(f"| {name} | {dtype} | {col_desc} |")
        
        lines.append("")
    
    return "\n".join(lines)
