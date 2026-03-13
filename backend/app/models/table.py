"""Table model - represents a normalized table in the system."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.relationship import Relationship
    from app.models.source import Source


class Table(Base, UUIDMixin, TimestampMixin):
    """
    Table entity.
    
    Represents a normalized table created from imported data.
    Stores column metadata and statistics.
    """

    __tablename__ = "ttd_tables"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ttd_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original table/file name before normalization",
    )
    normalized_name: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        unique=True,
        comment="PostgreSQL table name (sanitized)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated or user-provided description",
    )
    row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    columns: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Column metadata: name, type, nullable, stats",
    )
    data_semantic: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Auto-generated DATA SEMANTIC layer",
    )
    biz_semantic: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="User-provided BIZ SEMANTIC layer",
    )

    # Relationships
    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="tables",
    )
    relationships_from: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        foreign_keys="Relationship.from_table_id",
        back_populates="from_table",
        cascade="all, delete-orphan",
    )
    relationships_to: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        foreign_keys="Relationship.to_table_id",
        back_populates="to_table",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Table {self.normalized_name} ({self.row_count} rows)>"
