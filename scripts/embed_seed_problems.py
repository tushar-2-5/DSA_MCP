import asyncio
import logging
from database.connection import get_db_connection, close_pool
from database.queries import (
    get_all_problems_with_topics,
    get_embedding_by_source,
    insert_embedding,
)
from embeddings.gemini_client import GeminiEmbedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting problem embedding process...")
    embedder = GeminiEmbedder()

    async with get_db_connection() as conn:
        problems = await get_all_problems_with_topics(conn)
        total_problems = len(problems)
        logger.info(f"Fetched {total_problems} problems from database.")

        embedded_count = 0
        skipped_count = 0

        for index, problem in enumerate(problems, 1):
            prob_id = problem["id"]
            title = problem["title"]
            statement = problem["statement"]

            # Check if embedding already exists (idempotency check)
            existing = await get_embedding_by_source(conn, "problem", prob_id)
            if existing:
                print(f"Embedding problem {index}/{total_problems}: '{title}'... skipped (already exists)")
                skipped_count += 1
                continue

            # Generate embedding for statement text
            vector = embedder.embed(statement)

            # Store in database
            await insert_embedding(conn, "problem", prob_id, vector)
            await conn.commit()

            print(f"Embedding problem {index}/{total_problems}: '{title}'... done")
            embedded_count += 1

    await close_pool()
    print("-" * 50)
    print(f"Summary: Embedded {embedded_count} problem(s), Skipped {skipped_count} problem(s), Total {total_problems}.")


if __name__ == "__main__":
    asyncio.run(main())
