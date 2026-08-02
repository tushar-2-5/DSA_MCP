from mcp.server.fastmcp import FastMCP
from tools.get_mastery_report import get_mastery_report
from tools.log_attempt import log_attempt
from tools.suggest_next_problem import suggest_next_problem

mcp = FastMCP("recall")


@mcp.tool()
def say_hello(name: str) -> str:
    """Say hello to someone by name. Use this only when the user explicitly 
    asks for a greeting or wants to test the Recall MCP server connection."""
    return f"Hello, {name}! Recall MCP server is working."


# Register additional tools
mcp.tool()(get_mastery_report)
mcp.tool()(log_attempt)
mcp.tool()(suggest_next_problem)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
