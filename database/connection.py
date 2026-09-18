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

logging.basicConfig(stream=sys.stderr)
logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None


def get_pooled_database_url(url: str | None = None) -> str:
    """Get the pooled database URL ensuring Neon-compatible sslmode=require."""
    if not url:
        url = os.getenv("DATABASE_URL", "")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Ensure sslmode=require for Neon
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    elif "sslmode=disable" in url or "sslmode=verify-full" in url:
        url = url.replace("sslmode=disable", "sslmode=require").replace(
            "sslmode=verify-full", "sslmode=require"
        )
    return url


def get_direct_database_url(url: str | None = None) -> str:
    """Convert a Neon pooled database URL to a direct database URL.
    Direct connections (port 5432 / non-pooler) are required for DDL/migrations."""
    pooled_url = get_pooled_database_url(url)
    # Remove -pooler from host (e.g., ep-abc-pooler.region.aws.neon.tech -> ep-abc.region.aws.neon.tech)
    direct_url = pooled_url.replace("-pooler.", ".")
    # Replace port 6543 with 5432 if present
    direct_url = direct_url.replace(":6543/", ":5432/").replace(":6543?", ":5432?")
    return direct_url


async def get_pool() -> AsyncConnectionPool:
    global _pool
    pooled_url = get_pooled_database_url()

    if _pool is None or _pool.closed:
        _pool = AsyncConnectionPool(
            conninfo=pooled_url,
            open=False,
            min_size=1,
            max_size=5,
        )
        await _pool.open()
        logger.info("Database connection pool initialized (Neon pooled)")
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


@asynccontextmanager
async def get_direct_db_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """Provide a direct (non-pooled) database connection for DDL and migrations."""
    direct_url = get_direct_database_url()
    conn = await psycopg.AsyncConnection.connect(direct_url)
    try:
        yield conn
    except Exception as e:
        await conn.rollback()
        logger.error(f"Direct database operation failed, rolled back: {e}")
        raise
    finally:
        await conn.close()

