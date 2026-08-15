from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from psycopg.rows import dict_row
from web.auth import require_login
from web.rate_limit import limiter
from database.connection import get_db_connection
from database.queries import get_user_attempt_history

router = APIRouter()


@router.get("/history", response_class=HTMLResponse)
async def render_history(request: Request, user=Depends(require_login)):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="history.html", context={"user": user}
    )


@router.get("/api/history")
@limiter.limit("30/minute")
async def api_get_history(request: Request, user=Depends(require_login)):
    user_id = str(user["user_id"])
    async with get_db_connection() as conn:
        attempts = await get_user_attempt_history(conn, user_id)
    return attempts


@router.get("/api/problem-history/{problem_id}")
@limiter.limit("60/minute")
async def api_problem_history(
    request: Request, problem_id: str, user=Depends(require_login)
):
    user_id = str(user["user_id"])
    from datetime import datetime, timezone

    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # Get all attempts for this problem
            await cur.execute(
                """
                SELECT 
                    a.id,
                    a.outcome,
                    a.created_at,
                    a.time_taken_seconds,
                    a.complexity_achieved,
                    m.summary as mistake_summary,
                    m.category as mistake_category
                FROM attempts a
                LEFT JOIN mistakes m ON m.attempt_id = a.id
                WHERE a.user_id = %s AND a.problem_id = %s
                ORDER BY a.created_at DESC
                LIMIT 10
            """,
                (user_id, problem_id),
            )
            rows = await cur.fetchall()

            # Get problem topic for pattern analysis
            await cur.execute(
                """
                SELECT t.slug FROM problems p
                LEFT JOIN topics t ON t.id = p.topic_id
                WHERE p.id = %s
            """,
                (problem_id,),
            )
            prob_row = await cur.fetchone()
            topic_slug = prob_row["slug"] if prob_row else None

            # Get recent failures on same topic (pattern detection)
            topic_failure_count = 0
            topic_common_mistake = None
            if topic_slug:
                await cur.execute(
                    """
                    SELECT a.outcome, m.summary, m.category
                    FROM attempts a
                    JOIN problems p ON p.id = a.problem_id
                    LEFT JOIN mistakes m ON m.attempt_id = a.id
                    WHERE a.user_id = %s 
                    AND p.topic_id = (
                        SELECT topic_id FROM problems WHERE id = %s
                    )
                    AND a.outcome IN ('fail', 'failed', 'partial')
                    AND a.created_at > NOW() - INTERVAL '7 days'
                    ORDER BY a.created_at DESC
                    LIMIT 10
                """,
                    (user_id, problem_id),
                )
                topic_failures = await cur.fetchall()
                topic_failure_count = len(topic_failures)
                if topic_failures:
                    from collections import Counter

                    cats = [
                        r["category"]
                        for r in topic_failures
                        if r.get("category")
                    ]
                    if cats:
                        topic_common_mistake = (
                            Counter(cats).most_common(1)[0][0]
                        )

    total = len(rows)
    solved = sum(1 for r in rows if r["outcome"] in ("pass", "solved"))
    failed = total - solved
    hint_used = sum(1 for r in rows if r["outcome"] in ("hint", "partial"))

    # Average time taken
    times = [
        r["time_taken_seconds"]
        for r in rows
        if r.get("time_taken_seconds")
    ]
    avg_time_mins = round(sum(times) / len(times) / 60) if times else None

    # Last attempt details
    last = rows[0] if rows else None
    last_outcome = last["outcome"] if last else None
    last_mistake = next(
        (r["mistake_summary"] for r in rows if r.get("mistake_summary")),
        None,
    )
    last_mistake_category = next(
        (r["mistake_category"] for r in rows if r.get("mistake_category")),
        None,
    )

    # Days since last attempt
    days_since = None
    if last and last.get("created_at"):
        last_dt = last["created_at"]
        if isinstance(last_dt, str):
            last_dt = datetime.fromisoformat(last_dt)
        if hasattr(last_dt, "tzinfo") and last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        days_since = (datetime.now(timezone.utc) - last_dt).days

    # Spaced repetition nudge
    review_nudge = None
    if solved > 0 and days_since is not None and days_since >= 7:
        review_nudge = (
            f"🔁 You solved this {days_since} days ago — time to review!"
        )

    # Badge and warning
    if total == 0:
        badge = None
        warning = None
        tip = None
    elif solved > 0 and failed == 0:
        badge = "solved"
        warning = f"✅ Solved {solved} time(s)"
        tip = review_nudge
    elif solved > 0 and failed > 0:
        badge = "partial"
        warning = f"⚡ Solved once but also failed {failed} time(s)"
        tip = f"Last mistake: {last_mistake}" if last_mistake else review_nudge
    else:
        badge = "failed"
        warning = f"⚠️ Failed {failed} time(s) — you can do this!"
        if last_mistake:
            tip = f"Last mistake: {last_mistake}"
        elif last_mistake_category:
            tip = f"Pattern: {last_mistake_category}"
        else:
            tip = "Try a different approach this time!"

    # Topic pattern warning
    pattern_warning = None
    if topic_failure_count >= 3:
        pattern_warning = (
            f"🔁 You've failed {topic_failure_count} "
            f"{topic_slug.replace('-', ' ').title()} problems "
            f"this week"
        )
        if topic_common_mistake:
            pattern_warning += f" — Common mistake: {topic_common_mistake}"

    return {
        "total_attempts": total,
        "solved": solved,
        "failed": failed,
        "hint_used": hint_used,
        "badge": badge,
        "warning": warning,
        "tip": tip,
        "avg_time_mins": avg_time_mins,
        "days_since_last": days_since,
        "review_nudge": review_nudge,
        "pattern_warning": pattern_warning,
        "last_mistake": last_mistake,
    }
