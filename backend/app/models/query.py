"""Query history model - tracks all generated and executed queries."""

from typing import Optional

from sqlalchemy import Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class QueryHistory(Base, UUIDMixin, TimestampMixin):
    """
    Query history entity.
    
    Tracks all natural language questions, generated SQL,
    and execution results for learning and auditing.
    """

    __tablename__ = "ttd_query_history"

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Natural language question from user",
    )
    generated_sql: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AI-generated SQL query",
    )
    executed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Was the query executed?",
    )
    execution_success: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Did execution succeed?",
    )
    row_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of rows returned",
    )
    execution_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Query execution time in milliseconds",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if execution failed",
    )
    llm_provider: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="LLM provider used (anthropic, openai, etc.)",
    )
    llm_model: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="LLM model used",
    )
    context_used: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Context sent to LLM (for debugging)",
    )
    user_feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User feedback on query quality",
    )

    def __repr__(self) -> str:
        status = "✓" if self.execution_success else "✗" if self.executed else "?"
        return f"<Query {status} '{self.question[:30]}...'>"
