"""Tests for query_engine service."""

import pytest
from sqlalchemy.orm import Session

from app.services.query_engine import (
    QueryGenerationError,
    extract_sql,
    generate_sql,
    record_query,
)


class TestExtractSQL:
    """Tests for SQL extraction from LLM responses."""

    def test_extract_from_sql_code_block(self):
        """Test extraction from ```sql code block."""
        response = """Here's the query:
```sql
SELECT * FROM users WHERE id = 1;
```
This will return the user."""
        
        sql = extract_sql(response)
        assert sql == "SELECT * FROM users WHERE id = 1;"
    
    def test_extract_from_plain_code_block(self):
        """Test extraction from plain ``` code block."""
        response = """```
SELECT COUNT(*) FROM orders;
```"""
        
        sql = extract_sql(response)
        assert sql == "SELECT COUNT(*) FROM orders;"
    
    def test_extract_from_raw_select(self):
        """Test extraction when SELECT is in plain text."""
        response = "SELECT id, name FROM customers ORDER BY name;"
        
        sql = extract_sql(response)
        assert sql == "SELECT id, name FROM customers ORDER BY name;"
    
    def test_extract_with_explanation_after(self):
        """Test that explanation after SQL is not included."""
        response = """```sql
SELECT * FROM products LIMIT 10;
```

This query retrieves the first 10 products."""
        
        sql = extract_sql(response)
        assert sql == "SELECT * FROM products LIMIT 10;"
        assert "This query" not in sql
    
    def test_extract_multiline_sql(self):
        """Test extraction of multiline SQL."""
        response = """```sql
SELECT 
    c.name,
    COUNT(o.id) AS order_count
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.name
ORDER BY order_count DESC;
```"""
        
        sql = extract_sql(response)
        assert "SELECT" in sql
        assert "COUNT(o.id)" in sql
        assert "GROUP BY" in sql
    
    def test_extract_with_cte(self):
        """Test extraction of CTE (WITH clause)."""
        response = """```sql
WITH top_customers AS (
    SELECT customer_id, SUM(total) as revenue
    FROM orders
    GROUP BY customer_id
)
SELECT * FROM top_customers WHERE revenue > 1000;
```"""
        
        sql = extract_sql(response)
        assert sql.startswith("WITH")
        assert "top_customers" in sql
    
    def test_extract_fails_gracefully_on_garbage(self):
        """Test that garbage input doesn't crash."""
        response = "I don't know how to write that query."
        
        # Should return the response as-is (will fail validation later)
        sql = extract_sql(response)
        assert isinstance(sql, str)
    
    def test_extract_handles_lowercase_select(self):
        """Test case-insensitive SELECT detection."""
        response = "select * from users;"
        
        sql = extract_sql(response)
        assert "select" in sql.lower()


class TestGenerateSQL:
    """Tests for SQL generation (mocked LLM)."""
    
    def test_generate_sql_returns_tuple(self, db: Session, mocker):
        """Test that generate_sql returns (sql, metadata)."""
        # Mock the LLM call
        mocker.patch(
            "app.services.query_engine.llm_complete",
            return_value="```sql\nSELECT COUNT(*) FROM users;\n```"
        )
        
        sql, metadata = generate_sql(db, "How many users?")
        
        assert isinstance(sql, str)
        assert "SELECT" in sql
        assert isinstance(metadata, dict)
        assert "generation_time_ms" in metadata
    
    def test_generate_sql_raises_on_invalid_response(self, db: Session, mocker):
        """Test that non-SELECT responses raise QueryGenerationError."""
        mocker.patch(
            "app.services.query_engine.llm_complete",
            return_value="I don't understand that question."
        )
        
        with pytest.raises(QueryGenerationError):
            generate_sql(db, "What's the weather?")
    
    def test_generate_sql_raises_on_llm_failure(self, db: Session, mocker):
        """Test that LLM API failures are caught."""
        mocker.patch(
            "app.services.query_engine.llm_complete",
            side_effect=Exception("API rate limit")
        )
        
        with pytest.raises(QueryGenerationError, match="LLM generation failed"):
            generate_sql(db, "Show me data")
    
    def test_generate_sql_handles_ddl_in_response(self, db: Session, mocker):
        """Test that DDL statements are rejected."""
        mocker.patch(
            "app.services.query_engine.llm_complete",
            return_value="```sql\nDROP TABLE users;\n```"
        )
        
        with pytest.raises(QueryGenerationError):
            generate_sql(db, "Delete all users")


class TestRecordQuery:
    """Tests for query history recording."""
    
    def test_record_query_creates_history_entry(self, db: Session):
        """Test that queries are logged to database."""
        query = record_query(
            db,
            question="Test question?",
            generated_sql="SELECT * FROM test;",
            executed=False,
        )
        
        assert query.id is not None
        assert query.question == "Test question?"
        assert query.generated_sql == "SELECT * FROM test;"
        assert query.executed is False
    
    def test_record_query_with_execution_results(self, db: Session):
        """Test recording with execution metadata."""
        query = record_query(
            db,
            question="How many rows?",
            generated_sql="SELECT COUNT(*) FROM data;",
            executed=True,
            execution_success=True,
            row_count=42,
            execution_time_ms=150,
        )
        
        assert query.executed is True
        assert query.execution_success is True
        assert query.row_count == 42
        assert query.execution_time_ms == 150
    
    def test_record_query_with_error(self, db: Session):
        """Test recording failed query."""
        query = record_query(
            db,
            question="Bad query",
            generated_sql="INVALID SQL",
            executed=True,
            execution_success=False,
            error_message="syntax error",
        )
        
        assert query.execution_success is False
        assert query.error_message == "syntax error"


class TestSQLInjectionAttempts:
    """Test that SQL injection attempts are blocked."""
    
    @pytest.mark.parametrize("malicious_input", [
        "'; DROP TABLE users; --",
        "1 OR 1=1",
        "UNION SELECT password FROM admin",
        "; DELETE FROM orders WHERE 1=1; --",
        "1'; UPDATE users SET admin=1; --",
    ])
    def test_injection_attempts_fail_validation(self, malicious_input, db: Session, mocker):
        """Test that common injection patterns are rejected."""
        # Mock LLM to return the injection attempt
        mocker.patch(
            "app.services.query_engine.llm_complete",
            return_value=f"```sql\nSELECT * FROM users WHERE id = {malicious_input};\n```"
        )
        
        # Should raise QueryGenerationError or fail SQL validation
        with pytest.raises((QueryGenerationError, Exception)):
            generate_sql(db, malicious_input)
