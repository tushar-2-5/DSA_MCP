import sys
import logging
import time
from typing import Optional
from database.connection import get_db_connection
from database.queries import (
    get_user,
    get_user_topic_masteries,
    get_problems_by_company,
    get_problems_filtered,
)

from tools.get_or_create_user import verify_user_token

logging.basicConfig(stream=sys.stderr)
logger = logging.getLogger(__name__)

COMPANY_TIPS = {
    "amazon": "Amazon Tip: Focus heavily on Leadership Principles, trade-off explanations, and writing clean, scalable O(N) code.",
    "google": "Google Tip: Prioritize optimal time/space complexity, edge case handling, and clear algorithm walkthrough before coding.",
    "microsoft": "Microsoft Tip: Emphasize robust code readability, modular design, and thorough unit testing edge cases.",
    "meta": "Meta Tip: Practice rapid problem-solving speed (2 coding questions in 45 min) with zero syntax errors.",
    "apple": "Apple Tip: Pay attention to low-level optimization, memory management, and elegant data structure selection.",
}


async def study_plan(
    user_id: str, target_company: Optional[str] = None, token: Optional[str] = None
) -> str:
    """Generate a personalized DSA study plan for a user, optionally targeted for a specific company interview.

    Always pass the token received from get_or_create_user. Never use a user_id
    that wasn't returned by get_or_create_user in this session.

    Args:
        user_id: The UUID string of the user.
        target_company: Optional target company name for interview prep.
        token: JWT token returned by get_or_create_user.
               Pass this to verify you can only access your own data.
    """
    tool_name = "study_plan"
    start = time.time()
    logger.info(f"Tool called: {tool_name} for user {user_id}")

    if token:
        verify_user_token(token, user_id)

    async with get_db_connection() as conn:
        user = await get_user(conn, user_id)
        if not user:
            duration = round((time.time() - start) * 1000, 2)
            logger.info(f"Tool completed: {tool_name} in {duration}ms")
            return f"Error: User with ID '{user_id}' not found."

        masteries = await get_user_topic_masteries(conn, user_id)

        company_str = target_company.strip().lower() if target_company else None

        EXCLUDED_DEFAULT_TOPICS = {"bit-manipulation", "greedy", "math", "tries", "strings"}
        CORE_FOUNDATIONAL_TOPICS = ["arrays-hashing", "trees", "graphs", "linked-list", "binary-search"]

        active_masteries = [m for m in masteries if (m.get("mastery_score") or 0.0) > 0]
        active_slugs = {m["slug"] for m in active_masteries}

        if company_str:
            problems = await get_problems_by_company(conn, company_name=company_str, limit=10)
            if not problems:
                problems, _ = await get_problems_filtered(conn, company=company_str, limit=10)
        else:
            if active_masteries:
                # Pick problems from user's lowest active mastery topics
                weakest_topics = active_masteries[:3]
                problems = []
                for t in weakest_topics:
                    probs, _ = await get_problems_filtered(conn, topic=t["slug"], limit=3)
                    problems.extend(probs)
            else:
                # User has no mastery data yet — pick problems from core foundational topics
                problems = []
                for topic_slug in CORE_FOUNDATIONAL_TOPICS:
                    probs, _ = await get_problems_filtered(conn, topic=topic_slug, limit=2)
                    problems.extend(probs)
                    if len(problems) >= 10:
                        break

        # Filter out niche topics unless user has active mastery in them
        problems = [
            p for p in problems
            if p.get("topic_slug") not in EXCLUDED_DEFAULT_TOPICS or p.get("topic_slug") in active_slugs
        ]

    # Format Study Plan Output Markdown
    header_title = f"🎯 DSA Study Plan for {user.display_name or user.email}"
    if company_str:
        header_title += f"\n**Optimized for: {company_str.title()} interviews**"

    lines = [
        header_title,
        "=" * 50,
        "",
        "### Recommended Target Problems:",
    ]

    if not problems:
        lines.append("- No specific problems found matching criteria. Start practicing foundational topics!")
    else:
        for idx, p in enumerate(problems[:10], 1):
            diff = (p.get("difficulty") or "medium").title()
            topic = (p.get("topic_slug") or "general").replace("-", " ").title()
            title = p.get("title", "Problem")
            url = p.get("url", "#")
            count = p.get("company_count") or (len(p.get("company_tags") or []))
            lines.append(f"{idx}. **[{title}]({url})** (`{diff}`) — *{topic}* (Asked by {count} companies)")

    lines.extend([
        "",
        "### Topic Mastery Breakdown:",
    ])
    if not active_masteries:
        lines.append("- 🚀 No mastery data yet! Log your first attempt to start tracking.")
    else:
        for m in active_masteries[:5]:
            score_pct = int(m.get("mastery_score", 0.0) * 100)
            slug_name = m.get("slug", "").replace("-", " ").title()
            lines.append(f"- **{slug_name}**: {score_pct}% mastery")

    if company_str:
        tip = COMPANY_TIPS.get(company_str, f"{company_str.title()} Tip: Practice explaining your thought process clearly and analyzing time/space complexity out loud.")
        lines.extend([
            "",
            "---",
            f"💡 **Interview Prep Tip:** {tip}",
        ])
    else:
        lines.extend([
            "",
            "---",
            "💡 **Study Tip:** Focus on practicing 1-2 weak topics daily to prevent exponential mastery decay!",
        ])

    duration = round((time.time() - start) * 1000, 2)
    logger.info(f"Tool completed: {tool_name} in {duration}ms")

    return "\n".join(lines)

