from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from web.auth import require_login
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
async def api_get_history(request: Request, user=Depends(require_login)):
    user_id = str(user["user_id"])
    async with get_db_connection() as conn:
        attempts = await get_user_attempt_history(conn, user_id)
    return attempts
