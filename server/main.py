import argparse
import os
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from tools.get_mastery_report import get_mastery_report
from tools.log_attempt import log_attempt
from tools.suggest_next_problem import suggest_next_problem
from tools.get_or_create_user import get_or_create_user
from tools.get_problem_context import get_problem_context
from tools.flag_recurring_mistake import flag_recurring_mistake

host = os.environ.get("HOST", "0.0.0.0")
port = int(os.environ.get("PORT", 8000))

mcp = FastMCP("recall", host=host, port=port)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for Railway and load balancers."""
    return JSONResponse({
        "status": "ok",
        "service": "recall-mcp-server",
        "transport": mcp.settings.streamable_http_path
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


def main():
    parser = argparse.ArgumentParser(description="Recall MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.environ.get("MCP_TRANSPORT", "streamable-http"),
        help="Transport protocol (stdio, sse, streamable-http)"
    )
    args = parser.parse_args()

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()

