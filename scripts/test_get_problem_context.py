import asyncio
import logging
import uuid
from database.connection import get_db_connection, close_pool
from database.queries import (
    get_all_problems_with_topics,
    insert_attempt,
    insert_embedding,
)
from embeddings.gemini_client import GeminiEmbedder
from tools.get_or_create_user import get_or_create_user
from tools.get_problem_context import get_problem_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting test_get_problem_context integration test...")
    embedder = GeminiEmbedder()

    # 1. Test brand new user with no history
    test_email_new = f"test_context_new_{uuid.uuid4().hex[:6]}@example.com"
    new_user_res = await get_or_create_user(email=test_email_new, display_name="Brand New User")
    new_user_id = new_user_res["user_id"]
    logger.info(f"Created brand new user: {new_user_id}")

    empty_res = await get_problem_context(
        user_id=new_user_id,
        problem_statement="Given an array of integers, return indices of two numbers that add up to target.",
    )
    assert empty_res["matches"] == [], f"Expected empty matches, got {empty_res['matches']}"
    assert "note" in empty_res, "Expected 'note' field for empty matches"
    assert (
        empty_res["note"] == "No similar past attempts found. Keep practicing to build your history!"
    ), f"Unexpected note text: {empty_res['note']}"
    logger.info("PASSED: Brand new user returns empty matches with note.")

    # 2. Test user with past attempts & code embeddings
    test_email = f"test_context_user_{uuid.uuid4().hex[:6]}@example.com"
    user_res = await get_or_create_user(email=test_email, display_name="Context Test User")
    user_id = user_res["user_id"]
    logger.info(f"Created test user: {user_id}")

    created_attempt_ids = []
    created_embedding_ids = []
    created_mistake_ids = []

    async with get_db_connection() as conn:
        problems = await get_all_problems_with_topics(conn)
        assert len(problems) >= 2, "Need at least 2 problems in DB for testing"

        prob1 = problems[0]
        prob2 = problems[1]

        # Create Attempt 1 (pass)
        attempt1 = await insert_attempt(
            conn,
            user_id=user_id,
            problem_id=prob1["id"],
            code_s3_key=None,
            outcome="pass",
            complexity_achieved="O(n)",
            time_taken_seconds=300,
        )
        created_attempt_ids.append(attempt1.id)

        # Create Attempt 2 (fail with mistake)
        attempt2 = await insert_attempt(
            conn,
            user_id=user_id,
            problem_id=prob2["id"],
            code_s3_key=None,
            outcome="fail",
            complexity_achieved="O(n^2)",
            time_taken_seconds=600,
        )
        created_attempt_ids.append(attempt2.id)

        # Insert mistake record for Attempt 2
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO mistakes (user_id, attempt_id, summary, category)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (user_id, str(attempt2.id), "Off-by-one error in sliding window loop condition", "logic_error"),
            )
            mistake_row = await cur.fetchone()
            created_mistake_ids.append(mistake_row[0])

        # Embed code snippets for both attempts
        code1 = "def solution(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        diff = target - num\n        if diff in seen:\n            return [seen[diff], i]\n        seen[num] = i\n"
        code2 = "def solution(s):\n    left = 0\n    for right in range(len(s)):\n        if s[right] in s[left:right]:\n            left += 1\n"

        vec1 = embedder.embed(code1)
        vec2 = embedder.embed(code2)

        emb1 = await insert_embedding(conn, "code_submission", attempt1.id, vec1)
        emb2 = await insert_embedding(conn, "code_submission", attempt2.id, vec2)
        created_embedding_ids.append(emb1["id"])
        created_embedding_ids.append(emb2["id"])

        await conn.commit()
        logger.info(f"Inserted 2 attempts, 1 mistake, and 2 code_submission embeddings.")

    # 3. Call get_problem_context
    query_statement = "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target."
    context_res = await get_problem_context(user_id=user_id, problem_statement=query_statement)

    assert "matches" in context_res, "Response missing 'matches' key"
    assert "note" not in context_res, "Response should NOT contain 'note' when matches are present"
    matches = context_res["matches"]
    assert len(matches) > 0, "Expected matches in response"
    logger.info(f"Received {len(matches)} match(es).")

    # 4. Verify match structure and distances
    import json
    print("\n=== ACTUAL MATCH OBJECTS RETURNED ===")
    print(json.dumps(context_res, indent=2))
    print("=====================================\n")

    distances = [m["distance"] for m in matches]
    assert distances == sorted(distances), f"Distances are not in ascending order: {distances}"
    logger.info(f"PASSED: Distances are strictly in ascending order: {distances}")

    for match in matches:
        assert "attempt_id" in match, "Match missing attempt_id"
        assert "outcome" in match, "Match missing outcome"
        assert "complexity_achieved" in match, "Match missing complexity_achieved"
        assert "mistake_summary" in match, "Match missing mistake_summary"
        assert "distance" in match, "Match missing distance"

        dist = match["distance"]
        assert isinstance(dist, float), f"Distance {dist} is not a float"
        assert 0.0 <= dist <= 2.0, f"Distance {dist} out of expected range [0, 2]"

    # Verify attempt with mistake record has non-null mistake_summary
    attempt2_matches = [m for m in matches if m["attempt_id"] == str(attempt2.id)]
    if attempt2_matches:
        assert attempt2_matches[0]["mistake_summary"] == "Off-by-one error in sliding window loop condition"
        logger.info("PASSED: mistake_summary populated correctly for failed attempt.")

    # 5. Cleanup test data
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM users WHERE id = %s OR id = %s", (user_id, new_user_id))
        await conn.commit()
    logger.info("Cleaned up test users and cascade deleted associated records.")

    await close_pool()
    logger.info("Integration test PASSED successfully!")


if __name__ == "__main__":
    asyncio.run(main())
