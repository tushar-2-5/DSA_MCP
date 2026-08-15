import logging
import time
from typing import Dict, Any
from uuid import UUID
from database.connection import get_db_connection
from database.queries import (
    get_user,
    get_user_topic_masteries,
    get_unattempted_problem_for_topic,
    find_most_recent_mistake_embedding,
    find_similar_unattempted_problems,
)
from memory.recommendation import pick_weak_topic, get_difficulty_band
from core.logging import logger


def format_progression_info(mastery_score: float, band: str) -> str:
    """Format progression info string based on mastery score and difficulty band."""
    if band == "Easy":
        return f"Based on your mastery ({mastery_score:.2f}), starting with Easy problems."
    elif band == "Medium":
        return f"Based on your mastery ({mastery_score:.2f}), you're ready for Medium problems."
    else:
        return f"Your mastery ({mastery_score:.2f}) qualifies you for Hard problems. Here's a challenge:"


async def suggest_next_problem(user_id: str) -> Dict[str, Any]:
    """Suggest the next DSA problem for a user based on their topic mastery scores,
    target difficulty band, and similarity to past mistakes.

    Use this tool when the user asks for a problem recommendation, what to practice next,
    or next steps (e.g., 'what problem should I solve next?', 'give me a practice problem').

    Args:
        user_id: The UUID string of the user.

    Returns:
        Dict matching contract:
        {
            "recommendation": {"id": str, "title": str, "difficulty": str} or None,
            "targeted_topic": str,
            "mastery_score": float,
            "reason": str or None
        }
    """
    tool_name = "suggest_next_problem"
    start = time.time()
    logger.info(f"Tool called: {tool_name} for user {user_id}")

    try:
        UUID(user_id)
    except (ValueError, TypeError):
        raise ValueError("user_id must be a valid UUID string.")

    async with get_db_connection() as conn:
        user = await get_user(conn, user_id)
        if not user:
            raise ValueError(
                f"No user found for user_id {user_id}. Call get_or_create_user first to register."
            )

        topic_masteries = await get_user_topic_masteries(conn, user_id)
        if not topic_masteries:
            from psycopg.rows import dict_row
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT id AS topic_id, slug FROM topics ORDER BY slug ASC")
                rows = await cur.fetchall()
                topic_masteries = [
                    {"topic_id": str(r["topic_id"]), "slug": r["slug"], "mastery_score": 0.0}
                    for r in rows
                ]

        if not topic_masteries:
            duration = round((time.time() - start) * 1000, 2)
            logger.info(f"Tool completed: {tool_name} in {duration}ms")
            return {
                "recommendation": None,
                "targeted_topic": "",
                "mastery_score": 0.0,
                "reason": "No topics found in the database. Vector/embedding-based similarity is not enabled.",
            }

        chosen_topic = pick_weak_topic(topic_masteries, epsilon=0.2)
        chosen_topic_id = chosen_topic["topic_id"]
        chosen_slug = chosen_topic["slug"]
        chosen_mastery = chosen_topic["mastery_score"]
        diff_band = get_difficulty_band(chosen_mastery)
        chosen_bands = [diff_band.lower(), diff_band.capitalize(), diff_band.upper()]

        # 1. Check if a mistake embedding exists for the user in this weak topic
        mistake_vector = await find_most_recent_mistake_embedding(
            conn, user_id, chosen_topic_id
        )
        if mistake_vector:
            similar_problems = await find_similar_unattempted_problems(
                conn, user_id, chosen_topic_id, chosen_bands, mistake_vector, limit=5
            )
            if similar_problems:
                top_cand = similar_problems[0]
                logger.info("suggestion_served", user_id=str(user_id), topic=chosen_slug)
                progression_str = format_progression_info(chosen_mastery, diff_band)
                return {
                    "recommendation": {
                        "id": top_cand["id"],
                        "title": top_cand["title"],
                        "difficulty": top_cand["difficulty"],
                    },
                    "targeted_topic": chosen_slug,
                    "mastery_score": chosen_mastery,
                    "reason": f"{progression_str} Selected based on similarity to your recent mistake in {chosen_slug}.",
                }

        # 2. Fall back to structured behavior if no mistake embeddings exist or no similar unattempted candidates
        ordered_topics = [chosen_topic] + [
            t for t in topic_masteries if t["topic_id"] != chosen_topic.get("topic_id")
        ]

        found_problem = None
        found_topic = None
        found_diff_band = diff_band
        fallback_used = False

        for topic in ordered_topics:
            # Skip micro-topics
            if topic.get('problem_count', 999) < 5 and topic.get('mastery_score', 0) == 0:
                continue

            topic_id = topic["topic_id"]
            mastery_score = topic["mastery_score"]
            cur_diff_band = get_difficulty_band(mastery_score)
            bands = [cur_diff_band.lower(), cur_diff_band.capitalize(), cur_diff_band.upper()]

            problem, is_fallback = await get_unattempted_problem_for_topic(
                conn, user_id, topic_id, bands
            )
            if problem:
                found_problem = problem
                found_topic = topic
                found_diff_band = cur_diff_band
                fallback_used = is_fallback
                break

        if not found_problem:
            duration = round((time.time() - start) * 1000, 2)
            logger.info(f"Tool completed: {tool_name} in {duration}ms")
            return {
                "recommendation": None,
                "targeted_topic": chosen_topic.get("slug", ""),
                "mastery_score": chosen_topic.get("mastery_score", 0.0),
                "reason": "No unattempted problems remaining across any topics.",
            }

        targeted_slug = found_topic["slug"]
        mastery_score = found_topic["mastery_score"]
        progression_str = format_progression_info(mastery_score, found_diff_band)

        rec = {
            "id": str(found_problem.id),
            "title": found_problem.title,
            "difficulty": found_problem.difficulty,
        }

        if not fallback_used:
            reason = f"{progression_str} Targeted topic '{targeted_slug}'."
        else:
            reason = (
                f"{progression_str} Targeted topic '{targeted_slug}' had no unattempted {found_diff_band} problems, "
                f"so fell back to difficulty '{found_problem.difficulty}'."
            )

    res = {
        "recommendation": rec,
        "targeted_topic": targeted_slug,
        "mastery_score": mastery_score,
        "reason": reason,
    }
    logger.info("suggestion_served", user_id=str(user_id), topic=targeted_slug)
    return res



