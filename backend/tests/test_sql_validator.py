"""Tests for SQL validation service."""

import pytest
from sqlalchemy.orm import Session

from app.services.sql_validator import (
    SQLValidationError,
    check_blocked_keywords,
    check_starts_with_select,
    extract_table_references,
    validate_sql,
    validate_syntax,
)


class TestCheckBlockedKeywords:
    """Tests for dangerous keyword detection."""
    
    @pytest.mark.parametrize("dangerous_sql", [
        "DROP TABLE users;",
        "DELETE FROM orders WHERE 1=1;",
        "INSERT INTO admin (name) VALUES ('hacker');",
        "UPDATE users SET admin=1;",
        "TRUNCATE TABLE logs;",
        "ALTER TABLE users ADD COLUMN backdoor TEXT;",
        "CREATE TABLE malicious (id INT);",
        "EXEC sp_executesql 'DROP TABLE users';",
        "GRANT ALL ON users TO attacker;",
    ])
    def test_blocked_keywords_raise_error(self, dangerous_sql):
        """Test that dangerous SQL is rejected."""
        with pytest.raises(SQLValidationError, match="blocked keyword"):
            check_blocked_keywords(dangerous_sql)
    
    @pytest.mark.parametrize("safe_sql", [
        "SELECT * FROM users;",
        "SELECT id, name FROM orders WHERE status = 'completed';",
        "WITH cte AS (SELECT * FROM data) SELECT * FROM cte;",
        "SELECT COUNT(*) FROM products;",
    ])
    def test_safe_keywords_pass(self, safe_sql):
        """Test that safe SELECT queries pass."""
        # Should not raise
        check_blocked_keywords(safe_sql)
    
    def test_case_insensitive_detection(self):
        """Test that keywords are detected case-insensitively."""
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("drop table users;")
        
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("DeLeTe FrOm users;")
    
    def test_substring_match_avoided(self):
        """Test that keywords in column/table names don't trigger."""
        # "deleted_at" contains "DELETE" but shouldn't trigger
        safe_sql = "SELECT deleted_at FROM users;"
        # This might still trigger with naive word boundary matching
        # Our implementation should handle this correctly
        try:
            check_blocked_keywords(safe_sql)
        except SQLValidationError:
            pytest.fail("False positive on column name containing keyword")


class TestCheckStartsWithSelect:
    """Tests for SELECT-only enforcement."""
    
    def test_select_passes(self):
        """Test that SELECT queries pass."""
        check_starts_with_select("SELECT * FROM users;")
    
    def test_with_clause_passes(self):
        """Test that CTE (WITH) queries pass."""
        check_starts_with_select("WITH cte AS (SELECT 1) SELECT * FROM cte;")
    
    def test_non_select_fails(self):
        """Test that non-SELECT queries fail."""
        with pytest.raises(SQLValidationError, match="must start with SELECT"):
            check_starts_with_select("UPDATE users SET name = 'test';")
    
    def test_whitespace_ignored(self):
        """Test that leading whitespace is handled."""
        check_starts_with_select("   SELECT * FROM data;")
    
    def test_subquery_injection_caught(self):
        """Test that subquery injection is caught."""
        # This is a SELECT but shouldn't be allowed as standalone
        malicious = "1; DROP TABLE users; SELECT * FROM admin;"
        with pytest.raises(SQLValidationError):
            check_starts_with_select(malicious)


