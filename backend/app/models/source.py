"""Data source model - represents CSV uploads or database connections."""

import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.table import Table


class SourceType(str, enum.Enum):
    """Type of data source."""

    CSV = "csv"
    DATABASE = "database"
    API = "api"


class Source(Base, UUIDMixin, TimestampMixin):
    """
    Data source entity.
    
    Represents either an uploaded file (CSV/Excel/Parquet) or a database connection.
    """

    __tablename__ = "ttd_sources"

    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    connection_info: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Encrypted connection details for database sources",
    )
    original_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Original filename for uploaded files",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )

    # Relationships
    tables: Mapped[list["Table"]] = relationship(
        "Table",
        back_populates="source",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Source {self.source_name} ({self.source_type.value})>"
