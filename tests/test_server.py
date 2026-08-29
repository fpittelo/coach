"""Comprehensive tests for Coach MCP MCPServer handlers and formatters."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from coach_mcp.client import IntervalsAPIError, IntervalsAuthError, IntervalsNotFoundError
from coach_mcp.formatters import (
    format_activities_list,
    format_activity_detail,
    format_activity_streams,
    format_events_list,
    format_fitness_summary,
    format_folders,
    format_power_curve,
    format_power_model,
    format_profile,
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
    GetSportSettingsInput,
    GetWellnessInput,
    ListActivitiesInput,
    ListEventsInput,
    ListFoldersInput,
    ListWorkoutsInput,
    RecordWellnessInput,
    ResponseFormat,
    UpdateActivityInput,
    UpdateEventInput,
)
from coach_mcp.server import (
    _get_client_from_ctx,
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
    intervals_get_sport_settings,
    intervals_get_wellness,
    intervals_list_activities,
    intervals_list_events,
    intervals_list_folders,
    intervals_list_workouts,
    intervals_record_wellness,
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
