"""
Query engine service for NL-to-SQL generation.

Handles:
- Prompt assembly
- LLM completion
- SQL extraction
- Query recording
"""

import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.query import QueryHistory
from app.services.context_assembler import assemble_query_prompt
from app.services.llm import llm_complete

settings = get_settings()


class QueryGenerationError(Exception):
    """Exception raised when query generation fails."""

    pass


def extract_sql(response: str) -> str:
    """
    Extract SQL query from LLM response.
    
    Handles various formats:
    - SQL inside ```sql code blocks
    - SQL inside ``` code blocks
    - Raw SQL
    """
    # Try ```sql block first
    sql_match = re.search(r'```sql\n(.*?)```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Try plain ``` block
    sql_match = re.search(r'```\n(.*?)```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Try looking for SELECT
    sql_match = re.search(r'(SELECT\s+.*?)(?:\n\n|$)', response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Just return the whole thing, might need manual cleanup
    return response.strip()


def generate_sql(
    db: Session,
    question: str,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Generate SQL from natural language question.
    
    Returns:
        Tuple of (generated_sql, metadata_dict)
    """
    # Assemble prompt
    prompt = assemble_query_prompt(db, question)
    
    # Get LLM response
    start_time = time.time()
    try:
        response = llm_complete(
            prompt=prompt,
            provider=provider or settings.default_llm_provider,
            model=model or settings.default_llm_model,
            max_tokens=2000,
            temperature=0.2,  # Low temp for deterministic SQL
        )
        generation_time_ms = int((time.time() - start_time) * 1000)
    except Exception as e:
        raise QueryGenerationError(f"LLM generation failed: {e}") from e
    
    # Extract SQL
    sql = extract_sql(response)
    
    if not sql or not sql.upper().startswith("SELECT"):
        raise QueryGenerationError(f"Failed to generate valid SQL. Response: {response[:200]}")
    
    metadata = {
        "prompt_tokens": len(prompt) // 4,  # Rough estimate
        "response_tokens": len(response) // 4,
        "generation_time_ms": generation_time_ms,
        "provider": provider or settings.default_llm_provider,
        "model": model or settings.default_llm_model,
    }
    
    return sql, metadata


def record_query(
    db: Session,
    question: str,
    generated_sql: str,
    executed: bool = False,
    execution_success: bool | None = None,
    row_count: int | None = None,
    execution_time_ms: int | None = None,
    error_message: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    context_used: dict[str, Any] | None = None,
) -> QueryHistory:
    """
    Record a query in the history.
    """
    query = QueryHistory(
        question=question,
        generated_sql=generated_sql,
        executed=executed,
        execution_success=execution_success,
        row_count=row_count,
        execution_time_ms=execution_time_ms,
        error_message=error_message,
        llm_provider=llm_provider,
        llm_model=llm_model,
        context_used=context_used,
    )
    
    db.add(query)
    db.commit()
    db.refresh(query)
    
    return query
