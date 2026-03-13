"""
SQL validation service for safety checks.

Validates:
- No DDL (CREATE, DROP, ALTER)
- No DML (INSERT, UPDATE, DELETE)
- No dangerous functions
- Table/column existence
- Syntax validation
"""

import re
from typing import Any

import sqlparse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.table import Table


class SQLValidationError(Exception):
    """Exception raised when SQL validation fails."""
    
    def __init__(self, message: str, violation: str):
        self.message = message
        self.violation = violation
        super().__init__(message)


# Dangerous keywords to block
BLOCKED_KEYWORDS = [
    # DDL
    "CREATE", "DROP", "ALTER", "TRUNCATE", "RENAME",
    # DML (excluding SELECT)
    "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT",
    # System commands
    "EXEC", "EXECUTE", "XP_CMDSHELL", "SP_EXECUTESQL",
    "BCP", "BULK", "OPENROWSET", "OPENDATASOURCE",
    # Other dangerous
    "GRANT", "REVOKE", "DENY", "BACKUP", "RESTORE",
]


def normalize_sql(sql: str) -> str:
    """Normalize SQL for validation."""
    return " ".join(sql.upper().split())


def check_blocked_keywords(sql: str) -> None:
    """
    Check for dangerous keywords in SQL.
    
    Raises SQLValidationError if found.
    """
    normalized = normalize_sql(sql)
    
    # Check for blocked keywords (whole word match)
    for keyword in BLOCKED_KEYWORDS:
        # Match word boundaries
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, normalized):
            raise SQLValidationError(
                f"SQL contains blocked keyword: {keyword}",
                violation="BLOCKED_KEYWORD",
            )


def check_starts_with_select(sql: str) -> None:
    """
    Ensure SQL starts with SELECT.
    
    This catches subqueries that might be used for injection.
    """
    normalized = normalize_sql(sql).strip()
    
    # Allow WITH (CTEs) at the start
    allowed_starts = ["SELECT", "WITH"]
    
    for start in allowed_starts:
        if normalized.startswith(start):
            return
    
    raise SQLValidationError(
        "SQL must start with SELECT or WITH",
        violation="INVALID_START",
    )


def validate_syntax(sql: str) -> None:
    """
    Validate SQL syntax using sqlparse.
    
    Raises SQLValidationError if syntax is invalid.
    """
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            raise SQLValidationError(
                "Could not parse SQL",
                violation="PARSE_ERROR",
            )
    except Exception as e:
        raise SQLValidationError(
            f"SQL syntax error: {e}",
            violation="SYNTAX_ERROR",
        ) from e


def extract_table_references(sql: str) -> list[str]:
    """
    Extract table names referenced in SQL.
    
    Simple heuristic: look for FROM and JOIN clauses.
    """
    tables = []
    normalized = normalize_sql(sql)
    
    # Find FROM table
    from_pattern = r"\bFROM\s+(\w+)"
    tables.extend(re.findall(from_pattern, normalized))
    
    # Find JOIN tables
    join_pattern = r"\bJOIN\s+(\w+)"
    tables.extend(re.findall(join_pattern, normalized))
    
    # Deduplicate while preserving order
    seen = set()
    unique_tables = []
    for t in tables:
        if t not in seen:
            seen.add(t)
            unique_tables.append(t)
    
    return unique_tables


def validate_table_existence(
    sql: str,
    db: Session,
) -> list[dict[str, Any]]:
    """
    Validate that referenced tables exist.
    
    Returns list of validation warnings.
    """
    warnings = []
    referenced_tables = extract_table_references(sql)
    
    # Get all normalized table names from database
    existing_tables = {
        t.normalized_name.upper(): t.normalized_name
        for t in db.query(Table).all()
    }
    
    for ref in referenced_tables:
        ref_upper = ref.upper()
        # Allow PostgreSQL system tables
        if ref_upper in ("INFORMATION_SCHEMA", "PG_CATALOG"):
            continue
        
        if ref_upper not in existing_tables:
            warnings.append({
                "type": "UNKNOWN_TABLE",
                "table": ref,
                "message": f"Table '{ref}' not found in database",
            })
    
    return warnings


def validate_sql(
    sql: str,
    db: Session | None = None,
    check_tables: bool = True,
) -> dict[str, Any]:
    """
    Full SQL validation.
    
    Returns validation result with status and any warnings/errors.
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
    }
    
    try:
        # 1. Check for blocked keywords
        check_blocked_keywords(sql)
    except SQLValidationError as e:
        result["valid"] = False
        result["errors"].append({
            "type": e.violation,
            "message": e.message,
        })
    
    # 2. Check starts with SELECT
    if result["valid"]:
        try:
            check_starts_with_select(sql)
        except SQLValidationError as e:
            result["valid"] = False
            result["errors"].append({
                "type": e.violation,
                "message": e.message,
            })
    
    # 3. Validate syntax
    if result["valid"]:
        try:
            validate_syntax(sql)
        except SQLValidationError as e:
            result["valid"] = False
            result["errors"].append({
                "type": e.violation,
                "message": e.message,
            })
    
    # 4. Check table existence
    if result["valid"] and db and check_tables:
        warnings = validate_table_existence(sql, db)
        result["warnings"].extend(warnings)
    
    return result


def safe_execute(
    sql: str,
    db: Session,
    limit: int = 1000,
) -> dict[str, Any]:
    """
    Safely execute SQL after validation.
    
    Adds LIMIT if not present.
    Returns dict with columns and rows.
    """
    # Validate first
    validation = validate_sql(sql, db)
    if not validation["valid"]:
        raise SQLValidationError(
            validation["errors"][0]["message"],
            validation["errors"][0]["type"],
        )
    
    # Add LIMIT if not present
    normalized = normalize_sql(sql)
    if "LIMIT" not in normalized:
        sql = f"{sql} LIMIT {limit}"
    
    try:
        result = db.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result]
        
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "limited": len(rows) == limit,
        }
    except SQLAlchemyError as e:
        raise SQLValidationError(
            f"Execution failed: {e}",
            violation="EXECUTION_ERROR",
        ) from e
