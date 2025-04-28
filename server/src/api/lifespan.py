from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database.pool import ConnectionPoolManager
from src.session.storage import SessionStorage


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ConnectionPoolManager.initialize_pool()
        await SessionStorage.initialize()
        yield
    finally:
        # Ensure pool is closed
        ConnectionPoolManager.close_pool()
        await SessionStorage.close()
