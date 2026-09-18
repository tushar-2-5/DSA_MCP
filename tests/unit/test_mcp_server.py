import pytest
from server.main import mcp


def test_mcp_tools_registration():
    """Verify all expected tools are registered on FastMCP and get_or_create_user is FIRST."""
    tools = mcp._tool_manager.list_tools()
    tool_names = [tool.name for tool in tools]

    # Critical requirement: get_or_create_user MUST be the FIRST tool registered
    assert tool_names[0] == "get_or_create_user", (
        f"get_or_create_user must be the first registered tool, but found: {tool_names[0]}"
    )

    # say_hello debug tool must be removed from production
    assert "say_hello" not in tool_names, "say_hello debug tool must not be registered"

    expected_core_tools = {
        "get_or_create_user",
        "get_mastery_report",
        "log_attempt",
        "get_problem_context",
        "flag_recurring_mistake",
        "suggest_next_problem",
    }
    for expected in expected_core_tools:
        assert expected in tool_names, f"Missing core tool: {expected}"


def test_mcp_custom_health_route():
    """Verify that /health custom route is registered on FastMCP."""
    route_paths = [route.path for route in mcp._custom_starlette_routes]
    assert "/health" in route_paths

