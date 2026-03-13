"""Pydantic schemas for Query entity."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QueryBase(BaseModel):
    """Base schema for Query."""

    question: str = Field(..., min_length=1, max_length=2000)


class QueryCreate(QueryBase):
    """Schema for creating a new Query record."""

    generated_sql: str
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    context_used: Optional[dict] = None


class QueryExecuteRequest(BaseModel):
    """Schema for executing a natural language query."""

    question: str = Field(..., min_length=1, max_length=2000)
    execute: bool = Field(True, description="Whether to execute the generated SQL")
    llm_provider: Optional[str] = Field(None, description="Override default LLM provider")
    llm_model: Optional[str] = Field(None, description="Override default LLM model")


class QueryExecuteResponse(BaseModel):
    """Schema for query execution response."""

    query_id: UUID
    question: str
    generated_sql: str
    executed: bool
    success: Optional[bool] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[int] = None
    columns: Optional[list[str]] = None
    data: Optional[list[dict[str, Any]]] = None
    error: Optional[str] = None


class QueryRead(QueryBase):
    """Schema for reading a Query record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    generated_sql: str
    executed: bool
    execution_success: Optional[bool] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    user_feedback: Optional[str] = None
    created_at: datetime


class QueryList(BaseModel):
    """Schema for listing queries."""

    queries: list[QueryRead]
    total: int


class QueryFeedback(BaseModel):
    """Schema for submitting query feedback."""

    feedback: str = Field(..., min_length=1, max_length=1000)
