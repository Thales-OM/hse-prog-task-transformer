from typing import Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager
from redis.asyncio import ConnectionPool, RedisError, Redis
from pydantic import ValidationError
from src.config import settings
from src.session.schemas import UserSessionData
from src.exceptions import RedisUnavailableException
from src.logger import LoggerFactory
import json


logger = LoggerFactory.getLogger(__name__)


class RedisConnection:
    """Wrapper for a Redis connection with session operations"""
    def __init__(self, connection: Redis):
        self._connection = connection

    async def close(self) -> None:
        """Close the connection (handled by context manager)"""
        await self._connection.aclose()

    async def set(self, ip: str, data: UserSessionData) -> None:
        """Save complete user session data"""
        try:
            await self._connection.set(ip, data.model_dump_json(), ex=settings.redis.ex)
        except (ValidationError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid session data: {e}")

    async def update(self, ip: str, **update_data: Any) -> UserSessionData:
        """Update specific fields in the session data"""
        existing = await self._connection.get(ip)
        if existing is None:
            session = UserSessionData(**update_data)
        else:
            session = UserSessionData.model_validate_json(existing)
            for key, value in update_data.items():
                setattr(session, key, value)
        
        await self._connection.set(ip, session.model_dump_json(), ex=settings.redis.ex)
        return session

    async def get(self, ip: str) -> Optional[UserSessionData]:
        """Retrieve complete session data"""
        data = await self._connection.get(ip)
        if data is None:
            return None
        return UserSessionData.model_validate_json(data)

    async def get_session_field(self, ip: str, field: str) -> Optional[Any]:
        """Get a specific field from session data"""
        session = await self.get(ip)
        return getattr(session, field, None) if session else None

    async def delete_session(self, ip: str) -> bool:
        """Delete session data"""
        return await self._connection.delete(ip) > 0


class SessionStorage:
    _redis_pool: Optional[ConnectionPool] = None

    @classmethod
    async def initialize(cls):
        """Initialize the Redis connection pool."""
        if cls._redis_pool is None:
            try:
                cls._redis_pool = ConnectionPool.from_url(
                    url=settings.redis.url, 
                    max_connections=settings.redis.pool_size,
                    decode_responses=False
                )
                logger.info("Redis connection pool initialized successfully")
            except RedisError as e:
                raise RedisUnavailableException(f"Failed to connect to Redis: {e}")

    @classmethod
    async def close(cls):
        """Close the Redis connection pool."""
        if cls._redis_pool is not None:
            await cls._redis_pool.disconnect(inuse_connections=True)
            cls._redis_pool = None

    @classmethod
    @asynccontextmanager
    async def get_connection(cls) -> AsyncGenerator:
        """
        Get a Redis connection as a context manager.
        
        Usage:
            async with storage.get_connection() as conn:
                await conn.get_session(...)
        """
        if cls._redis_pool is None:
            await cls.initialize()
        
        redis = Redis(connection_pool=cls._redis_pool)
        redis_connection = RedisConnection(connection=redis)
        try:
            yield redis_connection
        finally:
            await redis_connection.close()
