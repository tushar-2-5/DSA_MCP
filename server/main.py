import sys
import argparse
import logging
import os
import secrets
from contextlib import asynccontextmanager

# In stdio mode, redirect ALL logging to stderr
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from core.logging import setup_logging
from database.connection import close_pool, get_pool
from tools.flag_recurring_mistake import flag_recurring_mistake
from tools.get_mastery_report import get_mastery_report
from tools.get_or_create_user import get_or_create_user
from tools.get_problem_context import get_problem_context
from tools.log_attempt import log_attempt
from tools.study_plan import study_plan
from tools.suggest_next_problem import suggest_next_problem
from web.app import app as web_app
from web.middleware.logging_middleware import RequestLoggingMiddleware

setup_logging()
logger = logging.getLogger("recall_server")


host = os.environ.get("HOST", "0.0.0.0")
port = int(os.environ.get("PORT", 8000))

mcp = FastMCP("recall", host=host, port=port)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for Railway and load balancers."""
    return JSONResponse({
        "status": "ok",
        "service": "recall-mcp-server",
        "transport": mcp.settings.streamable_http_path,
    })


@mcp.tool()
def say_hello(name: str) -> str:
    """Say hello to someone by name. Use this only when the user explicitly 
    asks for a greeting or wants to test the Recall MCP server connection."""
    return f"Hello, {name}! Recall MCP server is working."


# Register additional tools
mcp.tool()(get_mastery_report)
mcp.tool()(log_attempt)
mcp.tool()(suggest_next_problem)
mcp.tool()(get_or_create_user)
mcp.tool()(get_problem_context)
mcp.tool()(flag_recurring_mistake)
mcp.tool()(study_plan)


# Build combined lifespan managing both database connection pool and FastMCP session manager
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    logger.info("Initializing database pool for Recall Server & Web Dashboard...")
    try:
        await get_pool()
        logger.info("Database pool initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database pool: {e}")

    async with mcp.session_manager.run():
        yield

    logger.info("Closing database pool...")
    try:
        await close_pool()
    except Exception as e:
        logger.error(f"Error closing database pool: {e}")


# Combined FastAPI Application
app = FastAPI(title="Recall Server & Web Dashboard", lifespan=combined_lifespan)

# Configure SessionMiddleware
SECRET_KEY = (
    os.environ.get("SECRET_KEY")
    or os.environ.get("SESSION_SECRET_KEY")
    or secrets.token_hex(32)
)
if not os.environ.get("SECRET_KEY") and not os.environ.get("SESSION_SECRET_KEY"):
    logger.warning("SECRET_KEY not set — using ephemeral key. All sessions will reset on restart.")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(RequestLoggingMiddleware)


# Inherit state (Jinja2 templates) from web_app
app.state.templates = web_app.state.templates

# Mount/Include MCP Streamable-HTTP routes (/mcp, /health)
mcp_starlette_app = mcp.streamable_http_app()
app.routes.extend(mcp_starlette_app.routes)

# Mount/Include Web Dashboard routes (/, /dashboard, /problems, /progress, /api/*)
app.routes.extend(web_app.routes)


def main():
    parser = argparse.ArgumentParser(description="Recall Server & Web Dashboard")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (stdio, sse, streamable-http)",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn

        uvicorn.run("server.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()


