import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, close_pool
from database.queries import get_problem_by_title
from tools.get_or_create_user import get_or_create_user
from tools.log_attempt import log_attempt
from tools.get_mastery_report import get_mastery_report
from tools.suggest_next_problem import suggest_next_problem
from tools.flag_recurring_mistake import flag_recurring_mistake

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def create_demo_data():
    logger.info("Starting demo seed data creation...")

    # STEP 1 — Create the demo user
    email = "demo@recall.dev"
    display_name = "Alex Chen"

    user_res = await get_or_create_user(email=email, display_name=display_name)
    user_id = user_res["user_id"]
    status = user_res["status"]

    if status == "existing":
        logger.info(f"User '{email}' already exists (user_id={user_id}). Skipping attempt creation to remain idempotent.")
    else:
        logger.info(f"Created demo user '{email}' (user_id={user_id}). Logging backdated attempts...")

        now = datetime.now(timezone.utc)
        day_21 = now - timedelta(days=21)
        day_14 = now - timedelta(days=14)
        day_10 = now - timedelta(days=10)
        day_7 = now - timedelta(days=7)
        day_3 = now - timedelta(days=3)

        # Baseline unpracticed topics to 0.50 so Alex Chen's practiced topics reflect his relative progress
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO mastery (user_id, topic_id, mastery_score, last_practiced_at)
                    SELECT %s, id, 0.50, NULL
                    FROM topics
                    ON CONFLICT (user_id, topic_id) DO NOTHING
                    """,
                    (user_id,),
                )
            await conn.commit()

        # Group attempts by day to simulate realistic progression and timestamps
        attempts_by_day = [
            # Day -21 (3 weeks ago)
            (
                day_21,
                [
                    {
                        "title": "Two Sum",
                        "code": """def twoSum(nums: list[int], target: int) -> list[int]:
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
""",
                        "outcome": "pass",
                        "complexity_achieved": "O(N)",
                        "time_taken_seconds": 180,
                    },
                    {
                        "title": "Contains Duplicate",
                        "code": """def containsDuplicate(nums: list[int]) -> bool:
    seen = set()
    for num in nums:
        if num in seen:
            return True
        seen.add(num)
    return False
""",
                        "outcome": "pass",
                        "complexity_achieved": "O(N)",
                        "time_taken_seconds": 120,
                    },
                ],
            ),
            # Day -14 (2 weeks ago)
            (
                day_14,
                [
                    {
                        "title": "Longest Substring Without Repeating Characters",
                        "code": """def lengthOfLongestSubstring(s: str) -> int:
    left = 0
    max_len = 0
    char_set = set()
    for right in range(len(s)):
        # Bug: Forgot to shrink window from left when duplicate found
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
""",
                        "outcome": "fail",
                        "mistake_category": "sliding_window_shrink_missing",
                        "mistake_summary": "Forgot to shrink window from left when duplicate found — window expanded incorrectly",
                    },
                    {
                        "title": "Minimum Window Substring",
                        "code": """def minWindow(s: str, t: str) -> str:
    from collections import Counter
    target_counts = Counter(t)
    window_counts = {}
    left = 0
    min_len = float('inf')
    res = ""
    for right in range(len(s)):
        c = s[right]
        window_counts[c] = window_counts.get(c, 0) + 1
        # Bug: left pointer not moved when constraint satisfied / violated, missing window shrink loop
        if all(window_counts.get(k, 0) >= v for k, v in target_counts.items()):
            if right - left + 1 < min_len:
                min_len = right - left + 1
                res = s[left:right+1]
    return res
""",
                        "outcome": "fail",
                        "mistake_category": "sliding_window_shrink_missing",
                        "mistake_summary": "Same window shrink error — left pointer not moved when constraint violated",
                    },
                ],
            ),
            # Day -10 (10 days ago)
            (
                day_10,
                [
                    {
                        "title": "Climbing Stairs",
                        "code": """def climbStairs(n: int) -> int:
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1], dp[2] = 1, 2
    for i in range(3, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]
""",
                        "outcome": "pass",
                        "complexity_achieved": "O(N)",
                        "time_taken_seconds": 240,
                    },
                    {
                        "title": "Coin Change",
                        "code": """def coinChange(coins: list[int], amount: int) -> int:
    memo = {}
    def dp(rem):
        if rem == 0: return 0
        if rem < 0: return float('inf')
        if rem in memo: return memo[rem]
        res = float('inf')
        for coin in coins:
            # Bug: Used top-down but memoized wrong subproblem state
            res = min(res, 1 + dp(rem))
        memo[rem] = res
        return res
    ans = dp(amount)
    return ans if ans != float('inf') else -1
