from typing import Optional, Dict, Any
from uuid import UUID
from database.connection import get_db_connection
from database.queries import get_user_mastery_report_rows


async def get_mastery_report(
    user_id: str, topic: Optional[str] = None
) -> Dict[str, Any]:
    """Fetch user's DSA topic mastery report.

    Use this tool when the user asks questions about their progress, mastery,
    performance, or weaknesses (e.g., 'how am I doing?', 'what's my weak topic?',
    'show my progress on binary trees').

    Args:
        user_id: The UUID string of the user.
        topic: Optional topic slug to filter results for a single topic (e.g. 'sliding-window').
               If omitted or null, returns mastery data for all topics.

    Returns:
        Dict with key 'topics' containing a list of topic mastery summaries:
        {"topics": [{"slug": str, "mastery_score": float, "last_practiced_at": str or None}]}
    """
    try:
        UUID(user_id)
    except (ValueError, TypeError):
        raise ValueError("user_id must be a valid UUID string.")

    async with get_db_connection() as conn:
        rows = await get_user_mastery_report_rows(conn, user_id, topic_slug=topic)


    topics_list = []
    for row in rows:
        last_practiced = row["last_practiced_at"]
        if last_practiced is not None:
            last_practiced_str = last_practiced.isoformat()
        else:
            last_practiced_str = None

        topics_list.append(
            {
                "slug": row["slug"],
                "mastery_score": float(row["mastery_score"]),
                "last_practiced_at": last_practiced_str,
            }
        )

    return {"topics": topics_list}
