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
from memory.recommendation import pick_weak_topic, difficulty_band

logger = logging.getLogger(__name__)


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
        chosen_bands = difficulty_band(chosen_mastery)

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
                duration = round((time.time() - start) * 1000, 2)
                logger.info(f"Tool completed: {tool_name} in {duration}ms")
                return {
                    "recommendation": {
                        "id": top_cand["id"],
                        "title": top_cand["title"],
                        "difficulty": top_cand["difficulty"],
                    },
                    "targeted_topic": chosen_slug,
                    "mastery_score": chosen_mastery,
                    "reason": f"Selected based on similarity to your recent mistake in {chosen_slug} and your current mastery level",
                }

        # 2. Fall back to structured behavior if no mistake embeddings exist or no similar unattempted candidates
        ordered_topics = [chosen_topic] + [
            t for t in topic_masteries if t["topic_id"] != chosen_topic.get("topic_id")
        ]

        found_problem = None
        found_topic = None
        fallback_used = False

        for topic in ordered_topics:
            topic_id = topic["topic_id"]
            mastery_score = topic["mastery_score"]
            bands = difficulty_band(mastery_score)

            problem, is_fallback = await get_unattempted_problem_for_topic(
                conn, user_id, topic_id, bands
            )
            if problem:
                found_problem = problem
                found_topic = topic
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
        bands = difficulty_band(mastery_score)

        rec = {
            "id": str(found_problem.id),
            "title": found_problem.title,
            "difficulty": found_problem.difficulty,
        }

        if not fallback_used:
            reason = (
                f"Selected weak topic '{targeted_slug}' (mastery score: {mastery_score:.2f}) "
                f"with target difficulty band {bands}."
            )
        else:
            reason = (
                f"Selected weak topic '{targeted_slug}' (mastery score: {mastery_score:.2f}). "
                f"Target difficulty band {bands} had no unattempted problems, so fell back to problem with difficulty '{found_problem.difficulty}'."
            )

    duration = round((time.time() - start) * 1000, 2)
    logger.info(f"Tool completed: {tool_name} in {duration}ms")

    return {
        "recommendation": rec,
        "targeted_topic": targeted_slug,
        "mastery_score": mastery_score,
        "reason": reason,
    }


