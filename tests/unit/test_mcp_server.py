import pytest
from server.main import mcp


def test_mcp_tools_registration():
    """Verify all 7 expected tools are registered on the FastMCP server instance."""
    tool_names = [tool.name for tool in mcp._tool_manager.list_tools()]
    expected_tools = {
        "say_hello",
        "get_mastery_report",
        "log_attempt",
        "suggest_next_problem",
        "get_or_create_user",
        "get_problem_context",
        "flag_recurring_mistake",
    }
    for expected in expected_tools:
        assert expected in tool_names, f"Missing tool: {expected}"


def test_mcp_custom_health_route():
    """Verify that /health custom route is registered on FastMCP."""
    route_paths = [route.path for route in mcp._custom_starlette_routes]
    assert "/health" in route_paths
