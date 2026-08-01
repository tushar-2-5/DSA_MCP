import asyncio
import logging
from database.connection import get_db_connection, close_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Testing database connection pool...")
    test_email = "test_connection_user@example.com"
    test_name = "Test Connection User"

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            # Check version
            await cur.execute("SELECT version();")
            version_row = await cur.fetchone()
            logger.info(f"Connected to CockroachDB: {version_row[0]}")

            # Clean up existing test user if present
            await cur.execute("DELETE FROM users WHERE email = %s;", (test_email,))

            # Insert test user
            await cur.execute(
                "INSERT INTO users (email, display_name) VALUES (%s, %s) RETURNING id, email, display_name, created_at;",
                (test_email, test_name),
            )
            inserted_user = await cur.fetchone()
            logger.info(f"Inserted test user: id={inserted_user[0]}, email={inserted_user[1]}, name={inserted_user[2]}")

            # Read back user
            await cur.execute("SELECT id, email, display_name FROM users WHERE id = %s;", (inserted_user[0],))
            read_user = await cur.fetchone()
            assert read_user is not None, "Failed to read inserted user back"
            assert read_user[1] == test_email, "Email does not match"
            logger.info("Successfully read inserted test user back from database")

            # Clean up
            await cur.execute("DELETE FROM users WHERE id = %s;", (inserted_user[0],))
            await conn.commit()
            logger.info("Cleaned up test user record")

    await close_pool()
    logger.info("Connection test PASSED successfully!")


if __name__ == "__main__":
    asyncio.run(main())
