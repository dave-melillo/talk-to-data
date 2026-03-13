"""Pydantic schemas for Table entity."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ColumnInfo(BaseModel):
    """Schema for column metadata."""

    name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    is_unique: bool = False
    sample_values: list[Any] = Field(default_factory=list)
    distinct_count: Optional[int] = None
    null_count: Optional[int] = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None


class TableBase(BaseModel):
    """Base schema for Table."""

    original_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TableCreate(TableBase):
    """Schema for creating a new Table."""

    source_id: UUID
    normalized_name: str = Field(..., min_length=1, max_length=63)
    row_count: int = 0
    columns: list[ColumnInfo] = Field(default_factory=list)


class TableUpdate(BaseModel):
    """Schema for updating a Table."""

    description: Optional[str] = None
    data_semantic: Optional[dict] = None
    biz_semantic: Optional[dict] = None


class TableRead(TableBase):
    """Schema for reading a Table."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    normalized_name: str
    row_count: int
    columns: list[ColumnInfo]
    data_semantic: Optional[dict] = None
    biz_semantic: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class TableList(BaseModel):
    """Schema for listing tables."""

    tables: list[TableRead]
    total: int
