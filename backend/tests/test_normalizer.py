"""Tests for normalizer service."""

import pytest

from app.services.normalizer import (
    generate_create_table_ddl,
    pandas_to_postgres_type,
    sanitize_column_name,
    sanitize_table_name,
)


class TestSanitizeTableName:
    """Tests for table name sanitization."""

    def test_basic(self):
        assert sanitize_table_name("customers") == "ttd_data_customers"

    def test_removes_extension(self):
        assert sanitize_table_name("customers.csv") == "ttd_data_customers"
        assert sanitize_table_name("data.xlsx") == "ttd_data_data"

    def test_handles_spaces(self):
        assert sanitize_table_name("my data file") == "ttd_data_my_data_file"

    def test_handles_special_chars(self):
        assert sanitize_table_name("data-2024!@#") == "ttd_data_data_2024"

    def test_lowercase(self):
        assert sanitize_table_name("MyData") == "ttd_data_mydata"

    def test_starts_with_number(self):
        assert sanitize_table_name("123data") == "ttd_data_t_123data"

    def test_truncates_long_names(self):
        long_name = "a" * 100
        result = sanitize_table_name(long_name)
        assert len(result) <= 63


class TestSanitizeColumnName:
    """Tests for column name sanitization."""

    def test_basic(self):
        assert sanitize_column_name("customer_id") == "customer_id"

    def test_spaces(self):
        assert sanitize_column_name("Customer Name") == "customer_name"

    def test_special_chars(self):
        assert sanitize_column_name("price$") == "price"

    def test_reserved_words(self):
        assert sanitize_column_name("order") == "order_"
        assert sanitize_column_name("user") == "user_"
        assert sanitize_column_name("table") == "table_"

    def test_starts_with_number(self):
        assert sanitize_column_name("123col") == "c_123col"


class TestPandasToPostgresType:
    """Tests for pandas to PostgreSQL type conversion."""

    def test_integer(self):
        assert pandas_to_postgres_type("int64") == "BIGINT"
        assert pandas_to_postgres_type("int32") == "INTEGER"

    def test_float(self):
        assert pandas_to_postgres_type("float64") == "DOUBLE PRECISION"

    def test_bool(self):
        assert pandas_to_postgres_type("bool") == "BOOLEAN"

    def test_datetime(self):
        assert pandas_to_postgres_type("datetime64[ns]") == "TIMESTAMP WITH TIME ZONE"

    def test_string(self):
        assert pandas_to_postgres_type("object") == "VARCHAR(255)"
        assert pandas_to_postgres_type("object", max_length=1000) == "TEXT"


class TestGenerateCreateTableDDL:
    """Tests for DDL generation."""

    def test_basic_table(self):
        columns = [
            {"name": "id", "data_type": "INTEGER", "nullable": False},
            {"name": "name", "data_type": "VARCHAR(255)", "nullable": True},
        ]
        ddl = generate_create_table_ddl("customers", columns)

        assert "CREATE TABLE" in ddl
        assert '"customers"' in ddl
        assert '"id" INTEGER NOT NULL' in ddl
        assert '"name" VARCHAR(255) NULL' in ddl
        assert "_ttd_row_id" in ddl

    def test_all_types(self):
        columns = [
            {"name": "int_col", "data_type": "INTEGER"},
            {"name": "float_col", "data_type": "FLOAT"},
            {"name": "bool_col", "data_type": "BOOLEAN"},
            {"name": "ts_col", "data_type": "TIMESTAMP"},
            {"name": "text_col", "data_type": "TEXT"},
        ]
        ddl = generate_create_table_ddl("test_table", columns)

        assert "INTEGER" in ddl
        assert "DOUBLE PRECISION" in ddl
        assert "BOOLEAN" in ddl
        assert "TIMESTAMP WITH TIME ZONE" in ddl
        assert "TEXT" in ddl
