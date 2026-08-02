from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
from database.connection import get_db_connection
from database.queries import (
    insert_attempt,
    get_problem,
    get_mastery_row,
    upsert_mastery,
)


def compute_placeholder_mastery(current_score: float, outcome: str) -> float:
    """Compute updated mastery score using a placeholder delta rule.

    +0.10 for 'pass', -0.05 for 'fail', +0.02 for 'partial', clamped to [0.0, 1.0].
    """
    outcome_lower = outcome.lower()
    if outcome_lower == "pass":
        delta = 0.10
    elif outcome_lower == "fail":
        delta = -0.05
    elif outcome_lower == "partial":
        delta = 0.02
    else:
        delta = 0.0

    new_score = current_score + delta
    clamped_score = max(0.0, min(1.0, new_score))
    return round(clamped_score, 4)


async def log_attempt(
    user_id: str,
    problem_id: str,
    code: str,
    outcome: str,
    complexity_achieved: Optional[str] = None,
    time_taken_seconds: Optional[int] = None,
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

    Returns:
        Dict confirming attempt was logged and showing updated mastery score:
        {"attempt_id": str, "status": "logged", "mastery_score_after": float}
    """
    try:
        UUID(user_id)
        UUID(problem_id)
    except (ValueError, TypeError):
        raise ValueError("user_id and problem_id must be valid UUID strings.")

    async with get_db_connection() as conn:

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

            problem = await get_problem(conn, problem_id)
            if not problem or not problem.topic_id:
                raise ValueError(
                    f"Problem '{problem_id}' not found or missing topic association."
                )

            mastery_row = await get_mastery_row(conn, user_id, problem.topic_id)
            current_score = float(mastery_row.mastery_score) if mastery_row else 0.0
            new_score = compute_placeholder_mastery(current_score, outcome)

            now = datetime.now(timezone.utc)
            await upsert_mastery(
                conn=conn,
                user_id=user_id,
                topic_id=problem.topic_id,
                mastery_score=new_score,
                last_practiced_at=now,
            )

    return {
        "attempt_id": str(attempt.id),
        "status": "logged",
        "mastery_score_after": new_score,
    }
