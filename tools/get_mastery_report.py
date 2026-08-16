import logging
import time
from typing import Optional, Dict, Any
from uuid import UUID
from database.connection import get_db_connection
from database.queries import get_user_mastery_report_rows, get_user

from tools.get_or_create_user import verify_user_token

logger = logging.getLogger(__name__)


async def get_mastery_report(
    user_id: str, topic: Optional[str] = None, token: Optional[str] = None
) -> Dict[str, Any]:
    """Fetch user's DSA topic mastery report.

    Always pass the token received from get_or_create_user. Never use a user_id
    that wasn't returned by get_or_create_user in this session.

    Args:
        user_id: The UUID string of the user.
        topic: Optional topic slug to filter results for a single topic (e.g. 'sliding-window').
               If omitted or null, returns mastery data for all topics.
        token: Optional JWT auth token returned by get_or_create_user.

    Returns:
        Dict with key 'topics' containing a list of topic mastery summaries:
        {"topics": [{"slug": str, "mastery_score": float, "last_practiced_at": str or None}]}
    """
    tool_name = "get_mastery_report"
    start = time.time()
    logger.info(f"Tool called: {tool_name} for user {user_id}")

    if token:
        try:
            payload = verify_user_token(token)
            if payload["user_id"] != user_id:
                raise ValueError(
                    "Access denied: token does not match user_id. "
                    "You can only access your own data."
                )
        except ValueError as e:
            raise ValueError(str(e))

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

    duration = round((time.time() - start) * 1000, 2)
    logger.info(f"Tool completed: {tool_name} in {duration}ms")

    return {"topics": topics_list}

