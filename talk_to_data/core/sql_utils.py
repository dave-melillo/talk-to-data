"""Shared SQL utilities: extraction and validation.

This is the single source of truth for SQL parsing and safety checks,
used by both the CLI (talk_to_data/generator.py) and the backend
(backend/app/services/query_engine.py).
"""

import re
from typing import Any


def extract_sql(response: str) -> str:
    """
    Extract SQL query from LLM response.

    Handles various formats:
    - SQL inside ```sql code blocks
    - SQL inside ``` code blocks
    - Raw SQL starting with SELECT/WITH
    - Falls back to full response
    """
    # Try ```sql block first
    sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()

    # Try plain ``` block
    sql_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()

    # Try looking for SELECT or WITH
    sql_match = re.search(
        r'((?:SELECT|WITH)\s+.*?)(?:\n\n|$)', response, re.DOTALL | re.IGNORECASE
    )
    if sql_match:
        return sql_match.group(1).strip()

    # Just return the whole thing
    return response.strip()


def parse_llm_response(response_text: str) -> dict[str, Any]:
    """
    Parse a structured LLM response into sql, explanation, and confidence.

    Expects the response to contain:
    - SQL in a ```sql block
    - EXPLANATION: ...
    - CONFIDENCE: high/medium/low
    """
    sql = extract_sql(response_text)

    explanation_match = re.search(
        r'EXPLANATION:\s*(.+?)(?=CONFIDENCE:|$)', response_text, re.DOTALL
    )
    explanation = explanation_match.group(1).strip() if explanation_match else ""

    confidence_match = re.search(
        r'CONFIDENCE:\s*(high|medium|low)', response_text, re.IGNORECASE
    )
    confidence = confidence_match.group(1).lower() if confidence_match else "medium"

    return {
        "sql": sql,
        "explanation": explanation,
        "confidence": confidence,
        "raw_response": response_text,
    }


# Dangerous keywords to block (read-only queries only)
BLOCKED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
    "ALTER", "CREATE", "MERGE", "UPSERT",
    "EXEC", "EXECUTE", "GRANT", "REVOKE",
]


def validate_sql(sql: str, dialect: str = "sqlite") -> dict[str, Any]:
    """
    Basic SQL validation (safety + syntax check).

    Returns dict with 'valid' bool and 'error' message if invalid.
    """
    sql_upper = sql.upper().strip()

    if not sql_upper:
        return {"valid": False, "error": "Empty SQL query"}

    # Must start with valid SQL keyword
    valid_starts = ["SELECT", "WITH", "EXPLAIN"]
    if not any(sql_upper.startswith(kw) for kw in valid_starts):
        return {"valid": False, "error": "Query must start with SELECT or WITH"}

    # Check for balanced parentheses
    if sql.count("(") != sql.count(")"):
        return {"valid": False, "error": "Unbalanced parentheses"}

    # Check for dangerous operations (we only allow SELECT)
    for kw in BLOCKED_KEYWORDS:
        pattern = rf"\b{kw}\b"
        if re.search(pattern, sql_upper):
            return {"valid": False, "error": f"Dangerous operation not allowed: {kw}"}

    return {"valid": True, "error": None}
