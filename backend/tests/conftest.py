"""Pytest fixtures for tests."""

import json
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base
from app.models.source import Source, SourceType
from app.models.table import Table

# -------------------------------------------------------------------
# SQLite compatibility: teach SQLite how to compile PostgreSQL types.
# -------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

_orig_pg_uuid = getattr(SQLiteTypeCompiler, "visit_UUID", None)
_orig_jsonb = getattr(SQLiteTypeCompiler, "visit_JSONB", None)

if _orig_jsonb is None:
    SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "TEXT"

if _orig_pg_uuid is None:
    SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "VARCHAR(36)"

# Also need Enum rendering to use VARCHAR for the SourceType enum
_orig_enum = getattr(SQLiteTypeCompiler, "visit_enum", None)
# SQLite already handles Enum, so this should be fine.

# -------------------------------------------------------------------

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys in SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_source(db):
    """Create a sample source record."""
    source = Source(
        id=uuid.uuid4(),
        source_type=SourceType.CSV,
        source_name="test_data",
        description="Test data source",
        original_filename="test_data.csv",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@pytest.fixture
def sample_customers_table(db, sample_source):
    """Create a test customers table with sample data in SQLite + metadata record."""
    # Drop first to ensure clean state (StaticPool reuses the connection)
    db.execute(text("DROP TABLE IF EXISTS test_customers"))
    db.execute(text("""
        CREATE TABLE test_customers (
            _ttd_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            total_orders INTEGER
        )
    """))
    db.execute(text("""
        INSERT INTO test_customers (name, email, total_orders)
        VALUES ('Alice', 'alice@test.com', 5),
               ('Bob', 'bob@test.com', 3),
               ('Charlie', 'charlie@test.com', 0)
    """))
    db.commit()

    # Create the metadata record in ttd_tables
    table = Table(
        id=uuid.uuid4(),
        source_id=sample_source.id,
        original_name="customers.csv",
        normalized_name="test_customers",
        description="Customer records",
        row_count=3,
        columns=[
            {
                "name": "name",
                "data_type": "VARCHAR",
                "nullable": False,
                "is_primary_key": False,
                "is_unique": False,
                "sample_values": ["Alice", "Bob", "Charlie"],
                "distinct_count": 3,
                "null_count": 0,
            },
            {
                "name": "email",
                "data_type": "VARCHAR",
                "nullable": False,
                "is_primary_key": False,
                "is_unique": True,
                "sample_values": ["alice@test.com", "bob@test.com"],
                "distinct_count": 3,
                "null_count": 0,
            },
            {
                "name": "total_orders",
                "data_type": "INTEGER",
                "nullable": False,
                "is_primary_key": False,
                "is_unique": False,
                "sample_values": [5, 3, 0],
                "distinct_count": 3,
                "null_count": 0,
                "min_value": 0,
                "max_value": 5,
            },
        ],
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


@pytest.fixture
def sample_orders_table(db, sample_source):
    """Create a test orders table with sample data."""
    db.execute(text("DROP TABLE IF EXISTS test_orders"))
    db.execute(text("""
        CREATE TABLE test_orders (
            _ttd_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            customer_name TEXT,
            amount REAL,
            status TEXT
        )
    """))
    db.execute(text("""
        INSERT INTO test_orders (order_id, customer_name, amount, status)
        VALUES (1, 'Alice', 99.99, 'completed'),
               (2, 'Alice', 49.50, 'completed'),
               (3, 'Bob', 150.00, 'pending'),
               (4, 'Charlie', 25.00, 'cancelled')
    """))
    db.commit()

    table = Table(
        id=uuid.uuid4(),
        source_id=sample_source.id,
        original_name="orders.csv",
        normalized_name="test_orders",
        description="Order records",
        row_count=4,
        columns=[
            {
                "name": "order_id",
                "data_type": "INTEGER",
                "nullable": False,
                "is_primary_key": True,
                "is_unique": True,
                "sample_values": [1, 2, 3, 4],
                "distinct_count": 4,
                "null_count": 0,
            },
            {
                "name": "customer_name",
                "data_type": "VARCHAR",
                "nullable": False,
                "is_primary_key": False,
                "is_unique": False,
                "sample_values": ["Alice", "Bob", "Charlie"],
                "distinct_count": 3,
                "null_count": 0,
            },
            {
                "name": "amount",
                "data_type": "FLOAT",
                "nullable": False,
                "is_primary_key": False,
                "is_unique": False,
                "sample_values": [99.99, 49.50, 150.00, 25.00],
                "distinct_count": 4,
                "null_count": 0,
                "min_value": 25.00,
                "max_value": 150.00,
            },
            {
                "name": "status",
                "data_type": "VARCHAR",
                "nullable": False,
                "is_primary_key": False,
                "is_unique": False,
                "sample_values": ["completed", "pending", "cancelled"],
                "distinct_count": 3,
                "null_count": 0,
            },
        ],
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


@pytest.fixture
def mock_llm_select_count():
    """Mock LLM to return a SELECT COUNT(*) query."""
    with patch("app.services.query_engine.llm_complete") as mock:
        mock.return_value = "```sql\nSELECT COUNT(*) AS customer_count FROM test_customers\n```"
        yield mock


@pytest.fixture
def mock_llm_select_sum():
    """Mock LLM to return a SELECT SUM query."""
    with patch("app.services.query_engine.llm_complete") as mock:
        mock.return_value = "```sql\nSELECT SUM(amount) AS total_revenue FROM test_orders WHERE status = 'completed'\n```"
        yield mock


@pytest.fixture
def mock_llm_bad_sql():
    """Mock LLM to return invalid SQL."""
    with patch("app.services.query_engine.llm_complete") as mock:
        mock.return_value = "I cannot generate SQL for that question."
        yield mock


@pytest.fixture
def mock_llm_descriptions():
    """Mock LLM for data semantic description generation."""
    with patch("app.services.llm.llm_complete") as mock:
        mock.return_value = "Test table description"
        yield mock
