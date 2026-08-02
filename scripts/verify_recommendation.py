import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool
from database.queries import get_topic_by_slug, get_problem
from tools.log_attempt import log_attempt
from tools.suggest_next_problem import suggest_next_problem
from tools.get_mastery_report import get_mastery_report
from tools.get_or_create_user import get_or_create_user
from psycopg.rows import dict_row


async def run_verification():
    test_email = f"rec_test_{uuid.uuid4().hex[:6]}@example.com"
    print("==================================================")
    print("      TASK 13 RECOMMENDATION LOGIC TEST          ")
    print("==================================================")

    # Step A: Create test user via get_or_create_user
    user_res = await get_or_create_user(email=test_email, display_name="Rec Test User")
    user_id_str = user_res["user_id"]
    print(f"Created test user_id: {user_id_str}")
    print("--------------------------------------------------")

    async with get_db_connection() as conn:

        # Step B: Call suggest_next_problem on fresh user (0 mastery)
        print("\n--- Test 1: Recommendation for Fresh User (Mastery = 0.0) ---")
        rec1 = await suggest_next_problem(user_id=user_id_str)
        print(f"Output: {rec1}")
        assert rec1["recommendation"] is not None
        assert rec1["mastery_score"] == 0.0
        assert rec1["recommendation"]["difficulty"] == "easy"
        print(f"PASSED: Recommended problem '{rec1['recommendation']['title']}' (Difficulty: {rec1['recommendation']['difficulty']}) in topic '{rec1['targeted_topic']}'")

        # Step C: Log a solution attempt for the recommended problem
        rec1_prob_id = rec1["recommendation"]["id"]
        print(f"\n--- Test 2: Log attempt for problem {rec1_prob_id} ---")
        log_res = await log_attempt(
            user_id=user_id_str,
            problem_id=rec1_prob_id,
            code="def solution(): pass",
            outcome="pass",
            complexity_achieved="O(1)",
        )
        print(f"Log Output: {log_res}")
        print(f"New mastery score after pass: {log_res['mastery_score_after']}")

        # Step D: Call suggest_next_problem again after boosting topic 1
        print("\n--- Test 3: Recommendation after 1st attempt ---")
        rec2 = await suggest_next_problem(user_id=user_id_str)
        print(f"Output: {rec2}")
        assert rec2["recommendation"] is not None
        print(f"PASSED: Recommended problem '{rec2['recommendation']['title']}' (Difficulty: {rec2['recommendation']['difficulty']}) in topic '{rec2['targeted_topic']}'")

        # Step E: Fetch mastery report for user
        print("\n--- Test 4: Mastery report summary ---")
        report = await get_mastery_report(user_id=user_id_str)
        print(f"Report: {report}")

        # Step F: Exhaust all easy 'arrays-hashing' problems and test fallback transparency
        print("\n--- Test 5: Exhaust all 'easy' arrays-hashing problems ---")
        topic_ah = await get_topic_by_slug(conn, "arrays-hashing")
        assert topic_ah is not None

        # Fetch all easy problems for arrays-hashing
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, title FROM problems WHERE topic_id = %s AND difficulty = 'easy'",
                (str(topic_ah.id),),
            )
            easy_probs = await cur.fetchall()

        print(f"Found {len(easy_probs)} easy problems in arrays-hashing. Attempting all of them...")
        for p in easy_probs:
            await log_attempt(
                user_id=user_id_str,
                problem_id=str(p["id"]),
                code="def solution(): pass",
                outcome="pass",
                complexity_achieved="O(1)",
            )

        # Set arrays-hashing mastery to 0.20 (so target difficulty band is still ['easy'])
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE mastery SET mastery_score = 0.20 WHERE user_id = %s AND topic_id = %s",
                (user_id_str, str(topic_ah.id)),
            )
        await conn.commit()

        # Set all other topics' mastery scores higher so arrays-hashing (0.20) is chosen as weakest topic
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM topics WHERE id != %s", (str(topic_ah.id),)
            )
            other_topics = await cur.fetchall()
            for ot in other_topics:
                await cur.execute(
                    """
                    INSERT INTO mastery (user_id, topic_id, mastery_score, last_practiced_at)
                    VALUES (%s, %s, 0.90, NOW())
                    ON CONFLICT (user_id, topic_id) DO UPDATE SET mastery_score = 0.90
                    """,
                    (user_id_str, str(ot[0])),
                )
        await conn.commit()

        rec5 = await suggest_next_problem(user_id=user_id_str)
        print(f"Output when easy problems exhausted: {rec5}")
        assert rec5["recommendation"] is not None
        assert rec5["targeted_topic"] == "arrays-hashing"
        # Confirm that reason explicitly discloses the fallback to medium/hard
        assert "Target difficulty band ['easy'] had no unattempted problems" in rec5["reason"]
        assert rec5["recommendation"]["difficulty"] != "easy"
        print(f"PASSED: Transparently fell back to difficulty '{rec5['recommendation']['difficulty']}' and disclosed in reason string!")

        # Cleanup test data
        print("\n--- Cleaning up test user & attempts ---")
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM attempts WHERE user_id = %s", (user_id_str,))
            await cur.execute("DELETE FROM mastery WHERE user_id = %s", (user_id_str,))
            await cur.execute("DELETE FROM users WHERE id = %s", (user_id_str,))
        await conn.commit()
        print("Cleanup completed successfully.")

    await close_pool()
    print("\n==================================================")
    print("      ALL RECOMMENDATION LOGIC TESTS PASSED!     ")
    print("==================================================")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_verification())
