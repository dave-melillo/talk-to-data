"""Initial schema - Sources, Tables, Relationships, QueryHistory

Revision ID: 001_initial
Revises: 
Create Date: 2026-03-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for source_type
    source_type = postgresql.ENUM("csv", "database", "api", name="sourcetype", create_type=False)
    source_type.create(op.get_bind(), checkfirst=True)

    # ttd_sources table
    op.create_table(
        "ttd_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("connection_info", postgresql.JSONB, nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # ttd_tables table
    op.create_table(
        "ttd_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ttd_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(63), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=False, default=0),
        sa.Column("columns", postgresql.JSONB, nullable=False, default=[]),
        sa.Column("data_semantic", postgresql.JSONB, nullable=True),
        sa.Column("biz_semantic", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ttd_tables_source_id", "ttd_tables", ["source_id"])

    # ttd_relationships table
    op.create_table(
        "ttd_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "from_table_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ttd_tables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_column", sa.String(255), nullable=False),
        sa.Column(
            "to_table_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ttd_tables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("to_column", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, default=0.0),
        sa.Column("user_confirmed", sa.Boolean, nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ttd_relationships_from_table", "ttd_relationships", ["from_table_id"])
    op.create_index("ix_ttd_relationships_to_table", "ttd_relationships", ["to_table_id"])

    # ttd_query_history table
    op.create_table(
        "ttd_query_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("generated_sql", sa.Text, nullable=False),
        sa.Column("executed", sa.Boolean, nullable=False, default=False),
        sa.Column("execution_success", sa.Boolean, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("execution_time_ms", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("llm_provider", sa.Text, nullable=True),
        sa.Column("llm_model", sa.Text, nullable=True),
        sa.Column("context_used", postgresql.JSONB, nullable=True),
        sa.Column("user_feedback", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ttd_query_history_created_at", "ttd_query_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("ttd_query_history")
    op.drop_table("ttd_relationships")
    op.drop_table("ttd_tables")
    op.drop_table("ttd_sources")
    op.execute("DROP TYPE IF EXISTS sourcetype")
