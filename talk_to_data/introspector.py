"""Schema introspection - extract table/column metadata from any SQL database or CSV file."""

from sqlalchemy import create_engine, inspect, MetaData
from typing import Dict, List, Any
from pathlib import Path
import pandas as pd


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


def introspect_csv(file_path: str, sample_rows: int = 100) -> Dict[str, Any]:
    """
    Introspect CSV file and return schema in same format as introspect_schema().
    
    Args:
        file_path: Path to CSV file
        sample_rows: Number of rows to sample for type inference
    
    Returns:
        Schema dict with single table containing CSV columns
    """
    try:
        # Read CSV file (sample first N rows for type inference)
        df = pd.read_csv(file_path, nrows=sample_rows)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")
    
    columns = []
    for col_name in df.columns:
        dtype = df[col_name].dtype
        
        # Map pandas dtype to SQL type
        if dtype == 'int64':
            sql_type = 'INTEGER'
        elif dtype == 'float64':
            sql_type = 'REAL'
        elif dtype == 'bool':
            sql_type = 'BOOLEAN'
        elif dtype in ['datetime64[ns]', 'datetime64']:
            sql_type = 'DATETIME'
        else:
            sql_type = 'TEXT'
        
        columns.append({
            "name": col_name,
            "type": sql_type,
            "nullable": df[col_name].isnull().any(),
            "primary_key": False
        })
    
    # CSV becomes a single table named after the file (minus extension)
    table_name = Path(file_path).stem
    
    schema = {
        "tables": {
            table_name: {
                "columns": columns,
                "primary_keys": [],
                "row_count": len(df)
            }
        },
        "relationships": []  # CSVs have no FK relationships
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
    # Test with sample database
    import json
    import sys
    
    if len(sys.argv) > 1:
        connection_string = sys.argv[1]
        schema = introspect_schema(connection_string)
        print(json.dumps(schema, indent=2))
    else:
        print("Usage: python introspector.py <connection_string>")
        print("Example: python introspector.py sqlite:///data/chinook.db")
