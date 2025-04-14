from typing import Generator
from contextlib import contextmanager
from src.database.pool import ConnectionPoolManager
import openai
from src.config import settings


def get_db_connection() -> Generator:
    with ConnectionPoolManager.get_connection() as conn:
        yield conn


def get_db_cursor() -> Generator:
    with ConnectionPoolManager.get_cursor() as cursor:
        yield cursor


async def get_openai_client():
    client = openai.AsyncClient(
        base_url=settings.openai.base_url,
        api_key=settings.openai.api_key
    )
    try:
        yield client
    finally:
        await client.close()
