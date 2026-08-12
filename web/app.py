import os
import sys
import asyncio
import logging
import secrets

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database.connection import get_pool, close_pool
from web.auth import get_current_user
from web.routes import auth as auth_routes
from web.routes import dashboard as dashboard_routes
from web.routes import problems as problems_routes
from web.routes import progress as progress_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recall_web")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database pool for Web Dashboard...")
    try:
        await get_pool()
        logger.info("Database pool initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database pool: {e}")
    yield
    logger.info("Closing database pool...")
    try:
        await close_pool()
    except Exception as e:
        logger.error(f"Error closing database pool: {e}")


app = FastAPI(title="Recall Web Dashboard", lifespan=lifespan)

# Add session middleware for simple session auth
SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("SESSION_SECRET_KEY") or secrets.token_hex(32)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Jinja2 Templates
templates = Jinja2Templates(directory="web/templates")
app.state.templates = templates

# Include Routers
app.include_router(auth_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(problems_routes.router)
app.include_router(progress_routes.router)


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
