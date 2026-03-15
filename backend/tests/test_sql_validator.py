"""Tests for SQL validation and safe execution."""

import pytest
from sqlalchemy import text

from app.services.sql_validator import (
    BLOCKED_KEYWORDS,
    SQLValidationError,
    check_blocked_keywords,
    check_starts_with_select,
    extract_table_references,
    normalize_sql,
    safe_execute,
    validate_sql,
    validate_syntax,
    validate_table_existence,
)


class TestNormalizeSQL:
    """Test SQL normalization."""

    def test_uppercases(self):
        assert "SELECT" in normalize_sql("select * from foo")

    def test_collapses_whitespace(self):
        result = normalize_sql("select  *\n  from\n\t  foo")
        assert "  " not in result

    def test_empty_string(self):
        assert normalize_sql("") == ""


class TestBlockedKeywords:
    """Test all blocked keyword detection."""

    @pytest.mark.parametrize("keyword", BLOCKED_KEYWORDS)
    def test_each_blocked_keyword(self, keyword):
        """Every keyword in BLOCKED_KEYWORDS should be caught."""
        sql = f"{keyword} TABLE test"
        with pytest.raises(SQLValidationError) as exc_info:
            check_blocked_keywords(sql)
        assert exc_info.value.violation == "BLOCKED_KEYWORD"

    def test_drop_table(self):
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("DROP TABLE customers")

    def test_insert_into(self):
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("INSERT INTO users VALUES (1, 'hack')")

    def test_update_set(self):
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("UPDATE users SET admin = true")

    def test_delete_from(self):
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("DELETE FROM users WHERE 1=1")

    def test_alter_table(self):
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("ALTER TABLE users ADD COLUMN hack TEXT")

    def test_truncate(self):
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("TRUNCATE TABLE logs")

    def test_grant_revoke(self):
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("GRANT ALL ON users TO hacker")
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("REVOKE SELECT ON users FROM readonly")

    def test_safe_select_allowed(self):
        # Should NOT raise
        check_blocked_keywords("SELECT * FROM users WHERE name = 'Alice'")

    def test_keyword_in_string_still_caught(self):
        """Keywords are matched as whole words in normalized SQL."""
        # "UPDATED_AT" should not trigger because UPDATE needs word boundary
        # But "UPDATE" alone should
        with pytest.raises(SQLValidationError):
            check_blocked_keywords("UPDATE users SET x = 1")

    def test_select_with_subquery_allowed(self):
        sql = "SELECT * FROM (SELECT id FROM users) sub"
        check_blocked_keywords(sql)  # Should not raise


class TestStartsWithSelect:
    """Test that SQL must start with SELECT or WITH."""

    def test_select_allowed(self):
        check_starts_with_select("SELECT * FROM users")

    def test_with_cte_allowed(self):
        check_starts_with_select("WITH cte AS (SELECT 1) SELECT * FROM cte")

    def test_insert_rejected(self):
        with pytest.raises(SQLValidationError) as exc_info:
            check_starts_with_select("INSERT INTO users VALUES (1)")
        assert exc_info.value.violation == "INVALID_START"

    def test_whitespace_handled(self):
        check_starts_with_select("  SELECT 1")

    def test_case_insensitive(self):
        check_starts_with_select("select * from users")


class TestValidateSyntax:
    """Test SQL syntax validation."""

    def test_valid_select(self):
        validate_syntax("SELECT * FROM users")

    def test_valid_complex(self):
        validate_syntax(
            "SELECT u.name, COUNT(o.id) FROM users u "
            "JOIN orders o ON u.id = o.user_id GROUP BY u.name"
        )

    def test_empty_raises(self):
        with pytest.raises(SQLValidationError):
            validate_syntax("")


class TestExtractTableReferences:
    """Test table name extraction from SQL."""

    def test_simple_from(self):
        tables = extract_table_references("SELECT * FROM users")
        assert "USERS" in tables

    def test_join(self):
        tables = extract_table_references(
            "SELECT * FROM orders o JOIN customers c ON o.cid = c.id"
        )
        assert "ORDERS" in tables
        assert "CUSTOMERS" in tables

    def test_multiple_joins(self):
        tables = extract_table_references(
            "SELECT * FROM a JOIN b ON a.id = b.aid "
            "LEFT JOIN c ON b.id = c.bid"
        )
        assert len(tables) == 3

    def test_subquery(self):
        tables = extract_table_references(
            "SELECT * FROM (SELECT id FROM users) sub"
        )
        assert "USERS" in tables

    def test_no_duplicates(self):
        tables = extract_table_references(
            "SELECT * FROM users u JOIN users u2 ON u.id = u2.manager_id"
        )
        assert tables.count("USERS") == 1


