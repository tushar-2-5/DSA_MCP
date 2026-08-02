import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    migrations_dir = Path(__file__).parent.parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    async with get_db_connection() as conn:
        # Step 1: Ensure tracking table exists
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT now()
                );
                """
            )
            await conn.commit()

            # Step 2: Fetch already applied migrations
            await cur.execute("SELECT filename FROM schema_migrations;")
            applied_rows = await cur.fetchall()
            applied_files = {row[0] for row in applied_rows}

        # Step 3: Run unapplied migrations in order
        for migration_file in migration_files:
            filename = migration_file.name
            if filename in applied_files:
                logger.info(f"Migration {filename} already applied, skipping.")
                continue

            logger.info(f"Applying migration {filename}...")
            sql_content = migration_file.read_text(encoding="utf-8")
            async with conn.cursor() as cur:
                await cur.execute(sql_content)
                await cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s);",
                    (filename,),
                )
            await conn.commit()
            logger.info(f"Migration {filename} applied and recorded successfully!")

        logger.info("Inspecting columns of 'problems' table...")
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'problems';"
            )
            columns = await cur.fetchall()
            print("Columns in problems table:")
            for col in columns:
                print(f"  - {col}")

    await close_pool()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
