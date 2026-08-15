import os
import sys
import asyncio
import logging

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web.auth import get_current_user
from web.rate_limit import limiter, custom_rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from web.routes import auth as auth_routes
from web.routes import dashboard as dashboard_routes
from web.routes import problems as problems_routes
from web.routes import progress as progress_routes
from web.routes import history as history_routes
from web.routes import topics as topics_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recall_web")


app = FastAPI(title="Recall Web Dashboard")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Jinja2 Templates
templates = Jinja2Templates(directory="web/templates")
app.state.templates = templates

# Include Routers
app.include_router(auth_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(problems_routes.router)
app.include_router(progress_routes.router)
app.include_router(history_routes.router)
app.include_router(topics_routes.router)


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="landing.html", context={"user": user})


port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=False)
