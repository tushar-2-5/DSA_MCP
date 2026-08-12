from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from web.auth import get_current_user
from database.connection import get_db_connection
from database.queries import (
    get_recent_attempts,
    get_problem,
    get_user_mastery_report_rows,
)
from tools.get_mastery_report import get_mastery_report
from psycopg.rows import dict_row

router = APIRouter()


@router.get("/progress", response_class=HTMLResponse)
async def render_progress(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/?action=login", status_code=302)

    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="progress.html", context={"user": user})


@router.get("/api/progress-data")
async def api_get_progress_data(request: Request, user_id: Optional[str] = None):
    user = await get_current_user(request)
    target_user_id = user_id or (user["user_id"] if user else None)
    if not target_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with get_db_connection() as conn:
        # Fetch mastery trends
        mastery_report = await get_mastery_report(user_id=target_user_id)
        mastery_trends = mastery_report.get("topics", [])
        for topic in mastery_trends:
            if topic.get("last_practiced_at") is None:
                topic["mastery_score"] = 0.0

        # Fetch recent attempts
        raw_attempts = await get_recent_attempts(conn, target_user_id, limit=20)
        recent_attempts = []
        for att in raw_attempts:
            problem = await get_problem(conn, att.problem_id)
            title = problem.title if problem else "Unknown Problem"
            recent_attempts.append({
                "id": str(att.id),
                "problem_id": str(att.problem_id),
                "problem_title": title,
                "outcome": att.outcome,
                "complexity_achieved": att.complexity_achieved,
                "time_taken_seconds": att.time_taken_seconds,
                "created_at": att.created_at.isoformat() if att.created_at else None,
            })

        # Fetch top mistakes
        top_mistakes = []
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT category, COUNT(*) as count
                FROM mistakes
                WHERE user_id = %s
                GROUP BY category
                ORDER BY count DESC
                LIMIT 5
                """,
                (str(target_user_id),)
            )
            rows = await cur.fetchall()
            for r in rows:
                top_mistakes.append({
                    "category": r["category"],
                    "count": r["count"]
                })

    return {
        "recent_attempts": recent_attempts,
        "mastery_trends": mastery_trends,
        "top_mistakes": top_mistakes,
    }
