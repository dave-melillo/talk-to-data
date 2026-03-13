"""Pydantic schemas for Relationship entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RelationshipBase(BaseModel):
    """Base schema for Relationship."""

    from_table_id: UUID
    from_column: str = Field(..., min_length=1, max_length=255)
    to_table_id: UUID
    to_column: str = Field(..., min_length=1, max_length=255)


class RelationshipCreate(RelationshipBase):
    """Schema for creating a new Relationship."""

    confidence: float = Field(0.0, ge=0.0, le=1.0)
    user_confirmed: bool = False


class RelationshipUpdate(BaseModel):
    """Schema for updating a Relationship."""

    confidence: float | None = Field(None, ge=0.0, le=1.0)
    user_confirmed: bool | None = None


class RelationshipRead(RelationshipBase):
    """Schema for reading a Relationship."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    confidence: float
    user_confirmed: bool
    created_at: datetime
    updated_at: datetime

    # Denormalized for convenience
    from_table_name: str | None = None
    to_table_name: str | None = None


class RelationshipList(BaseModel):
    """Schema for listing relationships."""

    relationships: list[RelationshipRead]
    total: int
