import asyncio
import json
import logging
import uuid
from database.connection import get_db_connection, close_pool
from database.queries import get_all_problems_with_topics
from tools.get_or_create_user import get_or_create_user
from tools.log_attempt import log_attempt
from tools.flag_recurring_mistake import flag_recurring_mistake, SIMILARITY_THRESHOLD

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting test_flag_recurring_mistake integration test...")

    # 1. Create test user
    test_email = f"test_flag_{uuid.uuid4().hex[:6]}@example.com"
    user_res = await get_or_create_user(email=test_email, display_name="Flag Test User")
    user_id = user_res["user_id"]
    logger.info(f"Created test user: {user_id}")

    async with get_db_connection() as conn:
        problems = await get_all_problems_with_topics(conn)
        assert len(problems) >= 3, "Need at least 3 problems for testing"
        sw_problems = [p for p in problems if p["topic_slug"] == "sliding-window"]
        if len(sw_problems) < 3:
            sw_problems = problems[:3]

    # 2. Log 3 failed attempts with the same mistake pattern
    failing_code_template = """def solution(nums, target):
    left = 0
    total = 0
    for right in range(len(nums)):
        total += nums[right]
        while total >= target:
            left += 1  # Bug: updated left pointer before subtracting nums[left]
"""

    mistake_category = "sliding_window_off_by_one"
    mistake_summary = "Updating left window boundary index without subtracting outgoing element"

    for i in range(3):
        prob = sw_problems[i]
        log_res = await log_attempt(
            user_id=user_id,
            problem_id=str(prob["id"]),
            code=failing_code_template,
            outcome="fail",
            complexity_achieved="O(N^2)",
            time_taken_seconds=300,
            mistake_summary=mistake_summary,
            mistake_category=mistake_category,
        )
        logger.info(f"Logged failed attempt {i+1}/3 for problem '{prob['title']}': attempt_id={log_res['attempt_id']}")

    # 3. Simulate writing new code with the same mistake pattern
    code_in_progress = """def min_sub_array_len(target, nums):
    left = 0
    curr_sum = 0
    for right in range(len(nums)):
        curr_sum += nums[right]
        while curr_sum >= target:
            left += 1  # Same mistake pattern
"""

    logger.info("Calling flag_recurring_mistake with similar code in progress...")
    result = await flag_recurring_mistake(user_id=user_id, code_in_progress=code_in_progress)

    print("\n=== ACTUAL FLAGGED RESPONSE ===")
    print(json.dumps(result, indent=2))
    print("===============================\n")

    # 4. Verify result contract and properties
    assert "checked" in result and result["checked"] is True, "Expected 'checked': True in response"
    assert "flagged" in result, "Expected 'flagged' key in response"
    flagged = result["flagged"]
    assert len(flagged) == 1, f"Expected exactly 1 deduplicated flagged mistake, got {len(flagged)}"

    for item in flagged:
        assert "summary" in item, "Item missing 'summary'"
        assert "category" in item, "Item missing 'category'"
        assert "distance" in item, "Item missing 'distance'"
        assert "occurrences" in item, "Item missing 'occurrences'"

        dist = item["distance"]
        assert dist < SIMILARITY_THRESHOLD, f"Distance {dist} is not strictly less than threshold {SIMILARITY_THRESHOLD}"
        assert 0.0 <= dist <= 2.0, f"Distance {dist} out of bounds"
        assert item["occurrences"] >= 3, f"Expected occurrences >= 3, got {item['occurrences']}"

    logger.info("PASSED: Flagged mistake matched expected pattern, distance threshold, and occurrences.")

    # 5. Test completely unrelated code (should return empty flagged array)
    unrelated_code = """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def max_depth(root: TreeNode) -> int:
    if not root:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))
"""

    logger.info("Calling flag_recurring_mistake with unrelated binary tree code...")
    unrelated_res = await flag_recurring_mistake(user_id=user_id, code_in_progress=unrelated_code)

    assert unrelated_res["checked"] is True, "Expected 'checked': True for unrelated code"
    assert unrelated_res["flagged"] == [], f"Expected empty flagged array for unrelated code, got {unrelated_res['flagged']}"
    logger.info("PASSED: Unrelated code returned empty flagged array (no false positives).")

    # 6. Cleanup test user and data
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        await conn.commit()
    logger.info("Cleaned up test user and cascade deleted records.")

    await close_pool()
    logger.info("Integration test PASSED successfully!")


if __name__ == "__main__":
    asyncio.run(main())
