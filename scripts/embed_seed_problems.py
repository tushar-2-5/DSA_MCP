import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
        # Step 0: Verify vector extension and HNSW index exist before inserting embeddings
        logger.info("Verifying vector extension and HNSW index in Neon DB...")
        async with conn.cursor() as cur:
            await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings USING hnsw (embedding vector_cosine_ops);"
            )
            await conn.commit()

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
                print(f"Embedding problem {index}/{total_problems}: '{title}'... skipped (already exists)", flush=True)
                skipped_count += 1

                continue

            try:
                # Generate embedding for statement text
                vector = embedder.embed(statement)

                # Store in database
                await insert_embedding(conn, "problem", prob_id, vector)
                await conn.commit()

                print(f"Embedding problem {index}/{total_problems}: '{title}'... done", flush=True)
                embedded_count += 1
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower() or "limit reached" in err_msg.lower():
                    logger.warning(f"Quota/Rate limit encountered on problem {index}/{total_problems} ('{title}'): {e}")
                    print(f"\n⚠️ Gemini free tier quota limit reached at problem {index}/{total_problems}.")
                    print(f"Progress has been saved to Neon DB ({embedded_count} embedded this run, {skipped_count} previously existing).")
                    print("Re-run this script after your daily quota resets (midnight UTC) to continue embedding remaining problems.")
                    break
                else:
                    logger.error(f"Error embedding problem '{title}': {e}")
                    continue


    await close_pool()
    print("-" * 50, flush=True)
    print(f"Summary: Embedded {embedded_count} problem(s), Skipped {skipped_count} problem(s), Total {total_problems}.", flush=True)



if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
