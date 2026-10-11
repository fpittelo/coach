"""Comprehensive tests for Coach MCP MCPServer handlers and formatters."""

import json
import re
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from coach_mcp.client import (
    IntervalsAPIError,
    IntervalsAuthError,
    IntervalsNotFoundError,
)
from coach_mcp.formatters import (
    format_activities_list,
    format_activity_detail,
    format_activity_streams,
    format_events_list,
    format_fitness_summary,
    format_folders,
    format_icu_wellness,
    format_power_curve,
    format_power_model,
    format_profile,
    format_readiness_dashboard,
    format_sport_settings,
    format_wellness_list,
    format_workouts,
    to_json_str,
)
from coach_mcp.models import (
    CreateActivityInput,
    CreateEventInput,
    DeleteActivityInput,
    DeleteEventInput,
    GetActivityInput,
    GetActivityIntervalsInput,
    GetActivityStreamsInput,
    GetAthleteProfileInput,
    GetEventInput,
    GetFitnessSummaryInput,
    GetPowerCurveInput,
    GetPowerModelInput,
    GetReadinessDashboardInput,
    GetSportSettingsInput,
    GetWellnessInput,
    IcuAddSessionCommentInput,
    IcuBatchCreateEventsInput,
    IcuEventDraft,
    IcuGetWellnessInput,
    ListActivitiesInput,
    ListEventsInput,
    ListFoldersInput,
    ListWorkoutsInput,
    RecordWellnessBulkInput,
    RecordWellnessInput,
    ResponseFormat,
    UpdateActivityInput,
    UpdateEventInput,
    WellnessRecordItem,
    project_wellness_days,
)
from coach_mcp.server import (
    _build_batch_event_payload,
    _derive_batch_confirm_token,
    _get_client_from_ctx,
    icu_add_session_comment,
    icu_batch_create_events,
    icu_get_wellness,
    intervals_create_activity,
    intervals_create_event,
    intervals_delete_activity,
    intervals_delete_event,
    intervals_get_activity,
    intervals_get_activity_intervals,
    intervals_get_activity_streams,
    intervals_get_athlete_profile,
    intervals_get_event,
    intervals_get_fitness_summary,
    intervals_get_power_curve,
    intervals_get_power_model,
    intervals_get_readiness_dashboard,
    intervals_get_sport_settings,
    intervals_get_wellness,
    intervals_list_activities,
    intervals_list_events,
    intervals_list_folders,
    intervals_list_workouts,
    intervals_record_wellness,
    intervals_record_wellness_bulk,
    intervals_update_activity,
    intervals_update_event,
    mcp,
    server_lifespan,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ctx() -> Context:
    """Create a mock MCP Context with lifespan state."""
    ctx = MagicMock()
    ctx.request_context.lifespan_state = {}
    return ctx


@pytest.fixture
def mock_client():
    """Create a mock IntervalsClient."""
    client = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Server Registration Tests
# ---------------------------------------------------------------------------


def test_mcp_server_initialization():
    """Verify MCPServer instance and attributes."""
    assert isinstance(mcp, MCPServer)
    assert mcp.name == "Coach"


def test_tools_registered():
    """Verify all core endurance tools are registered on the MCPServer."""
    tools = mcp._tool_manager.list_tools()
    tool_names = [t.name for t in tools]

    expected_tools = [
        "intervals_get_athlete_profile",
        "intervals_get_sport_settings",
        "intervals_list_activities",
        "intervals_get_activity",
        "intervals_get_activity_streams",
        "intervals_get_activity_intervals",
        "intervals_get_power_curve",
        "intervals_get_power_model",
        "intervals_create_activity",
        "intervals_update_activity",
        "intervals_delete_activity",
        "intervals_get_wellness",
        "intervals_record_wellness",
        "intervals_record_wellness_bulk",
        "intervals_get_fitness_summary",
        "intervals_get_readiness_dashboard",
        "intervals_list_events",
        "intervals_get_event",
        "intervals_create_event",
        "intervals_update_event",
        "intervals_delete_event",
        "intervals_list_folders",
        "intervals_list_workouts",
        "icu_get_wellness",
        "icu_add_session_comment",
        "icu_batch_create_events",
    ]

    for expected in expected_tools:
        assert expected in tool_names, f"Expected tool '{expected}' not found in registered tools"

    # Verify strongly-typed annotations are attached to tools
    annotations_by_name = {t.name: t.annotations for t in tools}
    profile_annotations = annotations_by_name["intervals_get_athlete_profile"]
    create_annotations = annotations_by_name["intervals_create_activity"]
    delete_annotations = annotations_by_name["intervals_delete_activity"]
    assert isinstance(profile_annotations, ToolAnnotations)
    assert profile_annotations.read_only_hint is True
    assert create_annotations is not None
    assert create_annotations.read_only_hint is False
    assert create_annotations.idempotent_hint is False
    assert delete_annotations is not None
    assert delete_annotations.destructive_hint is True


# ---------------------------------------------------------------------------
# Context Client Retrieval Tests
# ---------------------------------------------------------------------------


def test_get_client_from_ctx_lifespan(mock_ctx, mock_client):
    """Test retrieving client from context lifespan state."""
    mock_ctx.request_context.lifespan_state["client"] = mock_client
    result = _get_client_from_ctx(mock_ctx)
    assert result is mock_client


def test_get_client_from_ctx_missing_state(mock_ctx):
    """Test creating new client when lifespan state is unavailable."""
    mock_ctx.request_context.lifespan_state = {}
    result = _get_client_from_ctx(mock_ctx)
    assert isinstance(result, type(mock_ctx)) is False
    from coach_mcp.client import IntervalsClient

    assert isinstance(result, IntervalsClient)


def test_get_client_from_ctx_no_request_context():
    """Test creating new client when request_context is missing."""
    ctx = MagicMock()
    ctx.request_context = None
    from coach_mcp.client import IntervalsClient

    result = _get_client_from_ctx(ctx)
    assert isinstance(result, IntervalsClient)


@pytest.mark.asyncio
async def test_server_lifespan_yields_client():
    """Test server lifespan yields a client and closes it on teardown."""
    from coach_mcp.client import IntervalsClient

    async with server_lifespan(mcp) as state:
        assert "client" in state
        assert isinstance(state["client"], IntervalsClient)


# ---------------------------------------------------------------------------
# Athlete Tool Handler Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervals_get_athlete_profile_markdown(mock_ctx, mock_client):
    """Test athlete profile tool returns markdown."""
    mock_client.get_athlete_profile = AsyncMock(
        return_value={"athlete": {"id": "0", "name": "Test Athlete", "weight": 70.0}}
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetAthleteProfileInput(response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_athlete_profile(params, mock_ctx)

    assert "Test Athlete" in result
    assert "# Athlete Profile" in result
    mock_client.get_athlete_profile.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_intervals_get_athlete_profile_json(mock_ctx, mock_client):
    """Test athlete profile tool returns JSON."""
    mock_client.get_athlete_profile = AsyncMock(
        return_value={"athlete": {"id": "0", "name": "Test Athlete"}}
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetAthleteProfileInput(response_format=ResponseFormat.JSON)
    result = await intervals_get_athlete_profile(params, mock_ctx)

    assert '"name": "Test Athlete"' in result
    mock_client.get_athlete_profile.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_intervals_get_athlete_profile_error(mock_ctx, mock_client):
    """Test athlete profile tool handles API errors."""
    mock_client.get_athlete_profile = AsyncMock(
        side_effect=IntervalsAuthError("Auth failed", status_code=401)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetAthleteProfileInput()
    result = await intervals_get_athlete_profile(params, mock_ctx)

    assert "Error fetching athlete profile" in result
    assert "Auth failed" in result


@pytest.mark.asyncio
async def test_intervals_get_sport_settings_markdown(mock_ctx, mock_client):
    """Test sport settings tool returns markdown."""
    mock_client.get_sport_settings = AsyncMock(
        return_value=[{"types": ["Ride"], "ftp": 300, "lthr": 170}]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetSportSettingsInput(response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_sport_settings(params, mock_ctx)

    assert "Athlete Sport Settings" in result
    assert "300" in result
    mock_client.get_sport_settings.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_intervals_get_sport_settings_json(mock_ctx, mock_client):
    """Test sport settings tool returns JSON."""
    mock_client.get_sport_settings = AsyncMock(return_value=[{"ftp": 300}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetSportSettingsInput(response_format=ResponseFormat.JSON)
    result = await intervals_get_sport_settings(params, mock_ctx)

    assert '"ftp": 300' in result


# ---------------------------------------------------------------------------
# Activity Tool Handler Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervals_list_activities_markdown(mock_ctx, mock_client):
    """Test list activities tool returns markdown."""
    mock_client.list_activities = AsyncMock(
        return_value=[
            {
                "id": "act1",
                "name": "Endurance Ride",
                "type": "Ride",
                "start_date_local": "2026-08-22T09:00:00",
                "moving_time": 7200,
                "icu_training_load": 110,
            }
        ]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListActivitiesInput(
        oldest="2026-08-01", newest="2026-08-22", response_format=ResponseFormat.MARKDOWN
    )
    result = await intervals_list_activities(params, mock_ctx)

    assert "Activities Summary" in result
    assert "Endurance Ride" in result
    mock_client.list_activities.assert_awaited_once_with(
        oldest="2026-08-01", newest="2026-08-22", athlete_id=None, limit=50
    )


@pytest.mark.asyncio
async def test_intervals_list_activities_json(mock_ctx, mock_client):
    """Test list activities tool returns JSON."""
    mock_client.list_activities = AsyncMock(return_value=[{"id": "act1"}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListActivitiesInput(
        oldest="2026-08-01", newest="2026-08-22", response_format=ResponseFormat.JSON
    )
    result = await intervals_list_activities(params, mock_ctx)

    assert '"id": "act1"' in result


@pytest.mark.asyncio
@patch("coach_mcp.models.date")
async def test_intervals_list_activities_default_dates(mock_date, mock_ctx, mock_client):
    """Test list activities tool accepts empty input and uses default dates."""
    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.list_activities = AsyncMock(
        return_value=[
            {
                "id": "act1",
                "name": "Endurance Ride",
                "type": "Ride",
                "start_date_local": "2026-08-22T09:00:00",
                "moving_time": 7200,
                "icu_training_load": 110,
            }
        ]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListActivitiesInput()
    result = await intervals_list_activities(params, mock_ctx)

    assert "Endurance Ride" in result
    mock_client.list_activities.assert_awaited_once_with(
        oldest="2026-07-30", newest="2026-08-29", athlete_id=None, limit=50
    )


@pytest.mark.asyncio
async def test_intervals_get_activity_markdown(mock_ctx, mock_client):
    """Test get activity tool returns markdown."""
    mock_client.get_activity = AsyncMock(
        return_value={
            "id": "i123",
            "name": "Threshold Intervals",
            "type": "Ride",
            "start_date_local": "2026-08-22T09:00:00",
            "moving_time": 3600,
        }
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetActivityInput(activity_id="i123", response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_activity(params, mock_ctx)

    assert "Threshold Intervals" in result
    assert "Activity:" in result
    mock_client.get_activity.assert_awaited_once_with("i123")


@pytest.mark.asyncio
async def test_intervals_get_activity_json(mock_ctx, mock_client):
    """Test get activity tool returns JSON."""
    mock_client.get_activity = AsyncMock(return_value={"id": "i123"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetActivityInput(activity_id="i123", response_format=ResponseFormat.JSON)
    result = await intervals_get_activity(params, mock_ctx)

    assert '"id": "i123"' in result


@pytest.mark.asyncio
async def test_intervals_get_activity_streams_markdown(mock_ctx, mock_client):
    """Test get activity streams tool returns markdown."""
    mock_client.get_activity_streams = AsyncMock(
        return_value=[{"type": "watts", "data": [100, 200]}]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetActivityStreamsInput(activity_id="i123", response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_activity_streams(params, mock_ctx)

    assert "Activity Streams Data" in result
    assert "watts" in result
    mock_client.get_activity_streams.assert_awaited_once_with("i123", params.types)


@pytest.mark.asyncio
async def test_intervals_get_activity_streams_json(mock_ctx, mock_client):
    """Test get activity streams tool returns JSON."""
    mock_client.get_activity_streams = AsyncMock(return_value=[{"type": "watts"}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetActivityStreamsInput(
        activity_id="i123", types=["watts"], response_format=ResponseFormat.JSON
    )
    result = await intervals_get_activity_streams(params, mock_ctx)

    assert '"type": "watts"' in result


@pytest.mark.asyncio
async def test_intervals_get_activity_intervals(mock_ctx, mock_client):
    """Test get activity intervals tool returns JSON."""
    mock_client.get_activity_intervals = AsyncMock(
        return_value={"intervals": [{"name": "Interval 1"}]}
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetActivityIntervalsInput(activity_id="i123")
    result = await intervals_get_activity_intervals(params, mock_ctx)

    assert '"intervals"' in result
    assert "Interval 1" in result
    mock_client.get_activity_intervals.assert_awaited_once_with("i123")


@pytest.mark.asyncio
async def test_intervals_get_power_curve_athlete_markdown(mock_ctx, mock_client):
    """Test get power curve tool returns markdown for athlete curves."""
    mock_client.get_power_curve = AsyncMock(
        return_value={"Ride": {"5": 850, "60": 300, "300": 280}}
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetPowerCurveInput(
        athlete_id="i456", sport_type="Ride", response_format=ResponseFormat.MARKDOWN
    )
    result = await intervals_get_power_curve(params, mock_ctx)

    assert "Power Curve" in result
    assert "850" in result
    assert "300" in result
    mock_client.get_power_curve.assert_awaited_once_with("i456", "Ride")


@pytest.mark.asyncio
async def test_intervals_get_power_curve_athlete_json(mock_ctx, mock_client):
    """Test get power curve tool returns JSON for athlete curves."""
    mock_client.get_power_curve = AsyncMock(return_value={"Ride": {"60": 300}})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetPowerCurveInput(response_format=ResponseFormat.JSON)
    result = await intervals_get_power_curve(params, mock_ctx)

    assert '"Ride"' in result
    assert '"60": 300' in result
    mock_client.get_power_curve.assert_awaited_once_with(None, "Ride")


@pytest.mark.asyncio
async def test_intervals_get_power_curve_activity_markdown(mock_ctx, mock_client):
    """Test get power curve tool returns markdown for activity curve."""
    mock_client.get_activity_power_curve = AsyncMock(return_value={"5": 900, "60": 320, "300": 290})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetPowerCurveInput(activity_id="i123", response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_power_curve(params, mock_ctx)

    assert "Power Curve" in result
    assert "900" in result
    assert "320" in result
    mock_client.get_activity_power_curve.assert_awaited_once_with("i123")
    mock_client.get_power_curve.assert_not_awaited()


@pytest.mark.asyncio
async def test_intervals_get_power_curve_activity_json(mock_ctx, mock_client):
    """Test get power curve tool returns JSON for activity curve."""
    mock_client.get_activity_power_curve = AsyncMock(return_value={"60": 320})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetPowerCurveInput(activity_id="i123", response_format=ResponseFormat.JSON)
    result = await intervals_get_power_curve(params, mock_ctx)

    assert '"60": 320' in result
    mock_client.get_activity_power_curve.assert_awaited_once_with("i123")


@pytest.mark.asyncio
async def test_intervals_get_power_curve_error(mock_ctx, mock_client):
    """Test get power curve tool handles API errors gracefully."""
    mock_client.get_power_curve = AsyncMock(
        side_effect=IntervalsNotFoundError("Not found", status_code=404)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetPowerCurveInput(athlete_id="i999")
    result = await intervals_get_power_curve(params, mock_ctx)

    assert "Error fetching power curve" in result
    assert "Not found" in result


@pytest.mark.asyncio
async def test_intervals_get_power_model_markdown(mock_ctx, mock_client):
    """Test get power model tool returns markdown."""
    mock_client.get_power_model = AsyncMock(
        return_value={
            "cp": 300,
            "wPrime": 20000,
            "pMax": 1200,
            "model": "Morton",
            "ftp": 300,
        }
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetPowerModelInput(
        athlete_id="i456", sport_type="Ride", response_format=ResponseFormat.MARKDOWN
    )
    result = await intervals_get_power_model(params, mock_ctx)

    assert "Critical Power Model" in result
    assert "300" in result
    assert "20000" in result
    assert "1200" in result
    assert "Morton" in result
    mock_client.get_power_model.assert_awaited_once_with("i456", "Ride")


@pytest.mark.asyncio
async def test_intervals_get_power_model_json(mock_ctx, mock_client):
    """Test get power model tool returns JSON."""
    mock_client.get_power_model = AsyncMock(return_value={"cp": 300, "wPrime": 20000, "pMax": 1200})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetPowerModelInput(response_format=ResponseFormat.JSON)
    result = await intervals_get_power_model(params, mock_ctx)

    assert '"cp": 300' in result
    assert '"wPrime": 20000' in result
    assert '"pMax": 1200' in result
    mock_client.get_power_model.assert_awaited_once_with(None, "Ride")


@pytest.mark.asyncio
async def test_intervals_get_power_model_error(mock_ctx, mock_client):
    """Test get power model tool handles API errors gracefully."""
    mock_client.get_power_model = AsyncMock(
        side_effect=IntervalsNotFoundError("Not found", status_code=404)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetPowerModelInput(athlete_id="i999")
    result = await intervals_get_power_model(params, mock_ctx)

    assert "Error fetching power model" in result
    assert "Not found" in result


@pytest.mark.asyncio
async def test_intervals_create_activity(mock_ctx, mock_client):
    """Test create activity tool."""
    mock_client.create_activity = AsyncMock(return_value={"id": "i999", "name": "Manual Entry"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = CreateActivityInput(
        name="Manual Entry",
        type="Ride",
        start_date_local="2026-08-22T10:00:00",
        moving_time_seconds=3600,
    )
    result = await intervals_create_activity(params, mock_ctx)

    assert "Successfully created activity" in result
    assert "i999" in result
    mock_client.create_activity.assert_awaited_once()


@pytest.mark.asyncio
async def test_intervals_update_activity(mock_ctx, mock_client):
    """Test update activity tool."""
    mock_client.update_activity = AsyncMock(return_value={"id": "i123", "name": "Updated"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = UpdateActivityInput(activity_id="i123", name="Updated", feel=2)
    result = await intervals_update_activity(params, mock_ctx)

    assert "Successfully updated activity" in result
    assert "Updated" in result
    mock_client.update_activity.assert_awaited_once_with("i123", {"name": "Updated", "feel": 2})


@pytest.mark.asyncio
async def test_intervals_delete_activity(mock_ctx, mock_client):
    """Test delete activity tool."""
    mock_client.delete_activity = AsyncMock(return_value={"status": "success"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = DeleteActivityInput(activity_id="i123")
    result = await intervals_delete_activity(params, mock_ctx)

    assert "Successfully deleted activity" in result
    mock_client.delete_activity.assert_awaited_once_with("i123")


# ---------------------------------------------------------------------------
# Wellness & Fitness Tool Handler Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervals_get_wellness_markdown(mock_ctx, mock_client):
    """Test get wellness tool returns markdown."""
    mock_client.get_wellness = AsyncMock(
        return_value=[{"id": "2026-08-22", "restingHR": 48, "readiness": 85.5}]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetWellnessInput(
        oldest="2026-08-01", newest="2026-08-22", response_format=ResponseFormat.MARKDOWN
    )
    result = await intervals_get_wellness(params, mock_ctx)

    assert "Wellness & Recovery History" in result
    assert "48" in result
    mock_client.get_wellness.assert_awaited_once_with(
        oldest="2026-08-01", newest="2026-08-22", athlete_id=None
    )


@pytest.mark.asyncio
async def test_intervals_get_wellness_json(mock_ctx, mock_client):
    """Test get wellness tool returns JSON."""
    mock_client.get_wellness = AsyncMock(return_value=[{"id": "2026-08-22"}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetWellnessInput(
        oldest="2026-08-01", newest="2026-08-22", response_format=ResponseFormat.JSON
    )
    result = await intervals_get_wellness(params, mock_ctx)

    assert '"id": "2026-08-22"' in result


@pytest.mark.asyncio
@patch("coach_mcp.models.date")
async def test_intervals_get_wellness_default_dates(mock_date, mock_ctx, mock_client):
    """Test get wellness tool accepts empty input and uses default dates."""
    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.get_wellness = AsyncMock(
        return_value=[{"id": "2026-08-29", "restingHR": 48, "readiness": 85.5}]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetWellnessInput()
    result = await intervals_get_wellness(params, mock_ctx)

    assert "48" in result
    mock_client.get_wellness.assert_awaited_once_with(
        oldest="2026-08-22", newest="2026-08-29", athlete_id=None
    )


@pytest.mark.asyncio
async def test_intervals_record_wellness(mock_ctx, mock_client):
    """Test record wellness tool."""
    mock_client.record_wellness = AsyncMock(return_value={"id": "2026-08-22"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = RecordWellnessInput(date="2026-08-22", restingHR=48, readiness=85.5)
    result = await intervals_record_wellness(params, mock_ctx)

    assert "Successfully recorded wellness" in result
    mock_client.record_wellness.assert_awaited_once_with(
        "2026-08-22", {"restingHR": 48, "readiness": 85.5}, athlete_id=None
    )


@pytest.mark.asyncio
async def test_intervals_record_wellness_bulk(mock_ctx, mock_client):
    """Test record bulk wellness tool."""
    mock_client.record_wellness_bulk = AsyncMock(
        return_value=[{"id": "2026-08-22"}, {"id": "2026-08-23"}]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = RecordWellnessBulkInput(
        records=[
            WellnessRecordItem(date="2026-08-22", restingHR=48),
            WellnessRecordItem(date="2026-08-23", readiness=85.5),
        ]
    )
    result = await intervals_record_wellness_bulk(params, mock_ctx)

    assert "Successfully recorded bulk wellness" in result
    assert "2 day(s)" in result
    mock_client.record_wellness_bulk.assert_awaited_once_with(
        [
            {"date": "2026-08-22", "restingHR": 48},
            {"date": "2026-08-23", "readiness": 85.5},
        ],
        athlete_id=None,
    )


@pytest.mark.asyncio
async def test_intervals_record_wellness_bulk_error(mock_ctx, mock_client):
    """Test record bulk wellness tool handles API errors gracefully."""
    mock_client.record_wellness_bulk = AsyncMock(
        side_effect=IntervalsAPIError("Server error", status_code=500)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = RecordWellnessBulkInput(records=[WellnessRecordItem(date="2026-08-22", restingHR=48)])
    result = await intervals_record_wellness_bulk(params, mock_ctx)

    assert "Error recording bulk wellness" in result
    assert "Server error" in result


def test_intervals_record_wellness_bulk_docstring_caveat():
    """Test bulk wellness tool docstring contains sync-provider caveat."""
    docstring = intervals_record_wellness_bulk.__doc__ or ""
    assert "re-sync" in docstring
    assert "Oura" in docstring


@pytest.mark.asyncio
async def test_intervals_get_fitness_summary_markdown(mock_ctx, mock_client):
    """Test fitness summary tool returns markdown."""
    mock_client.get_wellness = AsyncMock(
        return_value=[
            {"id": "2026-08-21", "ctl": 50.0, "atl": 60.0},
            {"id": "2026-08-22", "ctl": 52.0, "atl": 58.0},
        ]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetFitnessSummaryInput(
        oldest="2026-08-01", newest="2026-08-22", response_format=ResponseFormat.MARKDOWN
    )
    result = await intervals_get_fitness_summary(params, mock_ctx)

    assert "Training Load & Fitness Status" in result
    assert "CTL" in result
    mock_client.get_wellness.assert_awaited_once_with(
        oldest="2026-08-01", newest="2026-08-22", athlete_id=None
    )


@pytest.mark.asyncio
async def test_intervals_get_fitness_summary_json(mock_ctx, mock_client):
    """Test fitness summary tool returns JSON."""
    mock_client.get_wellness = AsyncMock(return_value=[{"id": "2026-08-22", "ctl": 52.0}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetFitnessSummaryInput(
        oldest="2026-08-01", newest="2026-08-22", response_format=ResponseFormat.JSON
    )
    result = await intervals_get_fitness_summary(params, mock_ctx)

    assert '"ctl": 52.0' in result


@pytest.mark.asyncio
@patch("coach_mcp.models.date")
async def test_intervals_get_fitness_summary_default_dates(mock_date, mock_ctx, mock_client):
    """Test fitness summary tool accepts empty input and uses default dates."""
    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.get_wellness = AsyncMock(
        return_value=[{"id": "2026-08-29", "ctl": 52.0, "atl": 58.0}]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetFitnessSummaryInput()
    result = await intervals_get_fitness_summary(params, mock_ctx)

    assert "52.0" in result
    mock_client.get_wellness.assert_awaited_once_with(
        oldest="2026-07-18", newest="2026-08-29", athlete_id=None
    )


@pytest.mark.asyncio
@patch("coach_mcp.server.date")
async def test_intervals_get_readiness_dashboard_markdown(mock_date, mock_ctx, mock_client):
    """Test readiness dashboard tool returns markdown."""
    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.get_wellness = AsyncMock(
        return_value=[{"id": "2026-08-29", "ctl": 52.0, "atl": 58.0}]
    )
    mock_client.get_sport_settings = AsyncMock(return_value=[{"types": ["Ride"], "ftp": 300}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetReadinessDashboardInput(days=7, response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_readiness_dashboard(params, mock_ctx)

    assert "Daily Readiness & Training Dashboard" in result
    mock_client.get_wellness.assert_awaited_once_with(
        oldest="2026-08-23", newest="2026-08-29", athlete_id=None
    )
    mock_client.get_sport_settings.assert_awaited_once_with(athlete_id=None)


@pytest.mark.asyncio
@patch("coach_mcp.server.date")
async def test_intervals_get_readiness_dashboard_json(mock_date, mock_ctx, mock_client):
    """Test readiness dashboard tool returns JSON."""
    import json

    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.get_wellness = AsyncMock(
        return_value=[{"id": "2026-08-29", "ctl": 52.0, "atl": 58.0}]
    )
    mock_client.get_sport_settings = AsyncMock(return_value=[{"ftp": 300}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetReadinessDashboardInput(response_format=ResponseFormat.JSON)
    result = await intervals_get_readiness_dashboard(params, mock_ctx)

    data = json.loads(result)
    assert data["fitness"]["ctl"] == 52.0


@pytest.mark.asyncio
@patch("coach_mcp.server.date")
async def test_intervals_get_readiness_dashboard_empty(mock_date, mock_ctx, mock_client):
    """Test readiness dashboard tool handles empty wellness data."""
    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.get_wellness = AsyncMock(return_value=[])
    mock_client.get_sport_settings = AsyncMock(return_value=[])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetReadinessDashboardInput()
    result = await intervals_get_readiness_dashboard(params, mock_ctx)

    assert "Daily Readiness & Training Dashboard" in result
    assert "N/A" in result


@pytest.mark.asyncio
@patch("coach_mcp.server.date")
async def test_intervals_get_readiness_dashboard_api_error(mock_date, mock_ctx, mock_client):
    """Test readiness dashboard tool handles API errors gracefully."""
    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.get_wellness = AsyncMock(
        side_effect=IntervalsAPIError("Server error", status_code=500)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetReadinessDashboardInput()
    result = await intervals_get_readiness_dashboard(params, mock_ctx)

    assert "Error fetching readiness dashboard" in result
    assert "Server error" in result


@pytest.mark.asyncio
@patch("coach_mcp.server.date")
async def test_intervals_get_readiness_dashboard_concurrent(mock_date, mock_ctx, mock_client):
    """Test readiness dashboard awaits wellness and sport settings concurrently."""
    import asyncio
    import time

    mock_date.today.return_value = date(2026, 8, 29)

    async def slow_get_wellness(*args, **kwargs):
        await asyncio.sleep(0.05)
        return [{"id": "2026-08-29", "ctl": 52.0, "atl": 58.0}]

    async def slow_get_sport_settings(*args, **kwargs):
        await asyncio.sleep(0.05)
        return [{"types": ["Ride"], "ftp": 300}]

    mock_client.get_wellness = AsyncMock(side_effect=slow_get_wellness)
    mock_client.get_sport_settings = AsyncMock(side_effect=slow_get_sport_settings)
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetReadinessDashboardInput(days=7, response_format=ResponseFormat.MARKDOWN)
    start = time.perf_counter()
    result = await intervals_get_readiness_dashboard(params, mock_ctx)
    elapsed = time.perf_counter() - start

    assert "Daily Readiness & Training Dashboard" in result
    assert elapsed < 0.09  # sequential would be ~0.10s
    mock_client.get_wellness.assert_awaited_once()
    mock_client.get_sport_settings.assert_awaited_once()


@pytest.mark.asyncio
@patch("coach_mcp.server.date")
async def test_intervals_get_readiness_dashboard_gather_api_error(mock_date, mock_ctx, mock_client):
    """Test readiness dashboard handles IntervalsAPIError from one gather task."""
    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.get_wellness = AsyncMock(
        side_effect=IntervalsAPIError("Server error", status_code=500)
    )
    mock_client.get_sport_settings = AsyncMock(return_value=[{"ftp": 300}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetReadinessDashboardInput()
    result = await intervals_get_readiness_dashboard(params, mock_ctx)

    assert "Error fetching readiness dashboard" in result
    assert "Server error" in result


# ---------------------------------------------------------------------------
# ICU Bounded Wellness Tools (#84)
# ---------------------------------------------------------------------------


def _icu_wellness_raw_payload() -> list[dict[str, object]]:
    """Raw ICU wellness payload including non-whitelisted exfiltration bait."""
    return [
        {
            "id": "2026-10-09",
            "restingHR": 444,
            "hrv": 62.5,
            "weight": 77.7,
            "sleepSecs": 28800,
            "sleepQuality": 3,
            "readiness": 88.0,
            "soreness": 2,
            "fatigue": 2,
            "stress": 1,
            "mood": 3,
            "injury": 1,
            "comments": "secret-comment-text",
            "measurements": {"bp": "120/80"},
            "ctl": 55.0,
            "atl": 65.0,
        }
    ]


def test_format_icu_wellness_markdown():
    """Test bounded wellness markdown table renders whitelisted fields only."""
    days = project_wellness_days(_icu_wellness_raw_payload())
    result = format_icu_wellness(days)

    assert "# Bounded Wellness History (1 days)" in result
    assert "2026-10-09" in result
    assert "8.0" in result  # sleep hours derived from sleepSecs
    assert "62.5" in result  # hrv
    assert "88.0" in result  # readiness
    assert "-10.0" in result  # TSB derived as ctl - atl
    # Non-whitelisted raw values never surface.
    assert "77.7" not in result  # weight
    assert "444" not in result  # restingHR
    assert "secret-comment-text" not in result  # comments


def test_format_icu_wellness_json():
    """Test bounded wellness JSON output is the whitelist projection."""
    days = project_wellness_days(_icu_wellness_raw_payload())
    result = format_icu_wellness(days, fmt_json=True)

    parsed = json.loads(result)
    assert set(parsed[0].keys()) == {
        "date",
        "sleep_hours",
        "hrv",
        "soreness",
        "fatigue",
        "stress",
        "readiness",
        "ctl",
        "atl",
        "tsb",
    }
    assert parsed[0]["tsb"] == -10.0
    assert "77.7" not in result
    assert "444" not in result


def test_format_icu_wellness_empty():
    """Test bounded wellness formatter handles an empty projection."""
    result = format_icu_wellness(project_wellness_days([]))
    assert "No wellness records" in result


@pytest.mark.asyncio
async def test_icu_get_wellness_markdown(mock_ctx, mock_client):
    """Test bounded wellness tool returns the whitelisted markdown table."""
    mock_client.get_wellness = AsyncMock(return_value=_icu_wellness_raw_payload())
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuGetWellnessInput(oldest="2026-09-10", newest="2026-10-09")
    result = await icu_get_wellness(params, mock_ctx)

    assert "Bounded Wellness History" in result
    assert "62.5" in result
    assert "77.7" not in result
    assert "444" not in result
    assert "secret-comment-text" not in result
    mock_client.get_wellness.assert_awaited_once_with(
        oldest="2026-09-10", newest="2026-10-09", athlete_id=None
    )


@pytest.mark.asyncio
async def test_icu_get_wellness_json_whitelist_only(mock_ctx, mock_client):
    """Binding condition 2 (AC3): non-whitelisted ICU fields never appear in output."""
    mock_client.get_wellness = AsyncMock(return_value=_icu_wellness_raw_payload())
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuGetWellnessInput(
        oldest="2026-09-10", newest="2026-10-09", response_format=ResponseFormat.JSON
    )
    result = await icu_get_wellness(params, mock_ctx)

    parsed = json.loads(result)
    assert set(parsed[0].keys()) == {
        "date",
        "sleep_hours",
        "hrv",
        "soreness",
        "fatigue",
        "stress",
        "readiness",
        "ctl",
        "atl",
        "tsb",
    }
    for banned in ("weight", "restingHR", "mood", "injury", "comments", "measurements"):
        assert f'"{banned}"' not in result
    assert "77.7" not in result
    assert "secret-comment-text" not in result


@pytest.mark.asyncio
@patch("coach_mcp.models.date")
async def test_icu_get_wellness_clamps_wide_range_server_side(mock_date, mock_ctx, mock_client):
    """Binding condition 1 (AC2): a >90-day span is clamped before the ICU call."""
    mock_date.today.return_value = date(2026, 10, 10)
    mock_client.get_wellness = AsyncMock(return_value=[])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuGetWellnessInput(oldest="2026-01-01", newest="2026-10-10")
    await icu_get_wellness(params, mock_ctx)

    mock_client.get_wellness.assert_awaited_once_with(
        oldest="2026-07-12", newest="2026-10-10", athlete_id=None
    )


@pytest.mark.asyncio
@patch("coach_mcp.models.date")
async def test_icu_get_wellness_default_dates(mock_date, mock_ctx, mock_client):
    """Test bounded wellness tool computes a smart 30-day default window."""
    mock_date.today.return_value = date(2026, 10, 10)
    mock_client.get_wellness = AsyncMock(return_value=[])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuGetWellnessInput()
    await icu_get_wellness(params, mock_ctx)

    mock_client.get_wellness.assert_awaited_once_with(
        oldest="2026-09-10", newest="2026-10-10", athlete_id=None
    )


@pytest.mark.asyncio
async def test_icu_get_wellness_error(mock_ctx, mock_client):
    """Test bounded wellness tool follows the handled error-string convention."""
    mock_client.get_wellness = AsyncMock(
        side_effect=IntervalsAPIError("wellness upstream down", status_code=500)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuGetWellnessInput(oldest="2026-09-10", newest="2026-10-09")
    result = await icu_get_wellness(params, mock_ctx)

    assert result.startswith("Error")
    assert "wellness upstream down" in result


def test_icu_get_wellness_read_only_annotation():
    """Test the bounded wellness tool is annotated read-only."""
    tools = mcp._tool_manager.list_tools()
    annotations = {t.name: t.annotations for t in tools}
    annotation = annotations["icu_get_wellness"]
    assert isinstance(annotation, ToolAnnotations)
    assert annotation.read_only_hint is True


# ---------------------------------------------------------------------------
# ICU Session Comment Tool (#85)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_icu_add_session_comment_success(mock_ctx, mock_client):
    """Test the confirmed write posts the sanitized comment exactly once."""
    mock_client.add_activity_message = AsyncMock(
        return_value={"id": "m1", "activityId": "i123", "message": "Great debrief."}
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuAddSessionCommentInput(
        activity_id="i123", comment="Great debrief: 4x8min @ 300W.", confirmed=True
    )
    result = await icu_add_session_comment(params, mock_ctx)

    assert "Successfully posted session comment" in result
    assert "i123" in result
    mock_client.add_activity_message.assert_awaited_once_with(
        "i123", "Great debrief: 4x8min @ 300W."
    )


@pytest.mark.asyncio
async def test_icu_add_session_comment_requires_confirmation(mock_ctx, mock_client):
    """Binding condition 1 (AC2): unconfirmed invocation is rejected server-side."""
    mock_client.add_activity_message = AsyncMock()
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuAddSessionCommentInput(activity_id="i123", comment="Great debrief.")
    result = await icu_add_session_comment(params, mock_ctx)

    assert result.startswith("Error")
    assert "confirmation" in result
    mock_client.add_activity_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_icu_add_session_comment_posts_sanitized_text(mock_ctx, mock_client):
    """Binding condition 4: the posted text is the sanitized comment, never raw markup."""
    mock_client.add_activity_message = AsyncMock(return_value={"id": "m1"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuAddSessionCommentInput(
        activity_id="i123",
        comment="<script>alert('xss')</script>Clean debrief text.",
        confirmed=True,
    )
    await icu_add_session_comment(params, mock_ctx)

    sent_text = mock_client.add_activity_message.await_args.args[1]
    assert "<script>" not in sent_text
    assert "alert('xss')" not in sent_text
    assert "Clean debrief text." in sent_text


@pytest.mark.asyncio
async def test_icu_add_session_comment_error(mock_ctx, mock_client):
    """Test the write tool follows the handled error-string convention."""
    mock_client.add_activity_message = AsyncMock(
        side_effect=IntervalsAPIError("messages upstream down", status_code=500)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuAddSessionCommentInput(activity_id="i123", comment="Great debrief.", confirmed=True)
    result = await icu_add_session_comment(params, mock_ctx)

    assert result.startswith("Error")
    assert "messages upstream down" in result


def test_icu_add_session_comment_annotations():
    """AC8: a comment post is non-destructive and not idempotent."""
    tools = mcp._tool_manager.list_tools()
    annotations = {t.name: t.annotations for t in tools}
    annotation = annotations["icu_add_session_comment"]
    assert isinstance(annotation, ToolAnnotations)
    assert annotation.read_only_hint is False
    assert annotation.destructive_hint is False
    assert annotation.idempotent_hint is False


def test_icu_add_session_comment_docstring_documents_contract():
    """The docstring documents the validated-debrief-data contract (condition 4)."""
    docstring = icu_add_session_comment.__doc__ or ""
    assert "validated debrief data" in docstring
    assert "raw-LLM" in docstring
    assert "2000" in docstring


# ---------------------------------------------------------------------------
# Events Tool Handler Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervals_list_events_markdown(mock_ctx, mock_client):
    """Test list events tool returns markdown."""
    mock_client.list_events = AsyncMock(
        return_value=[
            {
                "id": "evt1",
                "name": "VO2max Intervals",
                "category": "WORKOUT",
                "type": "Ride",
                "start_date_local": "2026-08-22T08:00:00",
            }
        ]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListEventsInput(
        oldest="2026-08-01",
        newest="2026-08-22",
        category="WORKOUT",
        response_format=ResponseFormat.MARKDOWN,
    )
    result = await intervals_list_events(params, mock_ctx)

    assert "Planned Workouts & Events" in result
    assert "VO2max Intervals" in result
    mock_client.list_events.assert_awaited_once_with(
        oldest="2026-08-01", newest="2026-08-22", athlete_id=None, category="WORKOUT"
    )


@pytest.mark.asyncio
async def test_intervals_list_events_json(mock_ctx, mock_client):
    """Test list events tool returns JSON."""
    mock_client.list_events = AsyncMock(return_value=[{"id": "evt1"}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListEventsInput(
        oldest="2026-08-01", newest="2026-08-22", response_format=ResponseFormat.JSON
    )
    result = await intervals_list_events(params, mock_ctx)

    assert '"id": "evt1"' in result


@pytest.mark.asyncio
@patch("coach_mcp.models.date")
async def test_intervals_list_events_default_dates(mock_date, mock_ctx, mock_client):
    """Test list events tool accepts empty input and uses default dates."""
    mock_date.today.return_value = date(2026, 8, 29)
    mock_client.list_events = AsyncMock(
        return_value=[
            {
                "id": "evt1",
                "name": "VO2max Intervals",
                "category": "WORKOUT",
                "type": "Ride",
                "start_date_local": "2026-08-22T08:00:00",
            }
        ]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListEventsInput()
    result = await intervals_list_events(params, mock_ctx)

    assert "VO2max Intervals" in result
    mock_client.list_events.assert_awaited_once_with(
        oldest="2026-08-29", newest="2026-09-28", athlete_id=None, category=None
    )


@pytest.mark.asyncio
async def test_intervals_get_event_markdown(mock_ctx, mock_client):
    """Test get event tool returns markdown."""
    mock_client.get_event = AsyncMock(
        return_value={
            "id": "evt123",
            "name": "Threshold 3x10",
            "type": "Ride",
            "category": "WORKOUT",
            "start_date_local": "2026-08-22T08:00:00",
            "workout_doc": "- 10m warmup",
        }
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetEventInput(event_id="evt123", response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_event(params, mock_ctx)

    assert "Scheduled Workout" in result
    assert "Threshold 3x10" in result
    assert "- 10m warmup" in result
    mock_client.get_event.assert_awaited_once_with("evt123")


@pytest.mark.asyncio
async def test_intervals_get_event_workout_doc_dict(mock_ctx, mock_client):
    """Test get event tool handles dict workout_doc payload without TypeError."""
    mock_client.get_event = AsyncMock(
        return_value={
            "id": "evt123",
            "name": "Threshold 3x10",
            "type": "Ride",
            "category": "WORKOUT",
            "start_date_local": "2026-08-22T08:00:00",
            "workout_doc": {"steps": [{"duration": 600, "power": 0.95}]},
        }
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetEventInput(event_id="evt123", response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_event(params, mock_ctx)

    assert "Scheduled Workout" in result
    assert "Threshold 3x10" in result
    assert "steps" in result
    assert "600" in result
    mock_client.get_event.assert_awaited_once_with("evt123")


@pytest.mark.asyncio
async def test_intervals_get_event_workout_doc_dict_with_description(mock_ctx, mock_client):
    """Test get event tool falls back to description DSL when workout_doc is a dict."""
    mock_client.get_event = AsyncMock(
        return_value={
            "id": "evt123",
            "name": "Threshold 3x10",
            "type": "Ride",
            "category": "WORKOUT",
            "start_date_local": "2026-08-22T08:00:00",
            "description": "- 10m warmup\n- 3x 10m 95%",
            "workout_doc": {"steps": [{"duration": 600, "power": 0.95}]},
        }
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetEventInput(event_id="evt123", response_format=ResponseFormat.MARKDOWN)
    result = await intervals_get_event(params, mock_ctx)

    assert "Scheduled Workout" in result
    assert "- 10m warmup" in result
    assert "- 3x 10m 95%" in result
    mock_client.get_event.assert_awaited_once_with("evt123")


@pytest.mark.asyncio
async def test_intervals_get_event_json(mock_ctx, mock_client):
    """Test get event tool returns JSON."""
    mock_client.get_event = AsyncMock(return_value={"id": "evt123"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetEventInput(event_id="evt123", response_format=ResponseFormat.JSON)
    result = await intervals_get_event(params, mock_ctx)

    assert '"id": "evt123"' in result


@pytest.mark.asyncio
async def test_intervals_create_event(mock_ctx, mock_client):
    """Test create event tool."""
    mock_client.create_event = AsyncMock(return_value={"id": "evt999", "name": "New Workout"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = CreateEventInput(
        start_date_local="2026-08-23T08:00:00",
        name="New Workout",
        type="Ride",
        category="WORKOUT",
    )
    result = await intervals_create_event(params, mock_ctx)

    assert "Successfully scheduled event" in result
    assert "evt999" in result
    mock_client.create_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_intervals_update_event(mock_ctx, mock_client):
    """Test update event tool."""
    mock_client.update_event = AsyncMock(return_value={"id": "evt123", "name": "Updated"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = UpdateEventInput(event_id="evt123", name="Updated")
    result = await intervals_update_event(params, mock_ctx)

    assert "Successfully updated event" in result
    assert "Updated" in result
    mock_client.update_event.assert_awaited_once_with(
        "evt123", {"name": "Updated"}, athlete_id=None
    )


# ---------------------------------------------------------------------------
# Event workout_doc DSL delivery tests (issue #68)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervals_create_event_workout_doc_delivered_via_description(mock_ctx, mock_client):
    """Test create event delivers workout DSL via description, never via workout_doc."""
    mock_client.create_event = AsyncMock(return_value={"id": "evt999"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    dsl = "- 10m 55% Warmup\n3x\n- 5m 105%\n- 3m 50%"
    params = CreateEventInput(
        start_date_local="2026-08-23T08:00:00",
        name="Over-Unders 3x10min",
        workout_doc=dsl,
    )
    await intervals_create_event(params, mock_ctx)

    mock_client.create_event.assert_awaited_once()
    payload = mock_client.create_event.await_args.args[0]
    assert payload["description"] == dsl
    assert "workout_doc" not in payload


@pytest.mark.asyncio
async def test_intervals_create_event_description_and_workout_doc_combined(mock_ctx, mock_client):
    """Test create event combines human description and workout DSL with a blank line."""
    mock_client.create_event = AsyncMock(return_value={"id": "evt999"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    dsl = "- 10m 55% Warmup\n3x\n- 5m 105%\n- 3m 50%"
    params = CreateEventInput(
        start_date_local="2026-08-23T08:00:00",
        name="Over-Unders 3x10min",
        description="These are horribly nasty.",
        workout_doc=dsl,
    )
    await intervals_create_event(params, mock_ctx)

    mock_client.create_event.assert_awaited_once()
    payload = mock_client.create_event.await_args.args[0]
    assert payload["description"] == f"These are horribly nasty.\n\n{dsl}"
    assert "workout_doc" not in payload


@pytest.mark.asyncio
async def test_intervals_create_event_without_description_or_workout_doc(mock_ctx, mock_client):
    """Test create event omits description when neither description nor workout_doc given."""
    mock_client.create_event = AsyncMock(return_value={"id": "evt999"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = CreateEventInput(
        start_date_local="2026-08-23T08:00:00",
        name="New Workout",
    )
    await intervals_create_event(params, mock_ctx)

    mock_client.create_event.assert_awaited_once()
    payload = mock_client.create_event.await_args.args[0]
    assert "description" not in payload
    assert "workout_doc" not in payload


@pytest.mark.asyncio
async def test_intervals_update_event_workout_doc_delivered_via_description(mock_ctx, mock_client):
    """Test update event delivers workout DSL via description, never via workout_doc."""
    mock_client.update_event = AsyncMock(return_value={"id": "evt123"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    dsl = "- 10m 55% Warmup\n3x\n- 5m 105%\n- 3m 50%"
    params = UpdateEventInput(event_id="evt123", workout_doc=dsl)
    await intervals_update_event(params, mock_ctx)

    mock_client.update_event.assert_awaited_once()
    payload = mock_client.update_event.await_args.args[1]
    assert payload["description"] == dsl
    assert "workout_doc" not in payload


@pytest.mark.asyncio
async def test_intervals_update_event_description_only_regression(mock_ctx, mock_client):
    """Test update event with description only keeps description unchanged."""
    mock_client.update_event = AsyncMock(return_value={"id": "evt123"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = UpdateEventInput(event_id="evt123", description="Updated instructions")
    await intervals_update_event(params, mock_ctx)

    mock_client.update_event.assert_awaited_once()
    payload = mock_client.update_event.await_args.args[1]
    assert payload["description"] == "Updated instructions"
    assert "workout_doc" not in payload


@pytest.mark.asyncio
async def test_intervals_delete_event(mock_ctx, mock_client):
    """Test delete event tool."""
    mock_client.delete_event = AsyncMock(return_value={"status": "success"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = DeleteEventInput(event_id="evt123")
    result = await intervals_delete_event(params, mock_ctx)

    assert "Successfully deleted event" in result
    mock_client.delete_event.assert_awaited_once_with("evt123", athlete_id=None)


# ---------------------------------------------------------------------------
# Folders & Workouts Tool Handler Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervals_list_folders_markdown(mock_ctx, mock_client):
    """Test list folders tool returns markdown."""
    mock_client.list_folders = AsyncMock(
        return_value=[{"id": "folder1", "name": "Base", "children": []}]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListFoldersInput(response_format=ResponseFormat.MARKDOWN)
    result = await intervals_list_folders(params, mock_ctx)

    assert "Workout Library Folders" in result
    assert "Base" in result
    mock_client.list_folders.assert_awaited_once_with(athlete_id=None)


@pytest.mark.asyncio
async def test_intervals_list_folders_json(mock_ctx, mock_client):
    """Test list folders tool returns JSON."""
    mock_client.list_folders = AsyncMock(return_value=[{"id": "folder1"}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListFoldersInput(response_format=ResponseFormat.JSON)
    result = await intervals_list_folders(params, mock_ctx)

    assert '"id": "folder1"' in result


@pytest.mark.asyncio
async def test_intervals_list_workouts_markdown(mock_ctx, mock_client):
    """Test list workouts tool returns markdown."""
    mock_client.list_workouts = AsyncMock(
        return_value=[{"id": "w1", "name": "Sweet Spot", "type": "Ride"}]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListWorkoutsInput(folder_id="folder1", response_format=ResponseFormat.MARKDOWN)
    result = await intervals_list_workouts(params, mock_ctx)

    assert "Workout Templates" in result
    assert "Sweet Spot" in result
    mock_client.list_workouts.assert_awaited_once_with(folder_id="folder1", athlete_id=None)


@pytest.mark.asyncio
async def test_intervals_list_workouts_json(mock_ctx, mock_client):
    """Test list workouts tool returns JSON."""
    mock_client.list_workouts = AsyncMock(return_value=[{"id": "w1"}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListWorkoutsInput(response_format=ResponseFormat.JSON)
    result = await intervals_list_workouts(params, mock_ctx)

    assert '"id": "w1"' in result


# ---------------------------------------------------------------------------
# Error Handling Fallback Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intervals_get_activity_not_found_error(mock_ctx, mock_client):
    """Test get activity tool handles 404 error gracefully."""
    mock_client.get_activity = AsyncMock(
        side_effect=IntervalsNotFoundError("Not found", status_code=404)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = GetActivityInput(activity_id="missing")
    result = await intervals_get_activity(params, mock_ctx)

    assert "Error fetching activity" in result
    assert "Not found" in result


@pytest.mark.asyncio
async def test_intervals_list_activities_api_error(mock_ctx, mock_client):
    """Test list activities tool handles generic API errors gracefully."""
    mock_client.list_activities = AsyncMock(
        side_effect=IntervalsAPIError("Server error", status_code=500)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = ListActivitiesInput(oldest="2026-08-01", newest="2026-08-22")
    result = await intervals_list_activities(params, mock_ctx)

    assert "Error listing activities" in result
    assert "Server error" in result


@pytest.mark.asyncio
async def test_intervals_create_event_api_error(mock_ctx, mock_client):
    """Test create event tool handles API errors gracefully."""
    mock_client.create_event = AsyncMock(
        side_effect=IntervalsAuthError("Auth failed", status_code=401)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = CreateEventInput(start_date_local="2026-08-23T08:00:00", name="Test")
    result = await intervals_create_event(params, mock_ctx)

    assert "Error scheduling event" in result
    assert "Auth failed" in result


# ---------------------------------------------------------------------------
# Formatter Tests
# ---------------------------------------------------------------------------


def test_to_json_str():
    """Test JSON string formatter."""
    data = {"key": "value", "number": 42}
    result = to_json_str(data)
    assert '"key": "value"' in result
    assert '"number": 42' in result


def test_format_profile_markdown():
    """Test profile markdown formatter."""
    data = {"athlete": {"id": "0", "name": "Test Athlete", "weight": 70.0}}
    result = format_profile(data, fmt_json=False)
    assert "Athlete Profile" in result
    assert "Test Athlete" in result
    assert "70.0" in result


def test_format_profile_json():
    """Test profile JSON formatter."""
    data = {"athlete": {"id": "0", "name": "Test Athlete"}}
    result = format_profile(data, fmt_json=True)
    assert '"name": "Test Athlete"' in result


def test_format_sport_settings_markdown():
    """Test sport settings markdown formatter."""
    data = [{"types": ["Ride"], "ftp": 300, "lthr": 170, "max_hr": 190}]
    result = format_sport_settings(data, fmt_json=False)
    assert "Sport Settings" in result
    assert "300" in result
    assert "170" in result


def test_format_sport_settings_json():
    """Test sport settings JSON formatter."""
    data = [{"ftp": 300}]
    result = format_sport_settings(data, fmt_json=True)
    assert '"ftp": 300' in result


def test_format_activities_list_markdown():
    """Test activities list markdown formatter."""
    activities = [
        {
            "id": "act1",
            "name": "Ride",
            "type": "Ride",
            "start_date_local": "2026-08-22T09:00:00",
            "moving_time": 3600,
            "distance": 45000,
            "average_watts": 200,
            "average_heartrate": 140,
            "icu_training_load": 85,
        }
    ]
    result = format_activities_list(activities, fmt_json=False)
    assert "Activities Summary" in result
    assert "Ride" in result
    assert "1h 0m" in result


def test_format_activities_list_json():
    """Test activities list JSON formatter."""
    activities = [{"id": "act1"}]
    result = format_activities_list(activities, fmt_json=True)
    assert '"id": "act1"' in result


def test_format_activities_list_empty():
    """Test activities list formatter with empty list."""
    result = format_activities_list([], fmt_json=False)
    assert "No activities found" in result


def test_format_activity_detail_markdown():
    """Test activity detail markdown formatter."""
    act = {
        "id": "i123",
        "name": "Interval Session",
        "type": "Ride",
        "start_date_local": "2026-08-22T09:00:00",
        "moving_time": 3600,
        "distance": 45000,
        "icu_weighted_avg_watts": 250,
        "average_watts": 220,
        "icu_training_load": 95,
        "icu_intensity": 0.85,
    }
    result = format_activity_detail(act, fmt_json=False)
    assert "Interval Session" in result
    assert "250" in result


def test_format_activity_detail_json():
    """Test activity detail JSON formatter."""
    act = {"id": "i123"}
    result = format_activity_detail(act, fmt_json=True)
    assert '"id": "i123"' in result


def test_format_activity_streams_markdown():
    """Test activity streams markdown formatter."""
    streams = [{"type": "watts", "data": [100, 200, 300]}]
    result = format_activity_streams(streams, fmt_json=False)
    assert "Activity Streams Data" in result
    assert "watts" in result


def test_format_activity_streams_json():
    """Test activity streams JSON formatter."""
    streams = [{"type": "watts"}]
    result = format_activity_streams(streams, fmt_json=True)
    assert '"type": "watts"' in result


def test_format_wellness_list_markdown():
    """Test wellness list markdown formatter."""
    wellness = [
        {
            "id": "2026-08-22",
            "restingHR": 48,
            "hrv": 65.5,
            "weight": 72.5,
            "sleepSecs": 28800,
            "sleepQuality": 2,
            "readiness": 85.5,
            "fatigue": 2,
            "soreness": 2,
            "stress": 2,
            "mood": 1,
        }
    ]
    result = format_wellness_list(wellness, fmt_json=False)
    assert "Wellness & Recovery History" in result
    assert "48" in result


def test_format_wellness_list_json():
    """Test wellness list JSON formatter."""
    wellness = [{"id": "2026-08-22"}]
    result = format_wellness_list(wellness, fmt_json=True)
    assert '"id": "2026-08-22"' in result


def test_format_wellness_list_empty():
    """Test wellness list formatter with empty list."""
    result = format_wellness_list([], fmt_json=False)
    assert "No wellness records found" in result


def test_format_fitness_summary_markdown():
    """Test fitness summary markdown formatter."""
    wellness = [
        {"id": "2026-08-21", "ctl": 50.0, "atl": 60.0},
        {"id": "2026-08-22", "ctl": 52.0, "atl": 58.0},
    ]
    result = format_fitness_summary(wellness, fmt_json=False)
    assert "Training Load & Fitness Status" in result
    assert "52.0" in result
    assert "58.0" in result


def test_format_fitness_summary_json():
    """Test fitness summary JSON formatter."""
    wellness = [{"id": "2026-08-22", "ctl": 52.0}]
    result = format_fitness_summary(wellness, fmt_json=True)
    assert '"ctl": 52.0' in result


def test_format_fitness_summary_empty():
    """Test fitness summary formatter with empty list."""
    result = format_fitness_summary([], fmt_json=False)
    assert "No fitness tracking records found" in result


def test_compute_fitness_metrics_full():
    """Test _compute_fitness_metrics extracts latest values."""
    from coach_mcp.formatters import _compute_fitness_metrics

    entries = [
        {"id": "2026-08-21", "ctl": 50.0, "atl": 60.0, "rampRate": 2.0},
        {"id": "2026-08-22", "ctl": 52.0, "atl": 58.0},
    ]
    result = _compute_fitness_metrics(entries)
    assert result["ctl"] == 52.0
    assert result["atl"] == 58.0
    assert result["tsb"] == -6.0
    assert result["ramp_rate"] == 2.0
    assert result["date"] == "2026-08-22"


def test_compute_fitness_metrics_computes_tsb_and_ramp():
    """Test _compute_fitness_metrics computes TSB and ramp rate when absent."""
    from coach_mcp.formatters import _compute_fitness_metrics

    entries = [
        {"id": "2026-08-21", "ctl": 50.0, "atl": 60.0},
        {"id": "2026-08-22", "ctl": 52.0, "atl": 58.0},
    ]
    result = _compute_fitness_metrics(entries)
    assert result["tsb"] == -6.0
    assert result["ramp_rate"] == 2.0


def test_compute_fitness_metrics_empty():
    """Test _compute_fitness_metrics handles empty input."""
    from coach_mcp.formatters import _compute_fitness_metrics

    result = _compute_fitness_metrics([])
    assert result["ctl"] is None
    assert result["atl"] is None
    assert result["tsb"] is None
    assert result["date"] is None


def test_format_readiness_dashboard_markdown():
    """Test readiness dashboard markdown formatter."""
    wellness = [
        {
            "id": "2026-08-29",
            "restingHR": 48,
            "hrv": 65.5,
            "sleepSecs": 28800,
            "sleepQuality": 2,
            "readiness": 85.5,
            "soreness": 2,
            "fatigue": 2,
            "stress": 2,
            "ctl": 52.0,
            "atl": 58.0,
            "rampRate": 1.5,
        }
    ]
    sport = [
        {
            "types": ["Ride"],
            "ftp": 300,
            "indoor_ftp": 295,
            "lthr": 170,
            "max_hr": 190,
            "power_zones": [150, 200, 240, 280, 320, 380],
        }
    ]
    result = format_readiness_dashboard(wellness, sport, fmt_json=False)
    assert "# Daily Readiness & Training Dashboard" in result
    assert "2026-08-29" in result
    assert "65.5" in result
    assert "8.0 h" in result
    assert "300" in result
    assert "Neutral / Productive Training" in result
    assert "Coaching Recommendation" in result


def test_format_readiness_dashboard_json():
    """Test readiness dashboard JSON formatter."""
    import json

    wellness = [{"id": "2026-08-29", "ctl": 52.0, "atl": 58.0, "readiness": 85.5}]
    sport = [{"types": ["Ride"], "ftp": 300}]
    result = format_readiness_dashboard(wellness, sport, fmt_json=True)
    data = json.loads(result)
    assert data["fitness"]["ctl"] == 52.0
    assert data["fitness"]["tsb"] == -6.0
    assert data["cycling_parameters"]["ftp_watts"] == 300
    assert "recommendation" in data


def test_format_readiness_dashboard_empty_wellness():
    """Test readiness dashboard formatter handles empty wellness data."""
    sport = [{"types": ["Ride"], "ftp": 300}]
    result = format_readiness_dashboard([], sport, fmt_json=False)
    assert "# Daily Readiness & Training Dashboard" in result
    assert "N/A" in result


def test_format_readiness_dashboard_empty_sport_settings():
    """Test readiness dashboard formatter handles missing sport settings."""
    wellness = [{"id": "2026-08-29", "ctl": 52.0, "atl": 58.0}]
    result = format_readiness_dashboard(wellness, [], fmt_json=False)
    assert "# Daily Readiness & Training Dashboard" in result
    assert "Not configured" in result


def test_format_events_list_markdown():
    """Test events list markdown formatter."""
    events = [
        {
            "id": "evt1",
            "name": "VO2max",
            "category": "WORKOUT",
            "type": "Ride",
            "start_date_local": "2026-08-22T08:00:00",
            "moving_time": 3600,
            "icu_training_load": 120,
        }
    ]
    result = format_events_list(events, fmt_json=False)
    assert "Planned Workouts & Events" in result
    assert "VO2max" in result


def test_format_events_list_json():
    """Test events list JSON formatter."""
    events = [{"id": "evt1"}]
    result = format_events_list(events, fmt_json=True)
    assert '"id": "evt1"' in result


def test_format_events_list_empty():
    """Test events list formatter with empty list."""
    result = format_events_list([], fmt_json=False)
    assert "No planned events" in result


def test_format_folders_markdown():
    """Test folders markdown formatter."""
    folders = [{"id": "folder1", "name": "Base", "children": []}]
    result = format_folders(folders, fmt_json=False)
    assert "Workout Library Folders" in result
    assert "Base" in result


def test_format_folders_json():
    """Test folders JSON formatter."""
    folders = [{"id": "folder1"}]
    result = format_folders(folders, fmt_json=True)
    assert '"id": "folder1"' in result


def test_format_workouts_markdown():
    """Test workouts markdown formatter."""
    workouts = [{"id": "w1", "name": "Sweet Spot", "type": "Ride", "icu_training_load": 90}]
    result = format_workouts(workouts, fmt_json=False)
    assert "Workout Templates" in result
    assert "Sweet Spot" in result


def test_format_workouts_json():
    """Test workouts JSON formatter."""
    workouts = [{"id": "w1"}]
    result = format_workouts(workouts, fmt_json=True)
    assert '"id": "w1"' in result


def test_format_power_curve_markdown():
    """Test power curve markdown formatter."""
    data = {"Ride": {"5": 850, "60": 300, "300": 280}}
    result = format_power_curve(data, response_format=ResponseFormat.MARKDOWN)
    assert "Power Curve" in result
    assert "850" in result
    assert "300" in result


def test_format_power_curve_json():
    """Test power curve JSON formatter."""
    data = {"Ride": {"60": 300}}
    result = format_power_curve(data, response_format=ResponseFormat.JSON)
    assert '"Ride"' in result
    assert '"60": 300' in result


def test_format_power_curve_activity_markdown():
    """Test power curve markdown formatter for activity curve data."""
    data = {"5": 900, "60": 320, "300": 290}
    result = format_power_curve(data, response_format=ResponseFormat.MARKDOWN)
    assert "Power Curve" in result
    assert "900" in result
    assert "320" in result


def test_format_power_curve_empty():
    """Test power curve formatter with empty data."""
    result = format_power_curve({}, response_format=ResponseFormat.MARKDOWN)
    assert "Power Curve" in result
    assert "No power curve data" in result


def test_format_power_model_markdown():
    """Test power model markdown formatter."""
    data = {
        "cp": 300,
        "wPrime": 20000,
        "pMax": 1200,
        "model": "Morton",
        "ftp": 300,
    }
    result = format_power_model(data, fmt_json=False)
    assert "Critical Power Model" in result
    assert "300" in result
    assert "20000" in result
    assert "1200" in result
    assert "Morton" in result


def test_format_power_model_json():
    """Test power model JSON formatter."""
    data = {"cp": 300, "wPrime": 20000, "pMax": 1200}
    result = format_power_model(data, fmt_json=True)
    assert '"cp": 300' in result
    assert '"wPrime": 20000' in result
    assert '"pMax": 1200' in result


def test_format_power_model_empty():
    """Test power model formatter with empty data."""
    result = format_power_model({}, fmt_json=False)
    assert "Critical Power Model" in result
    assert "No power model data" in result


def test_format_power_model_alternative_keys():
    """Test power model formatter handles alternative field names."""
    data = {
        "ftp": 310,
        "w_prime": 21000,
        "p_max": 1250,
        "name": "CP Model",
    }
    result = format_power_model(data, fmt_json=False)
    assert "310" in result
    assert "21000" in result
    assert "1250" in result
    assert "CP Model" in result


# ---------------------------------------------------------------------------
# ICU Batch Events Tool (#94)
# ---------------------------------------------------------------------------


def _batch_params(**overrides: Any) -> IcuBatchCreateEventsInput:
    """Build a two-draft batch input with optional overrides."""
    drafts = [
        IcuEventDraft(external_id="w42-tue", date="2026-10-13", name="Tuesday Threshold"),
        IcuEventDraft(external_id="w42-wed", date="2026-10-14", name="Wednesday Recovery"),
    ]
    kwargs: dict[str, Any] = {"events": drafts}
    kwargs.update(overrides)
    return IcuBatchCreateEventsInput(**kwargs)


def _extract_preview_token(result: str) -> str:
    """Extract the confirmation token from a markdown preview response."""
    match = re.search(r"Confirmation token\*\*: `([0-9a-f]{16})`", result)
    assert match, f"no confirmation token in preview: {result}"
    return match.group(1)


@pytest.mark.asyncio
async def test_icu_batch_create_events_preview_returns_token(mock_ctx, mock_client):
    """AC3: the preview phase returns a confirmation token and writes nothing."""
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    result = await icu_batch_create_events(_batch_params(), mock_ctx)

    assert "Batch Event Preview" in result
    assert "dry-run" in result
    assert "w42-tue" in result
    assert "Tuesday Threshold" in result
    token = _extract_preview_token(result)
    assert len(token) == 16
    mock_client.bulk_create_events.assert_not_awaited()
    mock_client.list_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_icu_batch_create_events_preview_json(mock_ctx, mock_client):
    """The JSON preview carries the token and the normalized payloads."""
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = _batch_params(response_format=ResponseFormat.JSON)
    result = await icu_batch_create_events(params, mock_ctx)

    data = json.loads(result)
    assert data["phase"] == "preview"
    assert len(data["confirm_token"]) == 16
    assert data["item_count"] == 2
    assert data["events"][0]["external_id"] == "w42-tue"
    assert data["events"][0]["start_date_local"] == "2026-10-13T08:00:00"
    assert data["events"][0]["name"] == "Tuesday Threshold"


@pytest.mark.asyncio
async def test_icu_batch_create_events_executes_with_valid_token(mock_ctx, mock_client):
    """AC1/AC3: execution with the preview-derived token performs the bulk upsert."""
    mock_client.list_events = AsyncMock(return_value=[])
    mock_client.bulk_create_events = AsyncMock(
        return_value=[
            {"id": 101, "external_id": "w42-tue"},
            {"id": 102, "external_id": "w42-wed"},
        ]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    token = _extract_preview_token(preview)

    result = await icu_batch_create_events(_batch_params(confirm_token=token), mock_ctx)

    assert "Batch Event Upsert Report" in result
    assert "created" in result
    mock_client.list_events.assert_awaited_once_with(
        oldest="2026-10-13", newest="2026-10-14", athlete_id=None
    )
    mock_client.bulk_create_events.assert_awaited_once()
    sent = mock_client.bulk_create_events.await_args.args[0]
    assert sent[0]["external_id"] == "w42-tue"
    assert sent[0]["start_date_local"] == "2026-10-13T08:00:00"
    assert sent[0]["name"] == "Tuesday Threshold"


@pytest.mark.asyncio
async def test_icu_batch_create_events_rejects_token_mismatch(mock_ctx, mock_client):
    """AC3: execution with a wrong token is rejected before any network call."""
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    result = await icu_batch_create_events(_batch_params(confirm_token="0" * 16), mock_ctx)

    assert result.startswith("Error")
    assert "token" in result
    mock_client.bulk_create_events.assert_not_awaited()
    mock_client.list_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_icu_batch_create_events_rejects_empty_token(mock_ctx, mock_client):
    """AC3: an empty confirm_token is an execution attempt, not a preview."""
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    result = await icu_batch_create_events(_batch_params(confirm_token=""), mock_ctx)

    assert result.startswith("Error")
    mock_client.bulk_create_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_icu_batch_create_events_token_binds_payload(mock_ctx, mock_client):
    """AC3: changing a draft after the preview invalidates the token."""
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    token = _extract_preview_token(preview)

    tampered = IcuBatchCreateEventsInput(
        events=[
            IcuEventDraft(external_id="w42-tue", date="2026-10-13", name="Changed Title"),
            IcuEventDraft(external_id="w42-wed", date="2026-10-14", name="Wednesday Recovery"),
        ],
        confirm_token=token,
    )
    result = await icu_batch_create_events(tampered, mock_ctx)

    assert result.startswith("Error")
    assert "mismatch" in result
    mock_client.bulk_create_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_icu_batch_create_events_per_item_created_vs_updated(mock_ctx, mock_client):
    """AC1: the pre-read classifies updated (existing external_id) vs created."""
    mock_client.list_events = AsyncMock(
        return_value=[{"id": 99, "external_id": "w42-tue", "name": "Existing"}]
    )
    mock_client.bulk_create_events = AsyncMock(
        return_value=[
            {"id": 99, "external_id": "w42-tue"},
            {"id": 102, "external_id": "w42-wed"},
        ]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    token = _extract_preview_token(preview)

    result = await icu_batch_create_events(_batch_params(confirm_token=token), mock_ctx)

    assert "| w42-tue | updated | 99 |" in result
    assert "| w42-wed | created | 102 |" in result
    assert "**Updated**: 1" in result
    assert "**Created**: 1" in result


@pytest.mark.asyncio
async def test_icu_batch_create_events_idempotent_resubmission(mock_ctx, mock_client):
    """AC2: re-submitting the same external_ids upserts without duplicates."""
    mock_client.bulk_create_events = AsyncMock(
        return_value=[
            {"id": 101, "external_id": "w42-tue"},
            {"id": 102, "external_id": "w42-wed"},
        ]
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client
    # First run: the week is empty -> everything is created.
    mock_client.list_events = AsyncMock(return_value=[])

    first_preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    first_token = _extract_preview_token(first_preview)
    first_report = await icu_batch_create_events(_batch_params(confirm_token=first_token), mock_ctx)
    assert "**Created**: 2" in first_report

    # Second run: the same week now carries both external_ids -> all updated,
    # and the exact same payload (same external_ids) is re-sent for upsert.
    mock_client.list_events = AsyncMock(
        return_value=[
            {"id": 101, "external_id": "w42-tue"},
            {"id": 102, "external_id": "w42-wed"},
        ]
    )

    second_preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    second_token = _extract_preview_token(second_preview)
    second_report = await icu_batch_create_events(
        _batch_params(confirm_token=second_token), mock_ctx
    )

    assert "**Updated**: 2" in second_report
    assert "**Created**: 0" in second_report
    assert mock_client.bulk_create_events.await_count == 2
    first_payload = mock_client.bulk_create_events.await_args_list[0].args[0]
    second_payload = mock_client.bulk_create_events.await_args_list[1].args[0]
    assert first_payload == second_payload
    external_ids = [item["external_id"] for item in second_payload]
    assert len(external_ids) == len(set(external_ids)) == 2


@pytest.mark.asyncio
async def test_icu_batch_create_events_missing_from_response_failed(mock_ctx, mock_client):
    """AC1: an item missing from the API response is reported failed with a reason."""
    mock_client.list_events = AsyncMock(return_value=[])
    mock_client.bulk_create_events = AsyncMock(
        return_value=[{"id": 101, "external_id": "w42-tue"}]  # w42-wed missing
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    token = _extract_preview_token(preview)

    result = await icu_batch_create_events(_batch_params(confirm_token=token), mock_ctx)

    assert "| w42-wed | failed | - |" in result
    assert "missing from Intervals.icu response" in result
    assert "**Failed**: 1" in result


@pytest.mark.asyncio
async def test_icu_batch_create_events_api_error_all_failed(mock_ctx, mock_client):
    """A bulk POST failure follows the handled error-string convention."""
    mock_client.list_events = AsyncMock(return_value=[])
    mock_client.bulk_create_events = AsyncMock(
        side_effect=IntervalsAPIError("events bulk upstream down", status_code=500)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    token = _extract_preview_token(preview)

    result = await icu_batch_create_events(_batch_params(confirm_token=token), mock_ctx)

    assert result.startswith("Error")
    assert "events bulk upstream down" in result


@pytest.mark.asyncio
async def test_icu_batch_create_events_preread_error_aborts_before_write(mock_ctx, mock_client):
    """A pre-read failure aborts the batch before any write is attempted."""
    mock_client.list_events = AsyncMock(
        side_effect=IntervalsAPIError("events read down", status_code=500)
    )
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    token = _extract_preview_token(preview)

    result = await icu_batch_create_events(_batch_params(confirm_token=token), mock_ctx)

    assert result.startswith("Error")
    assert "events read down" in result
    mock_client.bulk_create_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_icu_batch_create_events_sanitizes_payload_before_send(mock_ctx, mock_client):
    """The payload sent upstream carries sanitized title/description text."""
    mock_client.list_events = AsyncMock(return_value=[])
    mock_client.bulk_create_events = AsyncMock(return_value=[{"id": 101, "external_id": "w42-tue"}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuBatchCreateEventsInput(
        events=[
            IcuEventDraft(
                external_id="w42-tue",
                date="2026-10-13",
                name="<script>alert('xss')</script>Threshold Day",
                description="<img src=x onerror=alert(1)>Ride steady.",
            )
        ]
    )
    preview = await icu_batch_create_events(params, mock_ctx)
    token = _extract_preview_token(preview)

    await icu_batch_create_events(
        IcuBatchCreateEventsInput(events=params.events, confirm_token=token), mock_ctx
    )

    sent = mock_client.bulk_create_events.await_args.args[0]
    assert "<script>" not in sent[0]["name"]
    assert "alert('xss')" not in sent[0]["name"]
    assert "Threshold Day" in sent[0]["name"]
    assert "<img" not in str(sent[0].get("description"))
    assert "Ride steady." in str(sent[0].get("description"))


@pytest.mark.asyncio
async def test_icu_batch_create_events_report_json(mock_ctx, mock_client):
    """The JSON execute report carries counts and per-item outcomes."""
    mock_client.list_events = AsyncMock(return_value=[])
    mock_client.bulk_create_events = AsyncMock(return_value=[{"id": 101, "external_id": "w42-tue"}])
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    params = IcuBatchCreateEventsInput(
        events=[IcuEventDraft(external_id="w42-tue", date="2026-10-13", name="Tuesday")],
        response_format=ResponseFormat.JSON,
    )
    preview = await icu_batch_create_events(params, mock_ctx)
    data = json.loads(preview)
    token = data["confirm_token"]

    result = await icu_batch_create_events(
        IcuBatchCreateEventsInput(
            events=params.events, confirm_token=token, response_format=ResponseFormat.JSON
        ),
        mock_ctx,
    )

    report = json.loads(result)
    assert report["created"] == 1
    assert report["updated"] == 0
    assert report["failed"] == 0
    assert report["outcomes"][0]["external_id"] == "w42-tue"
    assert report["outcomes"][0]["outcome"] == "created"
    assert report["outcomes"][0]["event_id"] == "101"


def test_icu_batch_create_events_annotations():
    """The batch upsert is a non-destructive, idempotent write."""
    tools = mcp._tool_manager.list_tools()
    annotations = {t.name: t.annotations for t in tools}
    annotation = annotations["icu_batch_create_events"]
    assert isinstance(annotation, ToolAnnotations)
    assert annotation.read_only_hint is False
    assert annotation.destructive_hint is False
    assert annotation.idempotent_hint is True


def test_icu_batch_create_events_docstring_documents_contract():
    """The docstring documents the gate, no-rollback semantics, and batch bound."""
    docstring = icu_batch_create_events.__doc__ or ""
    assert "confirmation token" in docstring
    assert "no rollback" in docstring
    assert "50" in docstring
    assert "external_id" in docstring


def test_build_batch_event_payload_normalization():
    """The payload builder pins the default start time and maps optional fields."""
    full = _build_batch_event_payload(
        IcuEventDraft(
            external_id="w42-tue",
            date="2026-10-13",
            name="Tuesday Threshold",
            description="3x10min @ 95%",
            workout_doc="- 10m warmup\n3x\n- 10m 95%",
            moving_time_seconds=3600,
            icu_training_load=90.0,
        )
    )
    assert full["external_id"] == "w42-tue"
    assert full["start_date_local"] == "2026-10-13T08:00:00"
    assert full["name"] == "Tuesday Threshold"
    assert full["type"] == "Ride"
    assert full["category"] == "WORKOUT"
    # workout DSL is appended to the description (single-event tool pattern).
    assert full["description"] == "3x10min @ 95%\n\n- 10m warmup\n3x\n- 10m 95%"
    assert full["moving_time"] == 3600
    assert full["icu_training_load"] == 90.0

    doc_only = _build_batch_event_payload(
        IcuEventDraft(
            external_id="w42-wed", date="2026-10-14", name="Recovery", workout_doc="- 30m easy"
        )
    )
    assert doc_only["description"] == "- 30m easy"
    assert "moving_time" not in doc_only
    assert "icu_training_load" not in doc_only

    bare = _build_batch_event_payload(
        IcuEventDraft(external_id="w42-thu", date="2026-10-15", name="Rest")
    )
    assert "description" not in bare


def test_derive_batch_confirm_token_is_deterministic_and_payload_bound():
    """The token is deterministic for identical payloads and changes with any draft."""
    payloads_a = [
        {"external_id": "a", "name": "Monday"},
        {"external_id": "b", "name": "Tuesday"},
    ]
    payloads_a_again = [
        {"external_id": "a", "name": "Monday"},
        {"external_id": "b", "name": "Tuesday"},
    ]
    payloads_b = [
        {"external_id": "a", "name": "Monday"},
        {"external_id": "b", "name": "Tuesday CHANGED"},
    ]

    token_a = _derive_batch_confirm_token(payloads_a)
    assert token_a == _derive_batch_confirm_token(payloads_a_again)
    assert len(token_a) == 16
    assert token_a != _derive_batch_confirm_token(payloads_b)
    # Key order within each payload dict must not affect the canonical
    # fingerprint (list order is semantic and does).
    assert token_a == _derive_batch_confirm_token(
        [{"name": "Monday", "external_id": "a"}, {"name": "Tuesday", "external_id": "b"}]
    )


@pytest.mark.asyncio
async def test_icu_batch_create_events_unexpected_response_shape(mock_ctx, mock_client):
    """A non-list bulk response is handled as an upstream error, never silent."""
    mock_client.list_events = AsyncMock(return_value=[])
    mock_client.bulk_create_events = AsyncMock(return_value={"unexpected": "shape"})
    mock_ctx.request_context.lifespan_state["client"] = mock_client

    preview = await icu_batch_create_events(_batch_params(), mock_ctx)
    token = _extract_preview_token(preview)

    result = await icu_batch_create_events(_batch_params(confirm_token=token), mock_ctx)

    assert result.startswith("Error")
    assert "Unexpected response shape" in result
