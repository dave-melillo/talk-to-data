"""Relationship model - represents detected or user-defined table relationships."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.table import Table


class Relationship(Base, UUIDMixin, TimestampMixin):
    """
    Table relationship entity.
    
    Represents a foreign key relationship between tables,
    either auto-detected or user-confirmed.
    """

    __tablename__ = "ttd_relationships"

    from_table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ttd_tables.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_column: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    to_table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ttd_tables.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_column: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="AI confidence score 0-1",
    )
    user_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Has user verified this relationship?",
    )

    # Relationships
    from_table: Mapped["Table"] = relationship(
        "Table",
        foreign_keys=[from_table_id],
        back_populates="relationships_from",
    )
    to_table: Mapped["Table"] = relationship(
        "Table",
        foreign_keys=[to_table_id],
        back_populates="relationships_to",
    )

    def __repr__(self) -> str:
        return f"<Relationship {self.from_column} -> {self.to_column} ({self.confidence:.0%})>"
