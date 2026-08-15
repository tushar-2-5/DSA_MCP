from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from web.rate_limit import limiter
from tools.get_mastery_report import get_mastery_report
from tools.suggest_next_problem import suggest_next_problem
from tools.study_plan import study_plan
from tools.flag_recurring_mistake import flag_recurring_mistake
from database.connection import get_db_connection
from database.queries import get_user_by_email, get_problems_by_company, get_user_streak

from core.logging import logger
from web.auth import get_current_user, require_login

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def render_dashboard(request: Request, user=Depends(require_login)):
    user_id = str(user.get("user_id") or user.get("id") or "guest")
    logger.info("dashboard_loaded", user_id=user_id)

    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user})


@router.get("/api/mastery")
@limiter.limit("30/minute")
async def api_get_mastery(request: Request, user=Depends(require_login)):
    target_user_id = str(user["user_id"])
    report = await get_mastery_report(user_id=target_user_id)
    topics = report.get("topics", [])
    for topic in topics:
        if topic.get("last_practiced_at") is None:
            topic["mastery_score"] = 0.0
    return {"topics": topics}


@router.get("/api/suggest")
@limiter.limit("20/minute")
async def api_suggest(request: Request, user=Depends(require_login), company: str = None):
    target_user_id = str(user["user_id"])
    if company:
        plan = await study_plan(user_id=target_user_id, target_company=company)
        return plan

    recommendation = await suggest_next_problem(user_id=target_user_id)
    return recommendation


@router.get("/api/target-company-problems")
@limiter.limit("10/minute")
async def api_target_company_problems(request: Request, user=Depends(require_login), company: str = "amazon"):
    async with get_db_connection() as conn:
        problems = await get_problems_by_company(conn, company_name=company, limit=5)
    return {"company": company, "problems": problems}


def _fmt_mastery(mastery: dict) -> str:
    topics = mastery.get("topics", [])
    if not topics:
        return "### 📊 Mastery Report\nNo data yet — log your first attempt!\n"
    lines = "\n".join(
        f"- **{t['slug'].replace('-',' ').title()}**: "
        f"{int(float(t.get('mastery_score', 0)) * 100)}%"
        for t in topics
    )
    return f"### 📊 Mastery Report\n{lines}\n"


def _fmt_suggestion(s: dict) -> str:
    rec = s.get("recommendation")
    if not rec:
        return "### 💡 Next Problem\nNo recommendations yet.\n"
    title = rec.get("title", "N/A")
    diff = rec.get("difficulty", "").title()
    topic = s.get("targeted_topic", "").replace("-", " ").title()
    reason = s.get("reason", "")
    return (
        f"### 💡 Next Problem\n"
        f"**{title}** ({diff}) — *{topic}*\n\n"
        f"_{reason}_\n"
    )


@router.post("/api/ask")
@limiter.limit("20/minute")
async def api_ask(request: Request, user=Depends(require_login)):
    body = await request.json()
    question = body.get("question", "").lower().strip()
    user_id = str(user["user_id"])
    
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
        result = f"## 🎯 {detected_company.title()} Interview Prep\n\n"
        result += _fmt_mastery(mastery) + "\n"
        result += _fmt_suggestion(suggestion) + "\n"
        result += f"> 💡 Ask *'Give me {detected_company} study plan'* for a full 7-day plan!"
    
    # CASE 3: What to practice / recommend / suggest
    elif any(word in question for word in 
        ["practice", "what should", "recommend", "suggest", 
         "next problem", "what to", "where to start",
         "which problem", "what problem"]):
        mastery = await get_mastery_report(user_id=user_id)
        suggestion = await suggest_next_problem(user_id=user_id)
        result = _fmt_mastery(mastery) + "\n" + _fmt_suggestion(suggestion)
    
    # CASE 4: Mastery / progress / score check
    elif any(word in question for word in 
        ["mastery", "progress", "score", "how am i", 
         "weak", "strong", "doing", "performance", "status"]):
        mastery = await get_mastery_report(user_id=user_id)
        result = _fmt_mastery(mastery)
    
    # CASE 5: Study plan without company
    elif any(word in question for word in 
        ["study plan", "7 day", "week plan", "weekly plan", "schedule"]):
        result = await study_plan(user_id=user_id)
    
    # CASE 6: Mistakes / errors / bugs
    elif any(word in question for word in 
        ["mistake", "error", "bug", "recurring", "flag", 
         "pattern", "keep making", "always fail"]):
        mistakes_data = await flag_recurring_mistake(
            user_id=user_id,
            code_in_progress="# Analyze my recurring mistake patterns"
        )
        flagged = mistakes_data.get("flagged", [])
        summary = mistakes_data.get("summary", "")
        tip = mistakes_data.get("tip", "")

        if not flagged:
            result = f"### ⚠️ Recurring Mistakes\n✅ No recurring mistakes detected. Clean code!"
        else:
            lines = "\n".join([
                f"- **{m['summary']}** ({m['category']}) — "
                f"seen {m['occurrences']} time(s)"
                for m in flagged
            ])
            result = f"### ⚠️ Recurring Mistakes\n{lines}\n"
            if tip:
                result += f"\n💡 {tip}"
    
    # CASE 7: Default — always show mastery + recommendation
    else:
        mastery = await get_mastery_report(user_id=user_id)
        suggestion = await suggest_next_problem(user_id=user_id)
        result = _fmt_mastery(mastery) + "\n" + _fmt_suggestion(suggestion)
    
    if isinstance(result, dict):
        import json
        result = json.dumps(result, indent=2, default=str)

    return {"answer": result}


@router.get("/api/streak")
@limiter.limit("60/minute")
async def api_streak(request: Request, user=Depends(require_login)):
    async with get_db_connection() as conn:
        streak = await get_user_streak(conn, str(user["user_id"]))
        return streak