class TestValidateTableExistence:
    """Test table existence validation against metadata."""

    def test_known_table_no_warnings(self, db, sample_customers_table):
        warnings = validate_table_existence(
            "SELECT * FROM test_customers", db
        )
        assert len(warnings) == 0

    def test_unknown_table_warns(self, db, sample_customers_table):
        warnings = validate_table_existence(
            "SELECT * FROM nonexistent_table", db
        )
        assert len(warnings) == 1
        assert warnings[0]["type"] == "UNKNOWN_TABLE"

    def test_system_tables_ignored(self, db):
        warnings = validate_table_existence(
            "SELECT * FROM information_schema", db
        )
        assert len(warnings) == 0


class TestValidateSQL:
    """Test full SQL validation pipeline."""

    def test_valid_select(self, db, sample_customers_table):
        result = validate_sql("SELECT * FROM test_customers", db)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_blocked_keyword_invalid(self, db):
        result = validate_sql("DROP TABLE test", db)
        assert result["valid"] is False
        assert result["errors"][0]["type"] == "BLOCKED_KEYWORD"

    def test_bad_start_invalid(self, db):
        result = validate_sql("SHOW TABLES", db)
        assert result["valid"] is False

    def test_unknown_table_warning(self, db, sample_customers_table):
        result = validate_sql("SELECT * FROM missing_table", db)
        assert result["valid"] is True  # Warnings don't make it invalid
        assert len(result["warnings"]) == 1

    def test_skip_table_check(self, db):
        result = validate_sql(
            "SELECT * FROM any_table", db, check_tables=False
        )
        assert result["valid"] is True
        assert len(result["warnings"]) == 0

    def test_no_db_skips_table_check(self):
        result = validate_sql("SELECT 1", db=None)
        assert result["valid"] is True

    def test_with_cte_valid(self, db):
        result = validate_sql(
            "WITH cte AS (SELECT 1 AS n) SELECT * FROM cte", db
        )
        assert result["valid"] is True


class TestSafeExecute:
    """Test safe SQL execution with validation and LIMIT enforcement."""

    def test_execute_simple_select(self, db, sample_customers_table):
        result = safe_execute("SELECT * FROM test_customers", db)

        assert result["row_count"] == 3
        assert "name" in result["columns"]
        assert "email" in result["columns"]
        assert len(result["rows"]) == 3

    def test_execute_count(self, db, sample_customers_table):
        result = safe_execute(
            "SELECT COUNT(*) AS cnt FROM test_customers", db
        )
        assert result["rows"][0]["cnt"] == 3

    def test_execute_with_where(self, db, sample_customers_table):
        result = safe_execute(
            "SELECT name FROM test_customers WHERE total_orders > 0", db
        )
        assert result["row_count"] == 2
        names = [r["name"] for r in result["rows"]]
        assert "Alice" in names
        assert "Bob" in names
        assert "Charlie" not in names

    def test_execute_adds_limit(self, db, sample_customers_table):
        result = safe_execute("SELECT * FROM test_customers", db, limit=2)
        assert result["row_count"] == 2
        assert result["limited"] is True

    def test_execute_respects_existing_limit(self, db, sample_customers_table):
        result = safe_execute(
            "SELECT * FROM test_customers LIMIT 1", db, limit=1000
        )
        assert result["row_count"] == 1

    def test_execute_blocked_sql_raises(self, db):
        with pytest.raises(SQLValidationError) as exc_info:
            safe_execute("DROP TABLE test_customers", db)
        assert exc_info.value.violation == "BLOCKED_KEYWORD"

    def test_execute_invalid_start_raises(self, db):
        with pytest.raises(SQLValidationError) as exc_info:
            safe_execute("SHOW TABLES", db)
        assert exc_info.value.violation == "INVALID_START"

    def test_execute_nonexistent_table_raises(self, db):
        with pytest.raises(SQLValidationError) as exc_info:
            safe_execute("SELECT * FROM no_such_table", db)
        assert exc_info.value.violation == "EXECUTION_ERROR"

    def test_execute_join(self, db, sample_customers_table, sample_orders_table):
        result = safe_execute(
            "SELECT c.name, o.amount "
            "FROM test_customers c "
            "JOIN test_orders o ON c.name = o.customer_name",
            db,
        )
        assert result["row_count"] > 0
        assert "name" in result["columns"]
        assert "amount" in result["columns"]

    def test_execute_aggregate(self, db, sample_orders_table):
        result = safe_execute(
            "SELECT status, COUNT(*) AS cnt, SUM(amount) AS total "
            "FROM test_orders GROUP BY status ORDER BY total DESC",
            db,
        )
        assert result["row_count"] > 0
        # completed: 2 orders, 149.49
        completed = next(r for r in result["rows"] if r["status"] == "completed")
        assert completed["cnt"] == 2
        assert completed["total"] == pytest.approx(149.49)
