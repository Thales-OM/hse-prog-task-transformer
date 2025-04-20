import os
from fastapi import Query, Depends, Header, Path, Request
from typing import Generator, Optional, get_args, AsyncGenerator
from contextlib import contextmanager
from psycopg2.extensions import cursor
from src.database.pool import ConnectionPoolManager
import openai
from src.config import settings
from src.api.auth import verify_rsa_key_pair
from src.exceptions import PublicKeyMissingException, UnauthorizedException, UserGroupNotFoundException
from src.utils import form_to_key, get_request_ip
from src.logger import LoggerFactory
from src.types import UserGroupCD, Language
from src.api.utils import existing_user_group_cd
from src.session.storage import SessionStorage, RedisConnection
from src.session.schemas import UserSessionData


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


async def get_user_group_query(user_group_cd: Optional[UserGroupCD] = Query(...), cursor: cursor = Depends(get_db_cursor)) -> Optional[UserGroupCD]:
    if user_group_cd is None:
        return None
    if not (await existing_user_group_cd(user_group_cd=user_group_cd, cursor=cursor)):
        raise UserGroupNotFoundException()
    return user_group_cd


async def get_redis_connection() -> AsyncGenerator:
    async with SessionStorage.get_connection() as redis_connection:
        yield redis_connection


async def get_language_query(request: Request, lang: Optional[Language] = Query(None), redis_connection: RedisConnection = Depends(get_redis_connection)) -> Language:
    ip = get_request_ip(request=request)
    if lang is None or lang not in get_args(Language):
        if ip:
            user_data = await redis_connection.get(ip=ip)
            lang = user_data.lang if user_data else None
        lang = lang or settings.frontend.default_language
    if ip:
        await redis_connection.set(ip=ip, data=UserSessionData(lang=lang))
    return lang
