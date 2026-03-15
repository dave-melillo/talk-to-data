"""Tests for context_assembler service."""

import pytest
from sqlalchemy.orm import Session

from app.models.table import Table
from app.services.context_assembler import (
    assemble_context,
    estimate_tokens,
    format_prompt,
    truncate_schema_semantically,
)


class TestEstimateTokens:
    """Tests for token estimation."""
    
    def test_estimate_short_text(self):
        """Test token estimation for short text."""
        text = "SELECT * FROM users;"
        tokens = estimate_tokens(text)
        # Should be roughly len / 3
        assert 5 <= tokens <= 10
    
    def test_estimate_structured_text(self):
        """Test estimation for structured text (markdown table)."""
        text = """| Column | Type | Description |
|--------|------|-------------|
| id     | INT  | Primary key |
| name   | TEXT | User name   |"""
        
        tokens = estimate_tokens(text)
        # Structured text is denser
        assert tokens > 0
    
    def test_estimate_empty_text(self):
        """Test that empty string returns 0."""
        assert estimate_tokens("") == 0


class TestTruncateSchemaSeantically:
    """Tests for semantic schema truncation."""
    
    def test_truncate_keeps_mentioned_tables(self, db: Session):
        """Test that tables mentioned in question are prioritized."""
        # Create mock tables
        users = Table(
            normalized_name="users",
            original_name="users",
            row_count=100,
            columns=[
                {"name": "id", "data_type": "INT"},
                {"name": "name", "data_type": "TEXT"},
            ],
            data_semantic={"table": {"description": "User data"}},
        )
        orders = Table(
            normalized_name="orders",
            original_name="orders",
            row_count=500,
            columns=[{"name": "id", "data_type": "INT"}],
            data_semantic={"table": {"description": "Order data"}},
        )
        
        question = "How many users are there?"
        
        # With very low budget, should keep "users" table
        schema = truncate_schema_semantically(
            db, [users, orders], question, max_tokens=100
        )
        
        assert "users" in schema.lower()
        # May or may not include orders depending on space
    
    def test_truncate_drops_tables_cleanly(self, db: Session):
        """Test that truncation never leaves partial tables."""
        # Create 10 large tables
        tables = []
        for i in range(10):
            table = Table(
                normalized_name=f"table_{i}",
                original_name=f"table_{i}",
                row_count=1000,
                columns=[
                    {"name": f"col_{j}", "data_type": "TEXT"}
                    for j in range(20)  # 20 columns each
                ],
                data_semantic={"table": {"description": f"Table {i}"}},
            )
            tables.append(table)
        
        question = "Show me data"
        
        # Low budget should drop entire tables
        schema = truncate_schema_semantically(db, tables, question, max_tokens=500)
        
        # Verify no truncated table structures (should be valid markdown)
        assert "###" in schema  # Has table headers
        assert "|" in schema    # Has column rows
        # Should not have cut-off lines
        lines = schema.split("\n")
        for line in lines:
            if line.startswith("|"):
                # Every column row should be complete (no dangling |)
                assert line.count("|") >= 3  # At least | col | type | desc |
    
    def test_truncate_with_empty_question(self, db: Session):
        """Test truncation with generic question."""
        tables = [
            Table(
                normalized_name="data",
                original_name="data",
                row_count=100,
                columns=[{"name": "id", "data_type": "INT"}],
                data_semantic={"table": {"description": "Data"}},
            )
        ]
        
        schema = truncate_schema_semantically(db, tables, "", max_tokens=200)
        assert "data" in schema.lower()


class TestAssembleContext:
    """Tests for full context assembly."""
    
    def test_assemble_includes_all_sections(self, db: Session, mocker):
        """Test that context includes schema, business, and examples."""
        # Mock schema generation
        mocker.patch(
            "app.services.context_assembler.generate_schema_summary",
            return_value="### users\n| id | INT |"
        )
        mocker.patch(
            "app.services.context_assembler.format_biz_semantic_for_context",
            return_value="## Business Context\n- Active = >90 days"
        )
        
        context = assemble_context(db, "Test question?", tables=[], include_examples=True)
        
        assert "schema" in context
        assert "business_context" in context
        assert "examples" in context
        assert context["question"] == "Test question?"
    
    def test_assemble_truncates_when_needed(self, db: Session, mocker):
        """Test that context is truncated if it exceeds max tokens."""
        # Generate massive schema
        huge_schema = "### table\n" + "| col | TEXT |\n" * 1000
        
        mocker.patch(
            "app.services.context_assembler.generate_schema_summary",
            return_value=huge_schema
        )
        mocker.patch(
            "app.services.context_assembler.format_biz_semantic_for_context",
            return_value=""
        )
        
        context = assemble_context(
            db, "Test?", tables=[], max_context_tokens=500
        )
        
        # Schema should be truncated
        schema_tokens = estimate_tokens(context["schema"])
        assert schema_tokens <= 500
    
    def test_assemble_prioritizes_business_context(self, db: Session, mocker):
        """Test that business context is never truncated."""
        biz = "## Business Context\nCritical info that must be preserved."
        
        mocker.patch(
            "app.services.context_assembler.generate_schema_summary",
            return_value="### huge\n" + "| col | TEXT |\n" * 500
        )
        mocker.patch(
            "app.services.context_assembler.format_biz_semantic_for_context",
            return_value=biz
        )
        
        context = assemble_context(db, "Test?", tables=[], max_context_tokens=200)
        
        # Business context should be intact
        assert context["business_context"] == biz


class TestFormatPrompt:
    """Tests for prompt formatting."""
    
    def test_format_includes_all_parts(self):
        """Test that formatted prompt has all sections."""
        context = {
            "schema": "### users",
            "business_context": "## Business\nGlossary here",
            "examples": "## Examples\nExample 1",
            "question": "How many users?",
        }
        
        prompt = format_prompt(context)
        
        assert "### users" in prompt
        assert "## Business" in prompt
        assert "## Examples" in prompt
        assert "How many users?" in prompt
        assert "## Instructions" in prompt
    
    def test_format_handles_empty_business_context(self):
        """Test prompt with no business context."""
        context = {
            "schema": "### data",
            "business_context": "",
            "examples": "",
            "question": "Show data",
        }
        
        prompt = format_prompt(context)
        assert "Show data" in prompt
