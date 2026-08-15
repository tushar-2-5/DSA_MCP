import math
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, Body, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from web.auth import get_current_user, require_login
from web.rate_limit import limiter
from database.connection import get_db_connection
from database.queries import (
    get_all_problems_with_topics,
    get_problem,
    get_problem_by_title,
    get_problems_filtered,
    get_top_companies,
    get_user_by_email,
)
from psycopg.rows import dict_row
from tools.log_attempt import log_attempt
from tools.get_or_create_user import get_or_create_user

from core.logging import logger

router = APIRouter()


@router.get("/problems", response_class=HTMLResponse)
async def render_problems(request: Request, user=Depends(require_login)):
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="problems.html", context={"user": user})


@router.get("/api/problems")
@limiter.limit("60/minute")
async def api_get_problems(
    request: Request,
    user=Depends(require_login),
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "company_count_desc",
    page: int = 1,
    limit: int = 50,
):
    page = max(1, page)
    limit = max(1, min(limit, 200))

    async with get_db_connection() as conn:
        problems, total = await get_problems_filtered(
            conn,
            topic=topic,
            difficulty=difficulty,
            company=company,
            search=search,
            sort_by=sort_by,
            page=page,
            limit=limit,
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

    total_pages = math.ceil(total / limit) if total > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1

    filter_str = f"topic={topic},difficulty={difficulty},company={company},search={search},page={page},limit={limit}"
    logger.info("problems_fetched", filter=filter_str, count=len(results))

    return {
        "problems": results,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev,
    }


@router.get("/api/companies")
@limiter.limit("60/minute")
async def api_get_companies(request: Request, limit: int = 30):
    async with get_db_connection() as conn:
        companies = await get_top_companies(conn, limit=limit)
    return {"companies": companies}


@router.post("/api/log-attempt")
@limiter.limit("20/minute")
async def api_log_attempt(
    request: Request,
    user=Depends(require_login),
    payload: dict = Body(...)
):
    user_id = payload.get("user_id") or str(user["user_id"])
    email = payload.get("email")
    if not user_id and email:
        async with get_db_connection() as conn:
            user_obj = await get_user_by_email(conn, email)
            if user_obj:
                user_id = str(user_obj.id)
            else:
                created = await get_or_create_user(email=email)
                user_id = created["user_id"]

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    problem_id = payload.get("problem_id")
    problem_title = payload.get("problem_title")
    if not problem_id and problem_title:
        async with get_db_connection() as conn:
            prob = await get_problem_by_title(conn, problem_title.strip())
            if not prob:
                filtered, _ = await get_problems_filtered(conn, search=problem_title.strip(), limit=1)
                if filtered:
                    problem_id = str(filtered[0]["id"])
            else:
                problem_id = str(prob.id)

    if not problem_id:
        async with get_db_connection() as conn:
            filtered, _ = await get_problems_filtered(conn, limit=1)
            if filtered:
                problem_id = str(filtered[0]["id"])

    outcome = payload.get("outcome", "pass")
    code = payload.get("code") or "# Submitted via Web Dashboard / API"
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

