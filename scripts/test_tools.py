import asyncio
import os
import sys
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool
from database.queries import create_user, create_topic, create_problem, upsert_mastery
from tools.get_mastery_report import get_mastery_report
from tools.log_attempt import log_attempt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_tools")


async def run_verification():
    test_email = f"tool_test_{uuid.uuid4().hex[:6]}@example.com"
    test_topic_slug = f"test-sliding-window-{uuid.uuid4().hex[:6]}"

    print("==================================================")
    print("         TASK 11 MASTERY DECAY TEST               ")
    print("==================================================")

    async with get_db_connection() as conn:
        # Step A: Setup test user, topic, and problem
        user = await create_user(conn, test_email, "Tool Test User")
        topic = await create_topic(conn, test_topic_slug, "Test Sliding Window")
        problem = await create_problem(
            conn,
            title="Two Sum Test Problem",
            statement="Given an array of integers nums and an integer target...",
            difficulty="easy",
            topic_id=topic.id,
            source="leetcode",
        )
        await conn.commit()
        print(f"Created test user_id: {user.id}")
        print(f"Created test topic_slug: {topic.slug} (id: {topic.id})")
        print(f"Created test problem_id: {problem.id}")
        print("--------------------------------------------------")

        # Step B1: Test get_mastery_report on malformed UUID (expecting ValueError)
        print("\n--- Test 1a: get_mastery_report for malformed UUID ---")
        try:
            await get_mastery_report(user_id="invalid-user-uuid")
            assert False, "Expected ValueError for malformed user_id, but none was raised"
        except ValueError as e:
            print(f"Caught expected ValueError: {e}")
        print("PASSED: Malformed user_id raises ValueError as expected.")

        # Step B2: Test get_mastery_report on fresh user with valid UUID (expecting {"topics": []})
        print("\n--- Test 1b: get_mastery_report for valid user with no data ---")
        empty_report = await get_mastery_report(user_id=str(user.id))
        print(f"Actual Output: {empty_report}")
        assert empty_report == {"topics": []}, f"Expected {{'topics': []}}, got {empty_report}"
        print("PASSED: Empty report for valid user matches contract shape exactly.")

        # Step C1: Test log_attempt with malformed UUID (expecting ValueError)
        print("\n--- Test 2a: log_attempt for malformed UUID ---")
        try:
            await log_attempt(
                user_id="invalid-user-uuid",
                problem_id=str(problem.id),
                code="print('hi')",
                outcome="pass",
            )
            assert False, "Expected ValueError for malformed user_id in log_attempt, but none was raised"
        except ValueError as e:
            print(f"Caught expected ValueError: {e}")
        print("PASSED: Malformed user_id in log_attempt raises ValueError as expected.")

        # Step C2: Test log_attempt (attempt 1: outcome='pass', optimal complexity)
        print("\n--- Test 2b: log_attempt Attempt #1 (pass + optimal complexity) ---")
        code_sample = "def twoSum(nums, target): return [0, 1]"
        log_res1 = await log_attempt(
            user_id=str(user.id),
            problem_id=str(problem.id),
            code=code_sample,
            outcome="pass",
            complexity_achieved="O(N)",
            time_taken_seconds=300,
        )
        print(f"Actual Output: {log_res1}")
        assert "attempt_id" in log_res1, "Missing 'attempt_id' in output"
        assert log_res1["status"] == "logged", f"Expected status 'logged', got {log_res1['status']}"
        # 0.0 + 0.15 (optimal pass) = 0.15
        assert log_res1["mastery_score_after"] == 0.15, f"Expected 0.15, got {log_res1['mastery_score_after']}"
        attempt_id_1 = log_res1["attempt_id"]
        print("PASSED: Attempt #1 score = 0.15.")

        # Step D1: Test Decay with non-optimal pass (+0.08)
        print("\n--- Test 3a: Backdate last_practiced_at by 14 days & test Decay + Non-Optimal Pass (+0.08) ---")
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
        await upsert_mastery(
            conn=conn,
            user_id=user.id,
            topic_id=topic.id,
            mastery_score=0.15,
            last_practiced_at=fourteen_days_ago,
        )
        await conn.commit()
        print(f"Backdated mastery last_practiced_at to: {fourteen_days_ago.isoformat()}")

        # Log attempt #2: pass, NOT optimal complexity (complexity_achieved=None) -> +0.08
        log_res2 = await log_attempt(
            user_id=str(user.id),
            problem_id=str(problem.id),
            code=code_sample,
            outcome="pass",
            complexity_achieved=None,  # Not optimal
            time_taken_seconds=120,
        )
        print(f"Actual Output Attempt #2 (complexity_achieved=None): {log_res2}")
        attempt_id_2 = log_res2["attempt_id"]

        # Breakdown:
        # Initial score = 0.150
        # Decayed score after 14 days (half-life) = 0.150 / 2 = 0.075
        # Non-optimal pass (+0.08) = 0.075 + 0.08 = 0.155
        expected_score_2 = 0.155
        actual_score_2 = log_res2["mastery_score_after"]

        print(f"  Score before decay:  0.150")
        print(f"  Decayed base score:   0.075 (after 14 days half-life)")
        print(f"  New score (+0.08):    {actual_score_2:.4f} (expected: {expected_score_2:.4f})")
        assert abs(actual_score_2 - expected_score_2) < 0.001, (
            f"Expected ~{expected_score_2}, got {actual_score_2}"
        )
        print("PASSED: Decay + non-optimal pass (+0.08) verified!")

        # Step D2: Test Decay with optimal pass (+0.15)
        print("\n--- Test 3b: Backdate last_practiced_at by 14 days & test Decay + Optimal Pass (+0.15) ---")
        await upsert_mastery(
            conn=conn,
            user_id=user.id,
            topic_id=topic.id,
            mastery_score=0.155,
            last_practiced_at=fourteen_days_ago,
        )
        await conn.commit()

        # Log attempt #3: pass, OPTIMAL complexity (complexity_achieved='O(N)') -> +0.15
        log_res3 = await log_attempt(
            user_id=str(user.id),
            problem_id=str(problem.id),
            code=code_sample,
            outcome="pass",
            complexity_achieved="O(N)",  # Optimal
            time_taken_seconds=120,
        )
        print(f"Actual Output Attempt #3 (complexity_achieved='O(N)'): {log_res3}")
        attempt_id_3 = log_res3["attempt_id"]

        # Breakdown:
        # Initial score = 0.155
        # Decayed score after 14 days (half-life) = 0.155 / 2 = 0.0775
        # Optimal pass (+0.15) = 0.0775 + 0.15 = 0.2275
        expected_score_3 = 0.2275
        actual_score_3 = log_res3["mastery_score_after"]

        print(f"  Score before decay:  0.1550")
        print(f"  Decayed base score:   0.0775 (after 14 days half-life)")
        print(f"  New score (+0.15):    {actual_score_3:.4f} (expected: {expected_score_3:.4f})")
        assert abs(actual_score_3 - expected_score_3) < 0.001, (
            f"Expected ~{expected_score_3}, got {actual_score_3}"
        )
        print("PASSED: Decay + optimal pass (+0.15) verified!")

        # Step E: Cleanup test data
        print("\n--- Cleaning up test data ---")
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM attempts WHERE id IN (%s, %s, %s)",
                (attempt_id_1, attempt_id_2, attempt_id_3),
            )
            await cur.execute("DELETE FROM mastery WHERE user_id = %s", (str(user.id),))
            await cur.execute("DELETE FROM problems WHERE id = %s", (str(problem.id),))
            await cur.execute("DELETE FROM topics WHERE id = %s", (str(topic.id),))
            await cur.execute("DELETE FROM users WHERE id = %s", (str(user.id),))
        await conn.commit()
        print("Cleanup completed successfully.")

    await close_pool()
    print("\n==================================================")
    print("       ALL DECAY VERIFICATION TESTS PASSED!       ")
    print("==================================================")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_verification())
