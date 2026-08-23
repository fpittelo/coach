"""Tests for Coach MCP FastMCP Server registration and tool schemas."""

from coach_mcp.server import mcp


def test_mcp_server_initialization():
    """Verify FastMCP server instance and attributes."""
    assert mcp.name == "coach_mcp"


def test_tools_registered():
    """Verify all core endurance tools are registered on the FastMCP server."""
    # FastMCP holds registered tools
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]

    expected_tools = [
        "intervals_get_athlete_profile",
        "intervals_get_sport_settings",
        "intervals_list_activities",
        "intervals_get_activity",
        "intervals_get_activity_streams",
        "intervals_get_activity_intervals",
        "intervals_create_activity",
        "intervals_update_activity",
        "intervals_delete_activity",
        "intervals_get_wellness",
        "intervals_record_wellness",
        "intervals_get_fitness_summary",
        "intervals_list_events",
        "intervals_get_event",
        "intervals_create_event",
        "intervals_update_event",
        "intervals_delete_event",
        "intervals_list_folders",
        "intervals_list_workouts",
    ]

    for expected in expected_tools:
        assert expected in tool_names, f"Expected tool '{expected}' not found in registered tools"
