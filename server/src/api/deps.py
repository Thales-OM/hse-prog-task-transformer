import os
from fastapi import Query, Depends, Header
from typing import Generator, Optional, Literal
from contextlib import contextmanager
from src.database.pool import ConnectionPoolManager
import openai
from src.config import settings
from src.api.auth import verify_rsa_key_pair
from src.exceptions import PublicKeyMissingException, UnauthorizedException
from src.utils import form_to_key
from src.logger import LoggerFactory


logger = LoggerFactory.getLogger(__name__)


def get_db_connection() -> Generator:
    with ConnectionPoolManager.get_connection() as conn:
        yield conn


def get_db_cursor() -> Generator:
    with ConnectionPoolManager.get_cursor() as cursor:
        yield cursor


async def get_openai_api_key(openai_api_key: str = Query(...)) -> str:
    return openai_api_key


async def get_openai_url(openai_url: Optional[str] = Query(None)) -> str:
    # Use provided URL or fall back to settings
    return openai_url if openai_url is not None else settings.openai.base_url


async def get_openai_client(openai_url: str = Depends(get_openai_url), openai_api_key: str = Depends(get_openai_api_key)):
    client = openai.AsyncClient(
        base_url=openai_url,
        api_key=openai_api_key
    )
    try:
        yield client
    finally:
        await client.close()


async def get_auth_token(authToken: str = Header(...)) -> str:
    public_pem = settings.server.get_public_api_key()
    authToken = form_to_key(text=authToken)

    if not verify_rsa_key_pair(private_pem=authToken, public_pem=public_pem):
        raise UnauthorizedException()
    return authToken