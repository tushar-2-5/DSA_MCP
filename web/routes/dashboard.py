from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from web.auth import get_current_user
from web.rate_limit import limiter
from tools.get_mastery_report import get_mastery_report
from tools.suggest_next_problem import suggest_next_problem
from database.connection import get_db_connection
from database.queries import get_user_by_email, get_problems_by_company

from core.logging import logger

from web.auth import get_current_user, require_login

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def render_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user_id = str(user.get("user_id") or user.get("id") or "guest")
    logger.info("dashboard_loaded", user_id=user_id)

    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user})


@router.get("/api/mastery")
@limiter.limit("30/minute")
async def api_get_mastery(request: Request, user_id: str = None, email: str = None):
    target_user_id = user_id
    if not target_user_id and email:
        async with get_db_connection() as conn:
            user_obj = await get_user_by_email(conn, email)
            if user_obj:
                target_user_id = str(user_obj.id)
            else:
                from tools.get_or_create_user import get_or_create_user
                created = await get_or_create_user(email=email)
                target_user_id = created["user_id"]

    if not target_user_id:
        user = await get_current_user(request)
        target_user_id = user["user_id"] if user else None

    if not target_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    report = await get_mastery_report(user_id=target_user_id)
    topics = report.get("topics", [])
    for topic in topics:
        if topic.get("last_practiced_at") is None:
            topic["mastery_score"] = 0.0
    return {"topics": topics}


@router.get("/api/suggest")
@limiter.limit("20/minute")
async def api_suggest(request: Request, user_id: str = None, email: str = None, company: str = None):
    target_user_id = user_id
    if not target_user_id and email:
        async with get_db_connection() as conn:
            user_obj = await get_user_by_email(conn, email)
            if user_obj:
                target_user_id = str(user_obj.id)
            else:
                from tools.get_or_create_user import get_or_create_user
                created = await get_or_create_user(email=email)
                target_user_id = created["user_id"]

    if not target_user_id:
        user = await get_current_user(request)
        target_user_id = user["user_id"] if user else None

    if not target_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if company:
        from tools.study_plan import study_plan
        plan = await study_plan(user_id=target_user_id, target_company=company)
        return plan

    recommendation = await suggest_next_problem(user_id=target_user_id)
    return recommendation


@router.get("/api/target-company-problems")
async def api_target_company_problems(request: Request, company: str = "amazon"):
    async with get_db_connection() as conn:
        problems = await get_problems_by_company(conn, company_name=company, limit=5)
    return {"company": company, "problems": problems}


@router.post("/api/ask")
async def api_ask(request: Request, user=Depends(require_login)):
    body = await request.json()
    question = body.get("question", "").lower().strip()
    user_id = str(user["user_id"])
    
    # First ALWAYS get mastery report to know weak topics
    from tools.get_mastery_report import get_mastery_report
    from tools.suggest_next_problem import suggest_next_problem
    from tools.study_plan import study_plan
    from tools.flag_recurring_mistake import flag_recurring_mistake
    
    # Detect company name in question
    companies = ["amazon", "google", "microsoft", "meta", "apple", 
                 "uber", "netflix", "adobe", "flipkart", "walmart",
                 "goldman", "jpmorgan", "morgan stanley", "oracle"]
    detected_company = None
    for c in companies:
        if c in question:
            detected_company = c
            break
    
    # CASE 1: Study plan with company
    if detected_company and any(word in question for word in 
        ["plan", "prepare", "study", "interview", "crack", "get into"]):
        result = await study_plan(user_id=user_id, target_company=detected_company)
    
    # CASE 2: Just company mentioned (e.g. "amazon problems", "for google")
    elif detected_company:
        mastery = await get_mastery_report(user_id=user_id)
        suggestion = await suggest_next_problem(user_id=user_id)
        result = f"🎯 Preparing for {detected_company.title()} interviews:\n\n"
        result += f"📊 Your Current Mastery:\n{mastery}\n\n"
        result += f"💡 Recommended Next Problem:\n{suggestion}\n\n"
        result += f"💡 Tip: Use 'Give me {detected_company} study plan' for a full 7-day plan!"
    
    # CASE 3: What to practice / recommend / suggest
    elif any(word in question for word in 
        ["practice", "what should", "recommend", "suggest", 
         "next problem", "what to", "where to start",
         "which problem", "what problem"]):
        mastery = await get_mastery_report(user_id=user_id)
        suggestion = await suggest_next_problem(user_id=user_id)
        result = f"📊 Your Mastery Report:\n{mastery}\n\n"
        result += f"💡 Recommended Next Problem:\n{suggestion}"
    
    # CASE 4: Mastery / progress / score check
    elif any(word in question for word in 
        ["mastery", "progress", "score", "how am i", 
         "weak", "strong", "doing", "performance", "status"]):
        result = await get_mastery_report(user_id=user_id)
    
    # CASE 5: Study plan without company
    elif any(word in question for word in 
        ["study plan", "7 day", "week plan", "weekly plan", "schedule"]):
        result = await study_plan(user_id=user_id)
    
    # CASE 6: Mistakes / errors / bugs
    elif any(word in question for word in 
        ["mistake", "error", "bug", "recurring", "flag", 
         "pattern", "keep making", "always fail"]):
        result = await flag_recurring_mistake(
            user_id=user_id,
            code_in_progress="# Analyze my recurring mistake patterns"
        )
    
    # CASE 7: Default — always show mastery + recommendation
    else:
        mastery = await get_mastery_report(user_id=user_id)
        suggestion = await suggest_next_problem(user_id=user_id)
        result = f"📊 Your Current Mastery:\n{mastery}\n\n"
        result += f"💡 My Recommendation:\n{suggestion}"
    
    return {"answer": result}


