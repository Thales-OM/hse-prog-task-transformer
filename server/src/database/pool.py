from contextlib import asynccontextmanager, contextmanager
from psycopg2.pool import SimpleConnectionPool
from psycopg2 import OperationalError
from psycopg2.extensions import connection
from typing import Generator, Optional
import asyncio
from time import sleep
from src.logger import LoggerFactory
from src.config import settings
from src.exceptions import DatabaseUnavailableException
from src.utils import get_connection_id


logger = LoggerFactory.getLogger(__name__)


class ConnectionPoolManager:
    _pool: Optional[SimpleConnectionPool] = None

    @classmethod
    def initialize_pool(cls) -> None:
        max_retries = settings.postgres.pool_conn_retries
        retry_delay = settings.postgres.pool_conn_retry_delay
        
        for attempt in range(max_retries):
            try:
                cls._pool = SimpleConnectionPool(
                    minconn=settings.postgres.minconn,
                    maxconn=settings.postgres.maxconn,
                    user=settings.postgres.user,
                    password=settings.postgres.password,
                    host=settings.postgres.host,
                    port=settings.postgres.port,
                    dbname=settings.postgres.dbname,
                )
                logger.info("Database connection pool initialized successfully")
                break
            except OperationalError as ex:
                logger.error(
                    f"Database connection failed: {ex}. Attempt {attempt + 1} of {max_retries}."
                )
                if attempt < max_retries - 1:
                    logger.info(f"Retrying connection after {retry_delay} secs")
                    sleep(retry_delay)
                else:
                    logger.critical("Max retries reached. Could not initialize pool.")
                    raise DatabaseUnavailableException(
                        detail="Database connection failed after multiple attempts."
                    )

    @classmethod
    def close_pool(cls) -> None:
        if cls._pool:
            try:
                cls._pool.closeall()
                logger.info("Closed all database connections in pool")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")
                raise

    @classmethod
    @contextmanager
    def get_connection(cls) -> Generator:
        if cls._pool is None:
            cls.initialize_pool()
        
        conn_id = None
        with cls._pool.getconn() as conn:
            conn_id = get_connection_id(conn)
            logger.debug(f"Acquired connection (ID {conn_id}) from pool")
            yield conn
            conn.commit() # Commit transaction
        logger.debug(f"Returned connection (ID {conn_id}) to pool")

    @classmethod
    @contextmanager
    def get_cursor(cls) -> Generator:
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                yield cursor

