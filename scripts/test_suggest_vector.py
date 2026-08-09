import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool
from database.queries import (
    get_topic_by_slug,
    get_embedding_by_source,
    insert_embedding,
)
from tools.log_attempt import log_attempt
from tools.suggest_next_problem import suggest_next_problem
from tools.get_or_create_user import get_or_create_user
from embeddings.gemini_client import GeminiEmbedder
from psycopg.rows import dict_row


async def setup_sliding_window_problem_embeddings():
    """Ensure problem embeddings exist for all sliding-window problems in DB."""
    async with get_db_connection() as conn:
        topic_sw = await get_topic_by_slug(conn, "sliding-window")
        assert topic_sw is not None, "Topic 'sliding-window' must exist in DB."
        topic_sw_id = str(topic_sw.id)

        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, title, statement FROM problems WHERE topic_id = %s ORDER BY created_at ASC",
                (topic_sw_id,),
            )
            sw_problems = await cur.fetchall()

        embedder = GeminiEmbedder()
        for p in sw_problems:
            p_id = str(p["id"])
            existing_emb = await get_embedding_by_source(conn, "problem", p_id)
            if not existing_emb:
                vec = embedder.embed(p["statement"])
                await insert_embedding(conn, "problem", p_id, vec)
                await conn.commit()
    return topic_sw_id, sw_problems


async def prepare_user1_mastery(user_id_1: str, topic_sw_id: str):
    """Set sliding-window mastery to 0.0 and all other topics to 0.90 for User 1."""
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM topics")
            all_topics = await cur.fetchall()
            for ot in all_topics:
                t_id = str(ot[0])
                score = 0.0 if t_id == topic_sw_id else 0.90
                await cur.execute(
                    """
                    INSERT INTO mastery (user_id, topic_id, mastery_score, last_practiced_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (user_id, topic_id) DO UPDATE SET mastery_score = EXCLUDED.mastery_score
                    """,
                    (user_id_1, t_id, score),
                )
        await conn.commit()



async def cleanup_test_users(user_ids: list[str]):
    """Clean up test users and associated data."""
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            for uid in user_ids:
                await cur.execute(
                    """
                    DELETE FROM embeddings WHERE source_id IN (
                        SELECT id FROM mistakes WHERE user_id = %s
                        UNION
                        SELECT id FROM attempts WHERE user_id = %s
                    )
                    """,
                    (uid, uid),
                )
                await cur.execute("DELETE FROM mistakes WHERE user_id = %s", (uid,))
                await cur.execute("DELETE FROM attempts WHERE user_id = %s", (uid,))
                await cur.execute("DELETE FROM mastery WHERE user_id = %s", (uid,))
                await cur.execute("DELETE FROM users WHERE id = %s", (uid,))
        await conn.commit()


async def run_verification():
    print("==================================================")
    print("      TASK 13 VECTOR SIMILARITY RECOMMENDATION TEST")
    print("==================================================")

    # 1. Create User 1 (with mistake history in sliding-window)
    email_user_1 = f"vec_test_user1_{uuid.uuid4().hex[:6]}@example.com"
    user1_res = await get_or_create_user(email=email_user_1, display_name="Vector Test User 1")
    user_id_1 = user1_res["user_id"]
    print(f"Created Test User 1: {user_id_1} ({email_user_1})")

    # Ensure problem embeddings exist for sliding-window topic
    topic_sw_id, sw_problems = await setup_sliding_window_problem_embeddings()
    assert len(sw_problems) >= 2, "Need at least 2 sliding-window problems in DB."

    # Prepare mastery so sliding-window is chosen as the weak topic for User 1
    await prepare_user1_mastery(user_id_1, topic_sw_id)

    # Log 2 failed attempts for User 1 on first sliding-window problem (creates mistake embeddings)
    failed_prob = sw_problems[0]
    failed_prob_id = str(failed_prob["id"])
    print(f"Logging 2 failed attempts for User 1 on problem '{failed_prob['title']}'...")

    await log_attempt(
        user_id=user_id_1,
        problem_id=failed_prob_id,
        code="def minWindow(s, t):\n    # Off by one error in sliding window pointers\n    left = 0\n    for right in range(len(s)):\n        pass",
        outcome="fail",
        mistake_summary="Sliding window off-by-one boundary expansion bug",
        mistake_category="sliding_window_off_by_one",
    )
    await log_attempt(
        user_id=user_id_1,
        problem_id=failed_prob_id,
        code="def minWindow(s, t):\n    # Failed to contract window correctly\n    window_counts = {}\n    return ''",
        outcome="fail",
        mistake_summary="Failed to shrink window when condition met",
        mistake_category="sliding_window_shrink_condition",
    )

    # Re-enforce User 1 mastery (sliding-window 0.0, others 0.90) after log_attempt
    await prepare_user1_mastery(user_id_1, topic_sw_id)


    # Call suggest_next_problem for User 1
    print("\n--- Test User 1 (With Mistake History) ---")
    rec_res_1 = await suggest_next_problem(user_id=user_id_1)
    print("Recommendation Result for User 1:")
    print(rec_res_1)

    # Verifications for User 1
    assert rec_res_1["recommendation"] is not None, "Recommendation should not be None"
    assert rec_res_1["targeted_topic"] == "sliding-window", f"Expected targeted_topic 'sliding-window', got '{rec_res_1['targeted_topic']}'"
    assert "similarity to your recent mistake in sliding-window" in rec_res_1["reason"], (
        f"Expected reason to mention similarity to past mistake, got: {rec_res_1['reason']}"
    )
    print("\nPASSED: User 1 received vector-similarity recommendation from 'sliding-window' with reason mentioning similarity to past mistake!")

    # 2. Create User 2 (No history)
    email_user_2 = f"vec_test_user2_{uuid.uuid4().hex[:6]}@example.com"
    user2_res = await get_or_create_user(email=email_user_2, display_name="Vector Test User 2")
    user_id_2 = user2_res["user_id"]
    print(f"\nCreated Test User 2 (No History): {user_id_2} ({email_user_2})")

    print("\n--- Test User 2 (No History / Fallback) ---")
    rec_res_2 = await suggest_next_problem(user_id=user_id_2)
    print("Recommendation Result for User 2:")
    print(rec_res_2)

    # Verifications for User 2
    assert rec_res_2["recommendation"] is not None, "Recommendation should not be None for user 2"
    assert ("Note: Vector/embedding-based similarity filtering is not yet enabled." in rec_res_2["reason"]
            or "Selected weak topic" in rec_res_2["reason"])
    print("\nPASSED: User 2 (no history) fallback worked cleanly with standard structured recommendation path!")

    # Cleanup test data
    print("\n--- Cleaning up test data ---")
    await cleanup_test_users([user_id_1, user_id_2])
    print("Cleanup completed successfully.")

    await close_pool()
    print("\n==================================================")
    print("  VECTOR SIMILARITY RECOMMENDATION TESTS PASSED!  ")
    print("==================================================")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_verification())
