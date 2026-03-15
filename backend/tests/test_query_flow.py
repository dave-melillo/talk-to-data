"""Integration tests for the full NL → SQL → validation → execution → results flow."""

from unittest.mock import patch

import pytest

from app.services.query_engine import extract_sql, generate_sql, record_query
from app.services.sql_validator import SQLValidationError, safe_execute, validate_sql


class TestExtractSQL:
    """Test SQL extraction from LLM responses."""

    def test_extract_from_sql_code_block(self):
        response = "Here is the query:\n```sql\nSELECT COUNT(*) FROM users\n```"
        assert extract_sql(response) == "SELECT COUNT(*) FROM users"

    def test_extract_from_plain_code_block(self):
        response = "```\nSELECT * FROM orders\n```"
        assert extract_sql(response) == "SELECT * FROM orders"

    def test_extract_raw_select(self):
        response = "SELECT name FROM customers WHERE id = 1"
        result = extract_sql(response)
        assert "SELECT" in result
        assert "customers" in result

    def test_extract_multiline_sql(self):
        response = """```sql
SELECT
    c.name,
    COUNT(o.id) AS order_count
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.name
```"""
        sql = extract_sql(response)
        assert "SELECT" in sql
        assert "JOIN" in sql
        assert "GROUP BY" in sql

    def test_extract_from_garbage_returns_raw(self):
        response = "I don't know how to help with that."
        result = extract_sql(response)
        assert result == response.strip()


class TestGenerateSQL:
    """Test SQL generation with mocked LLM."""

    def test_generate_simple_count(self, db, sample_customers_table, mock_llm_select_count):
        sql, metadata = generate_sql(db, "How many customers are there?")

        assert "SELECT" in sql.upper()
        assert "COUNT" in sql.upper()
        assert "test_customers" in sql.lower()
        assert "provider" in metadata
        assert "generation_time_ms" in metadata

    def test_generate_sum_query(self, db, sample_orders_table, mock_llm_select_sum):
        sql, metadata = generate_sql(db, "What is the total revenue?")

        assert "SUM" in sql.upper()
        assert "test_orders" in sql.lower()

    def test_generate_bad_response_raises(self, db, sample_customers_table, mock_llm_bad_sql):
        from app.services.query_engine import QueryGenerationError

        with pytest.raises(QueryGenerationError):
            generate_sql(db, "Something nonsensical")

    def test_generate_with_provider_override(self, db, sample_customers_table):
        with patch("app.services.query_engine.llm_complete") as mock:
            mock.return_value = "```sql\nSELECT 1\n```"
            sql, metadata = generate_sql(
                db, "test", provider="openai", model="gpt-4o"
            )

            assert metadata["provider"] == "openai"
            assert metadata["model"] == "gpt-4o"


class TestQueryFlow:
    """Test full flow: question → SQL generation → validation → execution → results."""

    def test_full_flow_count(self, db, sample_customers_table, mock_llm_select_count):
        """Test: NL question → valid SQL → results."""
        # Step 1: Generate SQL
        sql, metadata = generate_sql(db, "How many customers are there?")
        assert sql.upper().startswith("SELECT")

        # Step 2: Validate
        validation = validate_sql(sql, db)
        assert validation["valid"]

        # Step 3: Execute
        result = safe_execute(sql, db)
        assert result["row_count"] == 1
        assert result["columns"] == ["customer_count"]
        assert result["rows"][0]["customer_count"] == 3

    def test_full_flow_sum(self, db, sample_orders_table, mock_llm_select_sum):
        """Test: Aggregation query with filter."""
        sql, metadata = generate_sql(db, "What is the total revenue?")

        validation = validate_sql(sql, db)
        assert validation["valid"]

        result = safe_execute(sql, db)
        assert result["row_count"] == 1
        assert result["rows"][0]["total_revenue"] == pytest.approx(149.49)

    def test_full_flow_with_recording(
        self, db, sample_customers_table, mock_llm_select_count
    ):
        """Test: Full flow including query history recording."""
        question = "How many customers?"
        sql, metadata = generate_sql(db, question)

        result = safe_execute(sql, db)

        # Record the query
        record = record_query(
            db,
            question=question,
            generated_sql=sql,
            executed=True,
            execution_success=True,
            row_count=result["row_count"],
            llm_provider=metadata["provider"],
            llm_model=metadata["model"],
        )
        assert record.id is not None
        assert record.question == question
        assert record.executed is True
        assert record.execution_success is True

    def test_flow_blocked_sql_rejected(self, db):
        """Test: Dangerous SQL is blocked at validation."""
        validation = validate_sql("DROP TABLE customers", db)
        assert not validation["valid"]
        assert validation["errors"][0]["type"] == "BLOCKED_KEYWORD"

    def test_flow_safe_execute_rejects_invalid(self, db):
        """Test: safe_execute raises on invalid SQL."""
        with pytest.raises(SQLValidationError) as exc_info:
            safe_execute("DELETE FROM customers", db)
        assert exc_info.value.violation == "BLOCKED_KEYWORD"


class TestRecordQuery:
    """Test query history recording."""

    def test_record_basic_query(self, db):
        record = record_query(
            db,
            question="How many users?",
            generated_sql="SELECT COUNT(*) FROM users",
        )
        assert record.id is not None
        assert record.question == "How many users?"
        assert record.generated_sql == "SELECT COUNT(*) FROM users"
        assert record.executed is False

    def test_record_executed_query(self, db):
        record = record_query(
            db,
            question="test",
            generated_sql="SELECT 1",
            executed=True,
            execution_success=True,
            row_count=1,
            execution_time_ms=42,
            llm_provider="anthropic",
            llm_model="claude-sonnet-4-20250514",
        )
        assert record.executed is True
        assert record.execution_success is True
        assert record.row_count == 1
        assert record.execution_time_ms == 42

    def test_record_failed_query(self, db):
        record = record_query(
            db,
            question="test",
            generated_sql="SELECT invalid",
            executed=True,
            execution_success=False,
            error_message="column 'invalid' not found",
        )
        assert record.execution_success is False
        assert record.error_message == "column 'invalid' not found"
