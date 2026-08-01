from mcp.server.fastmcp import FastMCP

mcp = FastMCP("recall")


@mcp.tool()
def say_hello(name: str) -> str:
    """Say hello to someone by name. Use this only when the user explicitly 
    asks for a greeting or wants to test the Recall MCP server connection."""
    return f"Hello, {name}! Recall MCP server is working."


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

