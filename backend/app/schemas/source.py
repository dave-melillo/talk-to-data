"""Pydantic schemas for Source entity."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """Type of data source."""

    CSV = "csv"
    DATABASE = "database"
    API = "api"


class SourceBase(BaseModel):
    """Base schema for Source."""

    source_name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType
    description: Optional[str] = None


class SourceCreate(SourceBase):
    """Schema for creating a new Source."""

    connection_info: Optional[dict] = Field(
        None,
        description="Connection details for database sources",
    )
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None


class SourceUpdate(BaseModel):
    """Schema for updating a Source."""

    source_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class SourceRead(SourceBase):
    """Schema for reading a Source."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    table_count: int = Field(0, description="Number of tables from this source")


class SourceList(BaseModel):
    """Schema for listing sources."""

    sources: list[SourceRead]
    total: int
