from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from web.auth import require_login
from web.rate_limit import limiter
from database.connection import get_db_connection
from database.queries import get_topic_detail

router = APIRouter()


@router.get("/topic/{topic_slug}", response_class=HTMLResponse)
async def render_topic_detail(
    request: Request, topic_slug: str, user=Depends(require_login)
):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="topic_detail.html",
        context={"user": user, "topic_slug": topic_slug},
    )


@router.get("/api/topic/{topic_slug}")
@limiter.limit("30/minute")
async def api_topic_detail(
    request: Request, topic_slug: str, user=Depends(require_login)
):
    user_id = str(user["user_id"])
    async with get_db_connection() as conn:
        data = await get_topic_detail(conn, user_id, topic_slug)
    return data
