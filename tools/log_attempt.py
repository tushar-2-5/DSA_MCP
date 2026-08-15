import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
from database.connection import get_db_connection
from database.queries import (
    get_user,
    insert_attempt,
    get_problem,
    get_mastery_row,
    upsert_mastery,
    insert_embedding,
    insert_mistake,
)
from memory.mastery import decayed_mastery, update_base_score
from embeddings.gemini_client import GeminiEmbedder
from core.logging import logger


async def log_attempt(
    user_id: str,
    problem_id: str,
    code: str,
    outcome: str,
    complexity_achieved: Optional[str] = None,
    time_taken_seconds: Optional[int] = None,
    mistake_summary: Optional[str] = None,
    mistake_category: Optional[str] = None,
) -> Dict[str, Any]:
    """Log a user's DSA problem solution attempt and update their topic mastery score.

    Use this tool when the user states that they have completed, submitted, or attempted
    a problem (e.g., 'I just finished this problem', 'I solved problem X', 'Here is my submission for Y').

    Args:
        user_id: The UUID string of the user.
        problem_id: The UUID string of the problem attempted.
        code: The source code submitted by the user.
        outcome: Outcome of the attempt. Must be 'pass', 'fail', or 'partial'.
        complexity_achieved: Optional time/space complexity achieved (e.g., 'O(N)').
        time_taken_seconds: Optional time taken to solve the problem in seconds.
        mistake_summary: Optional summary of mistake made (for 'fail' or 'partial' outcomes).
        mistake_category: Optional category of mistake (e.g. 'sliding_window_off_by_one', 'logic_error').

    Returns:
        Dict confirming attempt was logged and showing updated mastery score:
        {"attempt_id": str, "status": "logged", "mastery_score_after": float}
    """
    tool_name = "log_attempt"
    start = time.time()
    logger.info(f"Tool called: {tool_name} for user {user_id}")

    try:
        UUID(str(user_id))
        UUID(str(problem_id))
    except (ValueError, TypeError):
        raise ValueError("user_id and problem_id must be valid UUID strings.")

    async with get_db_connection() as conn:
        user = await get_user(conn, user_id)
        if not user:
            raise ValueError(
                f"No user found for user_id {user_id}. Call get_or_create_user first to register."
            )

        problem = await get_problem(conn, problem_id)
        if not problem or not problem.topic_id:
            raise ValueError(
                f"Problem '{problem_id}' not found or missing topic association."
            )

        embedder = GeminiEmbedder()
        try:
            code_vector = embedder.embed(code)
        except Exception as e:
            logger.warning(f"Gemini embedding failed: {e}. Saving without embedding.")
            code_vector = None

        async with conn.transaction():
            attempt = await insert_attempt(
                conn=conn,
                user_id=user_id,
                problem_id=problem_id,
                code_s3_key=None,
                outcome=outcome,
                complexity_achieved=complexity_achieved,
                time_taken_seconds=time_taken_seconds,
            )

            # Store code submission embedding if available
            if code_vector is not None:
                await insert_embedding(conn, "code_submission", attempt.id, code_vector)

            # If failed or partial attempt, log mistake & mistake embedding
            if outcome in ("fail", "partial"):
                summary = (
                    mistake_summary
                    or f"Incorrect or sub-optimal solution for '{problem.title}'"
                )
                category = mistake_category or "logic_error"
                mistake_row = await insert_mistake(
                    conn,
                    user_id=user_id,
                    attempt_id=attempt.id,
                    summary=summary,
                    category=category,
                )
                if code_vector is not None:
                    await insert_embedding(conn, "mistake", mistake_row["id"], code_vector)


            now = datetime.now(timezone.utc)
            mastery_row = await get_mastery_row(conn, user_id, problem.topic_id)

            if mastery_row and mastery_row.last_practiced_at:
                days_since = (
                    now - mastery_row.last_practiced_at
                ).total_seconds() / 86400.0
                prev_score = decayed_mastery(
                    float(mastery_row.mastery_score), max(0.0, days_since)
                )
            else:
                prev_score = 0.0

            is_optimal = bool(complexity_achieved and complexity_achieved.strip())
            new_score = update_base_score(
                prev_base_score=prev_score,
                outcome=outcome,
                complexity_optimal=is_optimal,
            )

            await upsert_mastery(
                conn=conn,
                user_id=user_id,
                topic_id=problem.topic_id,
                mastery_score=new_score,
            )

    duration = round((time.time() - start) * 1000, 2)
    logger.info("attempt_logged", user_id=str(user_id), problem_slug=getattr(problem, "title", str(problem_id)), outcome=outcome)

    return {
        "attempt_id": str(attempt.id),
        "status": "logged",
        "mastery_score_after": new_score,
    }

