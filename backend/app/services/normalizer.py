"""
Normalizer service for creating PostgreSQL tables from uploaded data.

Handles:
- Table name sanitization
- DDL generation from inferred types
- Bulk data loading
- Relationship detection
"""

import re
import uuid
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.relationship import Relationship
from app.models.source import Source
from app.models.table import Table


class NormalizerError(Exception):
    """Exception raised during normalization."""

    pass


def sanitize_table_name(name: str, prefix: str = "ttd_data_") -> str:
    """
    Convert a filename or table name to a valid PostgreSQL identifier.
    
    - Lowercase
    - Replace spaces/special chars with underscores
    - Ensure starts with letter or underscore
    - Truncate to 63 chars (PostgreSQL limit)
    """
    # Remove file extension
    name = re.sub(r"\.[^.]+$", "", name)
    
    # Lowercase and replace non-alphanumeric with underscore
    sanitized = re.sub(r"[^a-z0-9_]", "_", name.lower())
    
    # Remove consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")
    
    # Ensure starts with letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = f"t_{sanitized}"
    
    # Add prefix and truncate
    full_name = f"{prefix}{sanitized}"
    return full_name[:63]


def sanitize_column_name(name: str) -> str:
    """Convert a column name to a valid PostgreSQL identifier."""
    sanitized = re.sub(r"[^a-z0-9_]", "_", str(name).lower())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    
    if sanitized and not sanitized[0].isalpha():
        sanitized = f"c_{sanitized}"
    
    # Reserved words
    reserved = {"order", "user", "table", "index", "select", "from", "where"}
    if sanitized in reserved:
        sanitized = f"{sanitized}_"
    
    return sanitized[:63] if sanitized else "column"


def pandas_to_postgres_type(dtype: str, max_length: int | None = None) -> str:
    """Convert pandas dtype to PostgreSQL type."""
    dtype_str = str(dtype).lower()
    
    if "int" in dtype_str:
        if "64" in dtype_str:
            return "BIGINT"
        return "INTEGER"
    elif "float" in dtype_str:
        return "DOUBLE PRECISION"
    elif "bool" in dtype_str:
        return "BOOLEAN"
    elif "datetime" in dtype_str:
        return "TIMESTAMP WITH TIME ZONE"
    elif "date" in dtype_str:
        return "DATE"
    elif "time" in dtype_str:
        return "TIME"
    else:
        # String types
        if max_length and max_length > 255:
            return "TEXT"
        return "VARCHAR(255)"


def generate_create_table_ddl(
    table_name: str,
    columns: list[dict[str, Any]],
) -> str:
    """Generate CREATE TABLE DDL statement."""
    col_defs = []
    
    for col in columns:
        pg_name = sanitize_column_name(col["name"])
        pg_type = col.get("data_type", "TEXT")
        
        # Convert inferred type to Postgres
        if pg_type == "INTEGER":
            pg_type = "INTEGER"
        elif pg_type == "FLOAT":
            pg_type = "DOUBLE PRECISION"
        elif pg_type == "BOOLEAN":
            pg_type = "BOOLEAN"
        elif pg_type == "TIMESTAMP":
            pg_type = "TIMESTAMP WITH TIME ZONE"
        elif pg_type.startswith("VARCHAR"):
            pass  # Keep as is
        else:
            pg_type = "TEXT"
        
        nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
        col_defs.append(f'    "{pg_name}" {pg_type} {nullable}')
    
    # Add internal row ID
    col_defs.insert(0, '    "_ttd_row_id" SERIAL PRIMARY KEY')
    
    cols_sql = ",\n".join(col_defs)
    return f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n{cols_sql}\n);'


