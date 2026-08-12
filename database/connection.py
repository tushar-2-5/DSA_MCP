import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import psycopg
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv

# On Windows, psycopg3 async requires WindowsSelectorEventLoopPolicy
# TODO: revisit if Python 3.16 removes this
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    global _pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    if _pool is None or _pool.closed:
        _pool = AsyncConnectionPool(
            conninfo=database_url,
            open=False,
            min_size=1,
            max_size=10,
        )
        await _pool.open()
        logger.info("Database connection pool initialized")
    return _pool


async def close_pool():
    global _pool
    if _pool is not None and not _pool.closed:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    pool = await get_pool()
    async with pool.connection() as conn:
        try:
            yield conn
        except Exception as e:
            await conn.rollback()
            logger.error(f"Database operation failed, rolled back transaction: {e}")
            raise
