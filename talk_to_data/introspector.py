"""Schema introspection - extract table/column metadata from any SQL database."""

from sqlalchemy import create_engine, inspect, MetaData
from typing import Dict, List, Any


def introspect_schema(connection_string: str) -> Dict[str, Any]:
    """
    Introspect database schema and return structured metadata.
    
    Args:
        connection_string: SQLAlchemy connection string (e.g., 'sqlite:///data.db')
    
    Returns:
        Dict with tables, columns, types, and relationships
    """
    engine = create_engine(connection_string)
    inspector = inspect(engine)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    schema = {
        "tables": {},
        "relationships": []
    }
    
    for table_name in inspector.get_table_names():
        columns = []
        primary_keys = [pk for pk in inspector.get_pk_constraint(table_name).get('constrained_columns', [])]
        
        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "primary_key": col["name"] in primary_keys
            })
        
        # Get foreign keys
        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            for i, col in enumerate(fk.get('constrained_columns', [])):
                ref_table = fk.get('referred_table')
                ref_col = fk.get('referred_columns', [])[i] if i < len(fk.get('referred_columns', [])) else None
                if ref_table and ref_col:
                    schema["relationships"].append({
                        "from_table": table_name,
                        "from_column": col,
                        "to_table": ref_table,
                        "to_column": ref_col
                    })
        
        schema["tables"][table_name] = {
            "columns": columns,
            "primary_keys": primary_keys,
            "row_count": None  # Optional: could query COUNT(*)
        }
    
    return schema


def schema_to_prompt(schema: Dict[str, Any], semantic: Dict[str, Any] = None) -> str:
    """
    Convert schema to a prompt-friendly string representation.
    
    Args:
        schema: Output from introspect_schema()
        semantic: Optional semantic layer definitions
    
    Returns:
        String representation for LLM prompt
    """
    lines = ["DATABASE SCHEMA:", ""]
    
    for table_name, table_info in schema["tables"].items():
        # Get semantic description if available
        table_desc = ""
        if semantic and table_name in semantic.get("tables", {}):
            table_desc = f" -- {semantic['tables'][table_name].get('description', '')}"
        
        lines.append(f"TABLE: {table_name}{table_desc}")
        
        for col in table_info["columns"]:
            pk_marker = " [PK]" if col["primary_key"] else ""
            col_desc = ""
            if semantic and table_name in semantic.get("tables", {}):
                col_desc = semantic["tables"][table_name].get("columns", {}).get(col["name"], "")
                if col_desc:
                    col_desc = f" -- {col_desc}"
            lines.append(f"  - {col['name']}: {col['type']}{pk_marker}{col_desc}")
        
        lines.append("")
    
    if schema["relationships"]:
        lines.append("RELATIONSHIPS:")
        for rel in schema["relationships"]:
            lines.append(f"  {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test with SQLite
    import json
    schema = introspect_schema("sqlite:///data/chinook.db")
    print(json.dumps(schema, indent=2))
