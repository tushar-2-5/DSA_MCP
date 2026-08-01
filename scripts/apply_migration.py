import asyncio
import logging
from pathlib import Path
from database.connection import get_db_connection, close_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    migration_file = Path(__file__).parent.parent / "migrations" / "0001_init.sql"
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return

    sql_content = migration_file.read_text(encoding="utf-8")

    logger.info("Connecting to CockroachDB Cloud and applying migrations/0001_init.sql...")
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql_content)
            await conn.commit()
    logger.info("Migration 0001_init.sql applied successfully!")

    logger.info("Running 'SHOW TABLES;'...")
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SHOW TABLES;")
            tables = await cur.fetchall()
            print("Existing tables in database:")
            for row in tables:
                table_name = row[1] if len(row) > 1 else row[0]
                print(f"  - {table_name}")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
