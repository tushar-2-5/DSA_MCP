from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from web.auth import get_current_user
from tools.get_mastery_report import get_mastery_report
from tools.suggest_next_problem import suggest_next_problem

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def render_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/?action=login", status_code=302)

    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user})


@router.get("/api/mastery")
async def api_get_mastery(request: Request, user_id: str = None):
    user = await get_current_user(request)
    target_user_id = user_id or (user["user_id"] if user else None)
    if not target_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    report = await get_mastery_report(user_id=target_user_id)
    topics = report.get("topics", [])
    for topic in topics:
        if topic.get("last_practiced_at") is None:
            topic["mastery_score"] = 0.0
    return {"topics": topics}


@router.get("/api/suggest")
async def api_suggest(request: Request, user_id: str = None):
    user = await get_current_user(request)
    target_user_id = user_id or (user["user_id"] if user else None)
    if not target_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    recommendation = await suggest_next_problem(user_id=target_user_id)
    return recommendation
