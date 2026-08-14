import asyncio
import sys
sys.path.insert(0, '.')
from database.connection import get_db_connection

async def check():
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT filename, applied_at FROM schema_migrations ORDER BY filename;")
        rows = await cursor.fetchall()
        for r in rows:
            print(f"Applied migration: {r[0]} (applied at {r[1]})")

asyncio.run(check())
