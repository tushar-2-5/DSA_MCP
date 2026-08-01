import asyncio
import os
import sys
import uuid
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool
from database.queries import (
    create_user,
    get_user,
    get_topic_by_slug,
    create_topic,
    upsert_mastery,
    get_mastery_row,
    create_problem,
    get_problem,
    insert_attempt,
    get_recent_attempts,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_queries")


async def run_test():
    test_slug = f"test-topic-{uuid.uuid4().hex[:6]}"
    test_email = f"test_{uuid.uuid4().hex[:6]}@example.com"

    async with get_db_connection() as conn:
        print("--- Step 1: Create User ---")
        user = await create_user(conn, test_email, "Test User")
        await conn.commit()
        await asyncio.sleep(0.02)
        print(f"Created User: {user}")

        print("\n--- Step 2: Get User ---")
        fetched_user = await get_user(conn, user.id)
        print(f"Fetched User: {fetched_user}")

        print("\n--- Step 3: Fetch or Create Topic ---")
        topic = await get_topic_by_slug(conn, test_slug)
        if not topic:
            topic = await create_topic(conn, test_slug, "Test Topic")
            await conn.commit()
            await asyncio.sleep(0.02)
        print(f"Topic: {topic}")

        print("\n--- Step 4: Upsert Mastery ---")
        mastery = await upsert_mastery(conn, user.id, topic.id, 0.42)
        await conn.commit()
        await asyncio.sleep(0.02)
        print(f"Upserted Mastery: {mastery}")

        print("\n--- Step 5: Get Mastery Row ---")
        fetched_mastery = await get_mastery_row(conn, user.id, topic.id)
        print(f"Fetched Mastery: {fetched_mastery}")

        print("\n--- Step 6: Create & Get Problem ---")
        problem = await create_problem(
            conn,
            "Test Problem",
            "Given an array...",
            "easy",
            topic.id,
            "leetcode",
        )
        await conn.commit()
        await asyncio.sleep(0.02)
        print(f"Created Problem: {problem}")
        fetched_problem = await get_problem(conn, problem.id)
        print(f"Fetched Problem: {fetched_problem}")

        print("\n--- Step 7: Insert Attempt ---")
        attempt = await insert_attempt(
            conn,
            user_id=user.id,
            problem_id=problem.id,
            code_s3_key="s3://bucket/test.py",
            outcome="pass",
            complexity_achieved="O(N)",
            time_taken_seconds=120,
        )
        await conn.commit()
        print(f"Inserted Attempt: {attempt}")

        print("\n--- Step 8: Get Recent Attempts ---")
        recent = await get_recent_attempts(conn, user.id, limit=5)
        print(f"Recent Attempts Count: {len(recent)}")
        print(f"Recent Attempt: {recent[0]}")

        print("\n--- Step 9: Cleanup Test Data ---")
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM attempts WHERE id = %s", (str(attempt.id),))
            await cur.execute(
                "DELETE FROM mastery WHERE user_id = %s AND topic_id = %s",
                (str(user.id), str(topic.id)),
            )
            await cur.execute("DELETE FROM problems WHERE id = %s", (str(problem.id),))
            await cur.execute("DELETE FROM topics WHERE id = %s", (str(topic.id),))
            await cur.execute("DELETE FROM users WHERE id = %s", (str(user.id),))
        await conn.commit()
        print("Cleanup completed successfully.")

    await close_pool()
    print("\nSUCCESS: All database queries verified successfully!")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_test())
