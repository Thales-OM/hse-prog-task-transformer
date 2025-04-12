from typing import Generator
from contextlib import contextmanager
from src.database.pool import ConnectionPoolManager


def get_db_connection() -> Generator:
    with ConnectionPoolManager.get_connection() as conn:
        yield conn


def get_db_cursor() -> Generator:
    with ConnectionPoolManager.get_cursor() as cursor:
        yield cursor