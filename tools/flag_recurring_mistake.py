from collections import Counter
from typing import Dict, Any, Optional
from uuid import UUID
from database.connection import get_db_connection
from database.queries import get_user, find_similar_past_mistakes
from embeddings.gemini_client import GeminiEmbedder
from tools.get_or_create_user import verify_user_token

SIMILARITY_THRESHOLD: float = 0.35


async def flag_recurring_mistake(
    user_id: str, code_in_progress: str, token: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze code currently being written against past mistake embeddings to warn of recurring mistakes.

    Always pass the token received from get_or_create_user. Never use a user_id
    that wasn't returned by get_or_create_user in this session.

    Args:
        user_id: The UUID string of the registered user.
        code_in_progress: The source code currently being written by the user.
        token: Optional JWT auth token returned by get_or_create_user.

    Returns:
        Dict matching contract:
        {"flagged": [...], "checked": True, "summary": str, "tip": str|None}
    """
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

    if not code_in_progress or not isinstance(code_in_progress, str) or not code_in_progress.strip():
        raise ValueError("code_in_progress must be a non-empty string.")

    async with get_db_connection() as conn:
        user = await get_user(conn, user_id)
        if not user:
            raise ValueError(
                f"No user found for user_id {user_id}. Call get_or_create_user first to register."
            )

        embedder = GeminiEmbedder()
        query_vector = embedder.embed(code_in_progress)

        mistakes_raw = await find_similar_past_mistakes(
            conn,
            user_id=user_id,
            query_vector=query_vector,
            threshold=SIMILARITY_THRESHOLD,
            limit=3,
        )

    flagged = [
        {
            "summary": m["summary"],
            "category": m["category"],
            "distance": round(float(m["distance"]), 4),
            "occurrences": m["occurrences"],
        }
        for m in mistakes_raw
    ]

    if not flagged:
        return {
            "flagged": [],
            "checked": True,
            "summary": "✅ No recurring mistakes detected. Clean code!",
            "tip": None,
        }

    n = len(flagged)
    summary = f"Found {n} recurring mistake pattern{'s' if n > 1 else ''} in your history."

    categories = [m["category"] for m in flagged if m.get("category")]
    if categories:
        most_common_category = Counter(categories).most_common(1)[0][0]
        tip = f"💡 Most common mistake: {most_common_category}. Focus on this pattern."
    else:
        tip = None

    return {
        "flagged": flagged,
        "checked": True,
        "summary": summary,
        "tip": tip,
    }
