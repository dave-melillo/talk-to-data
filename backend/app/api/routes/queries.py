"""Query endpoints - NL-to-SQL generation and execution."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.query import QueryHistory
from app.services.query_engine import (
    QueryGenerationError,
    generate_sql,
    record_query,
)
from app.services.sql_validator import SQLValidationError, safe_execute, validate_sql

router = APIRouter()


class ConversationEntry(BaseModel):
    """A previous question/answer pair from the conversation."""

    question: str
    sql: str
    success: bool = True


class QueryRequest(BaseModel):
    """Request to generate SQL from natural language."""

    question: str = Field(..., min_length=1, max_length=2000)
    execute: bool = Field(True, description="Execute the generated SQL")
    llm_provider: str | None = None
    llm_model: str | None = None
    conversation_history: list[ConversationEntry] = Field(
        default_factory=list,
        description="Recent conversation Q&A pairs for multi-turn context",
    )


class QueryResponse(BaseModel):
    """Response with generated SQL and optional results."""

    query_id: UUID
    question: str
    generated_sql: str
    executed: bool
    success: bool | None = None
    row_count: int | None = None
    execution_time_ms: int | None = None
    columns: list[str] | None = None
    data: list[dict[str, Any]] | None = None
    error: str | None = None


@router.post("/generate", response_model=QueryResponse)
async def generate_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """
    Generate SQL from natural language question.
    
    Optionally executes the query and returns results.
    """
    # Generate SQL
    try:
        sql, metadata = generate_sql(
            db,
            request.question,
            provider=request.llm_provider,
            model=request.llm_model,
            conversation_history=[
                entry.model_dump() for entry in request.conversation_history
            ],
        )
    except QueryGenerationError as e:
        # Record failed generation
        query = record_query(
            db,
            question=request.question,
            generated_sql="-- GENERATION FAILED",
            executed=False,
            error_message=str(e),
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
        )
        raise HTTPException(status_code=500, detail=str(e))
    
    # Record the query
    query = record_query(
        db,
        question=request.question,
        generated_sql=sql,
        executed=False,
        llm_provider=metadata.get("provider"),
        llm_model=metadata.get("model"),
        context_used=metadata,
    )
    
    # Execute if requested
    result_data: list[dict[str, Any]] = []
    columns: list[str] = []
    execution_success: bool | None = None
    row_count: int | None = None
    error: str | None = None
    exec_time_ms: int | None = None
    
    if request.execute:
        import time
        
        exec_start = time.time()
        try:
            result = db.execute(text(sql))
            exec_time_ms = int((time.time() - exec_start) * 1000)
            
            # Get column names
            columns = list(result.keys())
            
            # Fetch results (with limit)
            rows = result.fetchall()
            row_count = len(rows)
            
            # Convert to dicts
            result_data = [dict(row._mapping) for row in rows[:100]]  # Limit for response
            execution_success = True
            
        except Exception as e:
            exec_time_ms = int((time.time() - exec_start) * 1000)
            execution_success = False
            error = str(e)
        
        # Update query record
        query.executed = True
        query.execution_success = execution_success
        query.row_count = row_count
        query.execution_time_ms = exec_time_ms
        query.error_message = error
        db.commit()
    
    return QueryResponse(
        query_id=query.id,
        question=request.question,
        generated_sql=sql,
        executed=request.execute,
        success=execution_success,
        row_count=row_count,
        execution_time_ms=exec_time_ms,
        columns=columns if columns else None,
        data=result_data if result_data else None,
        error=error,
    )


@router.get("/{query_id}")
async def get_query(
    query_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific query from history."""
    query = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    return {
        "id": str(query.id),
        "question": query.question,
        "generated_sql": query.generated_sql,
        "executed": query.executed,
        "execution_success": query.execution_success,
        "row_count": query.row_count,
        "execution_time_ms": query.execution_time_ms,
        "error_message": query.error_message,
        "llm_provider": query.llm_provider,
        "llm_model": query.llm_model,
        "created_at": query.created_at.isoformat() if query.created_at else None,
    }


@router.get("/history/recent")
async def get_recent_queries(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get recent queries."""
    queries = (
        db.query(QueryHistory)
        .order_by(QueryHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return {
        "queries": [
            {
                "id": str(q.id),
                "question": q.question,
                "executed": q.executed,
                "execution_success": q.execution_success,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in queries
        ],
        "total": len(queries),
    }


@router.post("/{query_id}/feedback")
async def submit_feedback(
    query_id: UUID,
    feedback: str,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Submit feedback on a query."""
    query = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    query.user_feedback = feedback
    db.commit()
    
    return {"status": "feedback recorded"}


@router.post("/validate")
async def validate_query_sql(
    sql: str,
    check_tables: bool = True,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Validate SQL without executing.
    
    Checks for:
    - Blocked keywords (DDL/DML)
    - Valid SQL syntax
    - Table existence (optional)
    """
    result = validate_sql(sql, db if check_tables else None, check_tables)
    return result


@router.post("/execute-safe")
async def execute_sql_safe(
    sql: str,
    limit: int = 1000,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Execute SQL with safety checks.
    
    Validates SQL before execution and adds LIMIT if needed.
    """
    try:
        result = safe_execute(sql, db, limit=limit)
        return result
    except SQLValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
