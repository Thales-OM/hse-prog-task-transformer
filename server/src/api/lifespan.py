from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database.pool import ConnectionPoolManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ConnectionPoolManager.initialize_pool()
        yield
    finally: 
        # Ensure pool is closed
        ConnectionPoolManager.close_pool()