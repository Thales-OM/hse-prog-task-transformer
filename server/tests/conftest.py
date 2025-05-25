# tests/conftest.py
import pytest
import psycopg2
import os
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from psycopg2.pool import SimpleConnectionPool
from src.main import app
from src.database.pool import ConnectionPoolManager
from src.config import settings

# Get the directory of this conftest.py file
current_dir = Path(__file__).parent


@pytest.fixture(scope="session")
def test_client():
    return TestClient(app)


@pytest.fixture(scope="session")
def mock_db_pool():
    # Load test database configuration
    test_db_config = {
        "minconn": 1,
        "maxconn": 3,
        "host": settings.postgres.host,
        "port": settings.postgres.port,
        "dbname": "test_db",  # Use separate test database
        "user": settings.postgres.user,
        "password": settings.postgres.password,
    }

    # Initialize connection pool
    test_pool = SimpleConnectionPool(**test_db_config)
    ConnectionPoolManager._pool = test_pool

    # Initialize database schema
    init_sql_path = current_dir.parent / "postgres" / "init" / "init.sql"
    with test_pool.getconn() as conn:
        conn.autocommit = True  # Needed for schema creation
        with conn.cursor() as cursor:
            with open(init_sql_path, "r") as f:
                sql = f.read()
                cursor.execute(sql)
        test_pool.putconn(conn)

    yield test_pool

    # Cleanup
    test_pool.closeall()
    ConnectionPoolManager._pool = None


@pytest.fixture
def db_connection(mock_db_pool):
    conn = mock_db_pool.getconn()
    conn.autocommit = False  # Use transactions for rollback
    yield conn
    conn.rollback()  # Rollback after test to maintain isolation
    mock_db_pool.putconn(conn)


@pytest.fixture
def db_cursor(db_connection):
    with db_connection.cursor() as cursor:
        yield cursor


@pytest.fixture
def mock_openai():
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Test response<think>Test reasoning</think>"
                    )
                )
            ]
        )
    )

    with patch("src.api.deps.openai.AsyncClient") as mock:
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture(autouse=True)
def override_settings():
    # Override any settings for testing
    original = settings.postgres.dbname
    settings.postgres.dbname = "test_db"  # Use test database
    yield
    settings.postgres.dbname = original
