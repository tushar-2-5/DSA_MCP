from typing import Dict, Any, Optional
from uuid import UUID
from database.connection import get_db_connection
from database.queries import get_user, find_similar_past_attempts
from embeddings.gemini_client import GeminiEmbedder
from tools.get_or_create_user import verify_user_token


async def get_problem_context(
    user_id: str, problem_statement: str, token: Optional[str] = None
) -> Dict[str, Any]:
    """Find structurally similar past attempts from the user's history for a problem statement.

    Always pass the token received from get_or_create_user. Never use a user_id
    that wasn't returned by get_or_create_user in this session.

    Args:
        user_id: The UUID string of the registered user.
        problem_statement: The text of the problem statement to find similar past attempts for.
        token: JWT token returned by get_or_create_user.
               Pass this to verify you can only access your own data.

    Returns:
        Dict matching contract:
        - If matches exist: {"matches": [{"attempt_id": str, "outcome": str, "complexity_achieved": str|None, "mistake_summary": str|None, "distance": float}]}
        - If no matches: {"matches": [], "note": "No similar past attempts found. Keep practicing to build your history!"}
    """
    if token:
        verify_user_token(token, user_id)

    try:
        UUID(user_id)
    except (ValueError, TypeError):
        raise ValueError("user_id must be a valid UUID string.")

    if not problem_statement or not isinstance(problem_statement, str) or not problem_statement.strip():
        raise ValueError("problem_statement must be a non-empty string.")

    async with get_db_connection() as conn:
        user = await get_user(conn, user_id)
        if not user:
            raise ValueError(
                f"No user found for user_id {user_id}. Call get_or_create_user first to register."
            )

        embedder = GeminiEmbedder()
        query_vector = embedder.embed(problem_statement)

        matches_raw = await find_similar_past_attempts(
            conn, user_id=user_id, query_vector=query_vector, limit=5
        )

    matches = [
        {
            "attempt_id": m["attempt_id"],
            "outcome": m["outcome"],
            "complexity_achieved": m["complexity_achieved"],
            "code_snippet": m.get("code_blob", "")[:500] if m.get("code_blob") else None,
            "mistake_summary": m["mistake_summary"],
            "distance": round(float(m["distance"]), 4),
        }
        for m in matches_raw
    ]

    total = len(matches_raw)
    solved = sum(1 for m in matches_raw if m.get("outcome") == "pass")
    failed = sum(1 for m in matches_raw if m.get("outcome") in ("fail", "partial"))
    last_outcome = matches_raw[0]["outcome"] if matches_raw else None
    last_mistake = matches_raw[0]["mistake_summary"] if matches_raw else None

    if total == 0:
        warning = None
    elif failed > 0:
        if last_mistake:
            warning = (
                f"⚠️ You've attempted this {failed} times before and failed. "
                f"Last mistake: {last_mistake}"
            )
        else:
            warning = f"⚠️ You've attempted this {failed} times before and failed."
    elif solved == total:
        warning = f"✅ Great news! You've solved all {total} similar problems before. You got this!"
    else:
        warning = None

    past_attempts = {
        "total": total,
        "solved": solved,
        "failed": failed,
        "last_outcome": last_outcome,
        "last_mistake": last_mistake,
    }

    res = {
        "problem": {
            "statement": problem_statement,
        },
        "matches": matches,
        "past_attempts": past_attempts,
        "warning": warning,
    }

    if not matches_raw:
        res["note"] = "No similar past attempts found. Keep practicing to build your history!"

    return res