""",
                        "outcome": "fail",
                        "mistake_category": "dp_subproblem_wrong",
                        "mistake_summary": "Incorrect subproblem definition — used top-down but memoized wrong state",
                    },
                ],
            ),
            # Day -7 (1 week ago)
            (
                day_7,
                [
                    {
                        "title": "Longest Substring Without Repeating Characters",
                        "code": """def lengthOfLongestSubstring(s: str) -> int:
    char_map = {}
    left = 0
    max_len = 0
    for right, char in enumerate(s):
        if char in char_map and char_map[char] >= left:
            left = char_map[char] + 1
        char_map[char] = right
        max_len = max(max_len, right - left + 1)
    return max_len
""",
                        "outcome": "pass",
                        "complexity_achieved": "O(N)",
                        "time_taken_seconds": 300,
                    },
                    {
                        "title": "Valid Parentheses",
                        "code": """def isValid(s: str) -> bool:
    stack = []
    mapping = {")": "(", "}": "{", "]": "["}
    for char in s:
        if char in mapping:
            top_element = stack.pop() if stack else '#'
            if mapping[char] != top_element:
                return False
        else:
            stack.append(char)
    return not stack
""",
                        "outcome": "pass",
                        "complexity_achieved": "O(N)",
                        "time_taken_seconds": 150,
                    },
                ],
            ),
            # Day -3 (3 days ago)
            (
                day_3,
                [
                    {
                        "title": "Product of Array Except Self",
                        "code": """def productExceptSelf(nums: list[int]) -> list[int]:
    n = len(nums)
    res = [1] * n
    prefix = 1
    for i in range(n):
        res[i] = prefix
        prefix *= nums[i]
    postfix = 1
    for i in range(n - 1, -1, -1):
        res[i] *= postfix
        postfix *= nums[i]
    return res
""",
                        "outcome": "pass",
                        "complexity_achieved": "O(N)",
                        "time_taken_seconds": 200,
                    },
                    {
                        "title": "Maximum Subarray",
                        "code": """def maxSubArray(nums: list[int]) -> int:
    max_sum = nums[0]
    curr_sum = nums[0]
    for num in nums[1:]:
        curr_sum = max(num, curr_sum + num)
        max_sum = max(max_sum, curr_sum)
    return max_sum
""",
                        "outcome": "pass",
                        "complexity_achieved": "O(N)",
                        "time_taken_seconds": 180,
                    },
                ],
            ),
        ]

        attempt_count = 0
        async with get_db_connection() as conn:
            for day_date, attempts_list in attempts_by_day:
                for item in attempts_list:
                    attempt_count += 1
                    prob = await get_problem_by_title(conn, item["title"])
                    if not prob:
                        raise ValueError(f"Problem '{item['title']}' not found in database.")

                    log_res = await log_attempt(
                        user_id=user_id,
                        problem_id=str(prob.id),
                        code=item["code"],
                        outcome=item["outcome"],
                        complexity_achieved=item.get("complexity_achieved"),
                        time_taken_seconds=item.get("time_taken_seconds"),
                        mistake_summary=item.get("mistake_summary"),
                        mistake_category=item.get("mistake_category"),
                    )
                    attempt_id = log_res["attempt_id"]

                    async with conn.cursor() as cur:
                        await cur.execute(
                            "UPDATE attempts SET created_at = %s WHERE id = %s",
                            (day_date, attempt_id),
                        )
                        await cur.execute(
                            "UPDATE mistakes SET created_at = %s WHERE attempt_id = %s",
                            (day_date, attempt_id),
                        )
                    await conn.commit()
                    logger.info(
                        f"[{attempt_count}/10] Logged attempt for '{item['title']}' "
                        f"({item['outcome']}) on {day_date.strftime('%Y-%m-%d')}"
                    )

                # Update mastery.last_practiced_at for topics practiced on this day
                for item in attempts_list:
                    prob = await get_problem_by_title(conn, item["title"])
                    if prob and prob.topic_id:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "UPDATE mastery SET last_practiced_at = %s WHERE user_id = %s AND topic_id = %s",
                                (day_date, user_id, str(prob.topic_id)),
                            )
                        await conn.commit()

    # STEP 3 — Verify the demo state
    logger.info("Verifying demo state across all 3 tools...")

    print("\n==================================================")
    print("VERIFICATION 1: get_mastery_report")
    print("==================================================")
    mastery_report = await get_mastery_report(user_id=user_id)
    print(json.dumps(mastery_report, indent=2))

    print("\n==================================================")
    print("VERIFICATION 2: suggest_next_problem")
    print("==================================================")
    recommendation = await suggest_next_problem(user_id=user_id)
    print(json.dumps(recommendation, indent=2))

    print("\n==================================================")
    print("VERIFICATION 3: flag_recurring_mistake")
    print("==================================================")
    sliding_window_buggy_code = """def characterReplacement(s: str, k: int) -> int:
    left = 0
    max_len = 0
    char_set = set()
    for right in range(len(s)):
        # Bug: Forgot to shrink window from left when constraint violated
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
"""
    recurring_mistake = await flag_recurring_mistake(
        user_id=user_id, code_in_progress=sliding_window_buggy_code
    )
    print(json.dumps(recurring_mistake, indent=2))
    print("==================================================\n")

    await close_pool()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_demo_data())
