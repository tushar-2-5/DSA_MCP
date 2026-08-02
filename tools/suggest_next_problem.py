from typing import Dict, Any
from uuid import UUID
from database.connection import get_db_connection
from database.queries import (
    get_user_topic_masteries,
    get_unattempted_problem_for_topic,
)
from memory.recommendation import pick_weak_topic, difficulty_band


async def suggest_next_problem(user_id: str) -> Dict[str, Any]:
    """Suggest the next DSA problem for a user based on their topic mastery scores
    and target difficulty band.

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
    try:
        UUID(user_id)
    except (ValueError, TypeError):
        raise ValueError("user_id must be a valid UUID string.")

    async with get_db_connection() as conn:
        topic_masteries = await get_user_topic_masteries(conn, user_id)
        if not topic_masteries:
            return {
                "recommendation": None,
                "targeted_topic": "",
                "mastery_score": 0.0,
                "reason": "No topics found in the database. Vector/embedding-based similarity is not enabled.",
            }

        chosen_topic = pick_weak_topic(topic_masteries, epsilon=0.2)
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
            return {
                "recommendation": None,
                "targeted_topic": chosen_topic.get("slug", ""),
                "mastery_score": chosen_topic.get("mastery_score", 0.0),
                "reason": "No unattempted problems remaining across any topics. Note: Vector/embedding-based similarity filtering is not yet enabled.",
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
                f"with target difficulty band {bands}. Note: Vector/embedding-based similarity filtering is not yet enabled."
            )
        else:
            reason = (
                f"Selected weak topic '{targeted_slug}' (mastery score: {mastery_score:.2f}). "
                f"Target difficulty band {bands} had no unattempted problems, so fell back to problem with difficulty '{found_problem.difficulty}'. "
                f"Note: Vector/embedding-based similarity filtering is not yet enabled."
            )

    return {
        "recommendation": rec,
        "targeted_topic": targeted_slug,
        "mastery_score": mastery_score,
        "reason": reason,
    }
