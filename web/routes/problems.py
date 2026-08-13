from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, Body
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from web.auth import get_current_user
from database.connection import get_db_connection
from database.queries import (
    get_all_problems_with_topics,
    get_problem,
    get_problems_filtered,
    get_top_companies,
)
from psycopg.rows import dict_row
from tools.log_attempt import log_attempt

router = APIRouter()


@router.get("/problems", response_class=HTMLResponse)
async def render_problems(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/?action=login", status_code=302)

    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="problems.html", context={"user": user})


@router.get("/api/problems")
async def api_get_problems(
    request: Request,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
):
    async with get_db_connection() as conn:
        problems = await get_problems_filtered(
            conn, topic=topic, difficulty=difficulty, company=company, search=search
        )

    results = []
    for p in problems:
        tags = p.get("company_tags") or []
        results.append({
            "id": str(p["id"]),
            "title": p["title"],
            "difficulty": p.get("difficulty", "medium"),
            "topic_slug": p.get("topic_slug", ""),
            "statement": p.get("statement", ""),
            "url": p.get("url") or f"https://leetcode.com/problemset/all/?search={p['title'].replace(' ', '%20')}",
            "study_priority": p.get("study_priority", "medium"),
            "company_tags": tags,
            "company_count": p.get("company_count", len(tags)),
            "acceptance_rate": p.get("acceptance_rate", 0.0),
            "leetcode_id": p.get("leetcode_id", 0),
        })

    return {"problems": results, "total": len(results)}


@router.get("/api/companies")
async def api_get_companies(request: Request, limit: int = 30):
    async with get_db_connection() as conn:
        companies = await get_top_companies(conn, limit=limit)
    return {"companies": companies}


@router.post("/api/log-attempt")
async def api_log_attempt(
    request: Request,
    payload: dict = Body(...)
):
    user = await get_current_user(request)
    user_id = payload.get("user_id") or (user["user_id"] if user else None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    problem_id = payload.get("problem_id")
    outcome = payload.get("outcome", "pass")
    code = payload.get("code") or "# Submitted via Web Dashboard"
    complexity_achieved = payload.get("complexity_achieved")
    time_taken_seconds = payload.get("time_taken_seconds")
    if time_taken_seconds is None and payload.get("time_taken_minutes") is not None:
        try:
            time_taken_seconds = int(payload["time_taken_minutes"]) * 60
        except (ValueError, TypeError):
            time_taken_seconds = None

    mistake_summary = payload.get("mistake_summary")
    mistake_category = payload.get("mistake_category")

    if not problem_id:
        raise HTTPException(status_code=400, detail="problem_id is required")

    result = await log_attempt(
        user_id=user_id,
        problem_id=problem_id,
        code=code,
        outcome=outcome,
        complexity_achieved=complexity_achieved,
        time_taken_seconds=time_taken_seconds,
        mistake_summary=mistake_summary,
        mistake_category=mistake_category,
    )

    async with get_db_connection() as conn:
        prob = await get_problem(conn, problem_id)
        if prob and prob.topic_id:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT slug FROM topics WHERE id = %s", (str(prob.topic_id),))
                row = await cur.fetchone()
                if row:
                    result["topic"] = row["slug"]

    return result
