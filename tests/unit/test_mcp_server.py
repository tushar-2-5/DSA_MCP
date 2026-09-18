import pytest
from server.main import mcp


def test_mcp_tools_registration():
    """Verify all expected tools are registered on FastMCP, get_or_create_user is FIRST,
    say_hello is absent, and all descriptions are under 50 characters.
    """
    tools = mcp._tool_manager.list_tools()
    tool_names = [tool.name for tool in tools]

    # Critical requirement: get_or_create_user MUST be the FIRST tool registered
    assert tool_names[0] == "get_or_create_user", (
        f"get_or_create_user must be the first registered tool, but found: {tool_names[0]}"
    )

    # say_hello debug tool must be removed from production
    assert "say_hello" not in tool_names, "say_hello debug tool must not be registered"

    expected_tool_descriptions = {
        "get_or_create_user": "Register or fetch a user by email",
        "register_user": "Register or fetch a user by email",
        "get_mastery_report": "Get DSA topic mastery scores",
        "log_attempt": "Log a problem attempt",
        "get_problem_context": "Get similar past attempts",
        "flag_recurring_mistake": "Check code for recurring bugs",
        "suggest_next_problem": "Suggest next DSA problem",
        "study_plan": "Generate a personalized study plan",
    }

    for tool in tools:
        assert tool.name in expected_tool_descriptions, f"Unexpected tool registered: {tool.name}"
        assert len(tool.description) < 50, (
            f"Tool '{tool.name}' description exceeds 50 chars ({len(tool.description)}): '{tool.description}'"
        )
        assert tool.description == expected_tool_descriptions[tool.name]


def test_mcp_custom_health_route():
    """Verify that /health custom route is registered on FastMCP."""
    route_paths = [route.path for route in mcp._custom_starlette_routes]
    assert "/health" in route_paths
