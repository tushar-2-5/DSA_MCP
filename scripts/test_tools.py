import asyncio
import os
import sys
import uuid
import logging
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool
from database.queries import create_user, create_topic, create_problem
from tools.get_mastery_report import get_mastery_report
from tools.log_attempt import log_attempt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_tools")


async def run_verification():
    test_email = f"tool_test_{uuid.uuid4().hex[:6]}@example.com"
    test_topic_slug = f"test-sliding-window-{uuid.uuid4().hex[:6]}"
    
    print("==================================================")
    print("          TASK 5 TOOL VERIFICATION TEST           ")
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

        # Step C2: Test log_attempt (outcome: 'pass')
        print("\n--- Test 2b: log_attempt (outcome='pass') ---")
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
        assert log_res1["mastery_score_after"] == 0.1, f"Expected 0.1, got {log_res1['mastery_score_after']}"
        attempt_id_1 = log_res1["attempt_id"]
        print("PASSED: log_attempt output matches contract shape exactly.")

        # Step D: Test get_mastery_report after log_attempt (all topics & filtered by topic)
        print("\n--- Test 3: get_mastery_report (all topics) ---")
        report_all = await get_mastery_report(user_id=str(user.id))
        print(f"Actual Output: {report_all}")
        assert len(report_all["topics"]) == 1, "Expected 1 topic in report"
        topic_entry = report_all["topics"][0]
        assert topic_entry["slug"] == test_topic_slug
        assert topic_entry["mastery_score"] == 0.1
        assert topic_entry["last_practiced_at"] is not None
        print("PASSED: get_mastery_report matches contract shape exactly.")

        print("\n--- Test 4: get_mastery_report (filtered by topic) ---")
        report_filtered = await get_mastery_report(user_id=str(user.id), topic=test_topic_slug)
        print(f"Actual Output (matching topic): {report_filtered}")
        assert len(report_filtered["topics"]) == 1
        
        report_non_matching = await get_mastery_report(user_id=str(user.id), topic="non-existent-topic-slug")
        print(f"Actual Output (non-matching topic): {report_non_matching}")
        assert report_non_matching == {"topics": []}
        print("PASSED: Topic filtering works correctly.")

        # Step E: Test log_attempt (outcome: 'fail')
        print("\n--- Test 5: log_attempt (outcome='fail') ---")
        log_res2 = await log_attempt(
            user_id=str(user.id),
            problem_id=str(problem.id),
            code=code_sample,
            outcome="fail",
            complexity_achieved=None,
            time_taken_seconds=120,
        )
        print(f"Actual Output: {log_res2}")
        attempt_id_2 = log_res2["attempt_id"]
        # 0.1 - 0.05 = 0.05
        assert log_res2["mastery_score_after"] == 0.05, f"Expected 0.05, got {log_res2['mastery_score_after']}"
        print("PASSED: log_attempt score decrease verified.")

        # Step F: Cleanup test data
        print("\n--- Cleaning up test data ---")
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM attempts WHERE id IN (%s, %s)", (attempt_id_1, attempt_id_2))
            await cur.execute("DELETE FROM mastery WHERE user_id = %s", (str(user.id),))
            await cur.execute("DELETE FROM problems WHERE id = %s", (str(problem.id),))
            await cur.execute("DELETE FROM topics WHERE id = %s", (str(topic.id),))
            await cur.execute("DELETE FROM users WHERE id = %s", (str(user.id),))
        await conn.commit()
        print("Cleanup completed successfully.")

    await close_pool()
    print("\n==================================================")
    print("       ALL TOOL VERIFICATION TESTS PASSED!        ")
    print("==================================================")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_verification())