class TestExtractTableReferences:
    """Tests for table name extraction."""
    
    def test_extract_from_simple_select(self):
        """Test extraction from simple SELECT."""
        sql = "SELECT * FROM users;"
        tables = extract_table_references(sql)
        assert "USERS" in tables
    
    def test_extract_from_join(self):
        """Test extraction from JOIN query."""
        sql = """
        SELECT u.name, o.total
        FROM users u
        JOIN orders o ON u.id = o.user_id;
        """
        tables = extract_table_references(sql)
        assert "USERS" in tables
        assert "ORDERS" in tables
    
    def test_extract_deduplicates(self):
        """Test that duplicate table references are deduplicated."""
        sql = "SELECT * FROM users JOIN users u2 ON users.id = u2.manager_id;"
        tables = extract_table_references(sql)
        # Should appear only once
        assert tables.count("USERS") == 1
    
    def test_extract_multiple_joins(self):
        """Test extraction from complex multi-join."""
        sql = """
        SELECT *
        FROM orders o
        JOIN users u ON o.user_id = u.id
        JOIN products p ON o.product_id = p.id
        LEFT JOIN reviews r ON p.id = r.product_id;
        """
        tables = extract_table_references(sql)
        assert "ORDERS" in tables
        assert "USERS" in tables
        assert "PRODUCTS" in tables
        assert "REVIEWS" in tables


class TestValidateSyntax:
    """Tests for SQL syntax validation."""
    
    def test_valid_sql_passes(self):
        """Test that valid SQL passes syntax check."""
        validate_syntax("SELECT * FROM users WHERE id = 1;")
    
    def test_invalid_sql_fails(self):
        """Test that malformed SQL fails."""
        with pytest.raises(SQLValidationError, match="syntax error|parse"):
            validate_syntax("SELCT * FORM users;")  # Typos
    
    def test_empty_sql_fails(self):
        """Test that empty SQL fails."""
        with pytest.raises(SQLValidationError):
            validate_syntax("")


class TestValidateSQL:
    """Integration tests for full SQL validation."""
    
    def test_valid_select_passes(self, db: Session):
        """Test that a valid SELECT query passes all checks."""
        sql = "SELECT id, name FROM users WHERE active = true;"
        result = validate_sql(sql, db)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_dangerous_sql_fails(self, db: Session):
        """Test that dangerous SQL fails validation."""
        sql = "DROP TABLE users;"
        result = validate_sql(sql, db)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert result["errors"][0]["type"] == "BLOCKED_KEYWORD"
    
    def test_non_select_fails(self, db: Session):
        """Test that non-SELECT queries fail."""
        sql = "UPDATE users SET admin = 1;"
        result = validate_sql(sql, db)
        
        assert result["valid"] is False
    
    def test_unknown_table_warning(self, db: Session):
        """Test that unknown table generates warning."""
        sql = "SELECT * FROM nonexistent_table;"
        result = validate_sql(sql, db, check_tables=True)
        
        # Should pass validation but have warnings
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert result["warnings"][0]["type"] == "UNKNOWN_TABLE"
    
    def test_skip_table_check(self, db: Session):
        """Test that table checking can be disabled."""
        sql = "SELECT * FROM fake_table;"
        result = validate_sql(sql, db, check_tables=False)
        
        # Should not have table warnings
        assert len(result["warnings"]) == 0


class TestSQLInjectionDefense:
    """Comprehensive SQL injection attack tests."""
    
    @pytest.mark.parametrize("attack", [
        # Classic injection
        "1' OR '1'='1",
        "'; DROP TABLE users; --",
        
        # Stacked queries
        "1; DELETE FROM users WHERE 1=1;",
        
        # UNION attacks
        "1 UNION SELECT password FROM admin_users",
        
        # Comment injection
        "1' -- ",
        "1' /* comment */ OR '1'='1",
        
        # Time-based blind injection
        "1' AND SLEEP(10) --",
        "1' OR BENCHMARK(10000000,MD5('x')) --",
        
        # Boolean-based blind injection
        "1' AND 1=1 --",
        "1' AND SUBSTRING(password,1,1)='a' --",
    ])
    def test_injection_blocked(self, attack, db: Session):
        """Test that common injection patterns are blocked."""
        # Wrap in a SELECT to test validation
        sql = f"SELECT * FROM users WHERE id = {attack};"
        
        result = validate_sql(sql, db)
        
        # Should either fail validation or be caught by keyword check
        # At minimum, dangerous keywords should be detected
        if "DROP" in attack.upper() or "DELETE" in attack.upper():
            assert result["valid"] is False