def normalize_source(
    db: Session,
    source: Source,
    df: pd.DataFrame,
    columns: list[dict[str, Any]],
) -> Table:
    """
    Normalize a source into a PostgreSQL table.
    
    1. Generate sanitized table name
    2. Create table with inferred schema
    3. Load data
    4. Create ttd_tables record
    """
    # Generate unique table name
    base_name = source.source_name or source.original_filename or "data"
    table_name = sanitize_table_name(base_name)
    
    # Check for name collision, add suffix if needed
    existing = db.query(Table).filter(Table.normalized_name == table_name).first()
    if existing:
        suffix = str(uuid.uuid4())[:8]
        table_name = f"{table_name}_{suffix}"[:63]
    
    # Sanitize column names in DataFrame
    column_mapping = {}
    for col in df.columns:
        sanitized = sanitize_column_name(col)
        # Handle duplicate column names
        if sanitized in column_mapping.values():
            sanitized = f"{sanitized}_{len(column_mapping)}"
        column_mapping[col] = sanitized
    
    df_clean = df.rename(columns=column_mapping)
    
    # Update column metadata with sanitized names
    for col_meta in columns:
        col_meta["original_name"] = col_meta["name"]
        col_meta["name"] = column_mapping.get(col_meta["name"], col_meta["name"])
    
    # Generate and execute DDL
    ddl = generate_create_table_ddl(table_name, columns)
    db.execute(text(ddl))
    
    # Bulk insert data using COPY-like approach
    # Convert DataFrame to SQL-friendly format
    for col in df_clean.columns:
        # Handle NaN/None for proper NULL insertion
        if df_clean[col].dtype == "object":
            df_clean[col] = df_clean[col].fillna("")
    
    # Insert data in batches
    batch_size = 1000
    for i in range(0, len(df_clean), batch_size):
        batch = df_clean.iloc[i : i + batch_size]
        records = batch.to_dict(orient="records")
        
        if records:
            cols = [f'"{c}"' for c in batch.columns]
            placeholders = ", ".join([f":{c}" for c in batch.columns])
            insert_sql = f'INSERT INTO "{table_name}" ({", ".join(cols)}) VALUES ({placeholders})'
            
            # Use executemany-style insertion
            for record in records:
                db.execute(text(insert_sql), record)
    
    # Create ttd_tables record
    table_record = Table(
        source_id=source.id,
        original_name=source.source_name or source.original_filename or "data",
        normalized_name=table_name,
        row_count=len(df),
        columns=columns,
    )
    
    db.add(table_record)
    db.commit()
    db.refresh(table_record)
    
    return table_record


def detect_relationships(
    db: Session,
    tables: list[Table],
) -> list[Relationship]:
    """
    Detect potential foreign key relationships between tables.
    
    Uses heuristics:
    1. Column name matching (e.g., customer_id -> customers.id)
    2. Value overlap analysis
    """
    relationships = []
    
    for from_table in tables:
        from_cols = from_table.columns or []
        
        for from_col in from_cols:
            from_col_name = from_col.get("name", "")
            
            # Look for _id suffix patterns
            if not from_col_name.endswith("_id"):
                continue
            
            # Extract potential target table name
            potential_target = from_col_name[:-3]  # Remove _id
            if potential_target.endswith("_"):
                potential_target = potential_target[:-1]
            
            # Look for matching table
            for to_table in tables:
                if to_table.id == from_table.id:
                    continue
                
                # Check if table name matches
                to_name = to_table.normalized_name.lower()
                if potential_target in to_name or to_name.rstrip("s") == potential_target:
                    # Look for id column in target
                    to_cols = to_table.columns or []
                    to_id_col = next(
                        (c for c in to_cols if c.get("name") in ("id", f"{potential_target}_id")),
                        None,
                    )
                    
                    if to_id_col:
                        rel = Relationship(
                            from_table_id=from_table.id,
                            from_column=from_col_name,
                            to_table_id=to_table.id,
                            to_column=to_id_col["name"],
                            confidence=0.8,  # Name-based match
                            user_confirmed=False,
                        )
                        db.add(rel)
                        relationships.append(rel)
    
    if relationships:
        db.commit()
    
    return relationships


def drop_normalized_table(db: Session, table: Table) -> None:
    """Drop the PostgreSQL table for a ttd_tables record."""
    db.execute(text(f'DROP TABLE IF EXISTS "{table.normalized_name}" CASCADE'))
    db.commit()
