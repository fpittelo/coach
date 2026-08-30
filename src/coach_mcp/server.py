"""Coach MCP Server: MCPServer implementation for Intervals.icu endurance coaching."""

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Any, Literal, cast

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from coach_mcp.client import IntervalsAPIError, IntervalsClient
from coach_mcp.config import settings
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
    ListActivitiesInput,
    ListEventsInput,
    ListFoldersInput,
    ListWorkoutsInput,
    RecordWellnessInput,
    ResponseFormat,
    UpdateActivityInput,
    UpdateEventInput,
)
from coach_mcp.security import redact_sensitive

# Configure logging to stderr to prevent stdout JSON-RPC corruption
logger = logging.getLogger("coach_mcp")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# Lifespan manager to manage persistent HTTP client
@asynccontextmanager
async def server_lifespan(server: MCPServer) -> AsyncIterator[dict[str, Any]]:
    """Initialize and teardown server dependencies."""
    logger.info("Initializing Coach MCP Server & Intervals.icu client...")
    client = IntervalsClient()
    try:
        yield {"client": client}
    finally:
        logger.info("Shutting down Coach MCP Server & closing client session...")
        await client.close()


# Initialize MCPServer
mcp = MCPServer(
    "Coach",
    lifespan=server_lifespan,
    dependencies=["httpx", "pydantic", "pydantic-settings"],
)


def _get_client_from_ctx(ctx: Context) -> IntervalsClient:
    """Retrieve the shared client from lifespan state if available, or create a new one."""
    try:
        if (
            hasattr(ctx, "request_context")
            and ctx.request_context
            and hasattr(ctx.request_context, "lifespan_state")
        ):
            client = ctx.request_context.lifespan_state.get("client")
            if client:
                return cast(IntervalsClient, client)
    except (AttributeError, KeyError, RuntimeError) as exc:
        logger.debug("Failed to retrieve client from context lifespan: %s", exc)
    return IntervalsClient()


def _format_event_workout_doc(event: dict[str, Any]) -> str:
    """Safely format the workout_doc / description payload as a string.

    Intervals.icu may return ``workout_doc`` as either a DSL string or a
    compiled JSON dict. ``description`` may also contain the DSL text. This
    helper coerces both representations into a safe string suitable for
    markdown output.
    """
    workout_doc = event.get("workout_doc")
    description = event.get("description")

    # Prefer a string workout_doc when available
    if isinstance(workout_doc, str) and workout_doc.strip():
        return workout_doc

    # Fall back to description if it contains DSL text
    if isinstance(description, str) and description.strip():
        return description

    # If workout_doc is a dict, pretty-print it as JSON
    if isinstance(workout_doc, dict):
        return to_json_str(workout_doc)

    # If description is a dict, pretty-print it as JSON
    if isinstance(description, dict):
        return to_json_str(description)

    # No usable content
    return "No structured definition available."


# ---------------------------------------------------------------------------
# Athlete Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_get_athlete_profile",
    annotations=ToolAnnotations(
        title="Get Athlete Profile",
        read_only_hint=True,
    ),
)
async def intervals_get_athlete_profile(params: GetAthleteProfileInput, ctx: Context) -> str:
    """Retrieve athlete profile, resting HR, weight, and general settings."""
    client = _get_client_from_ctx(ctx)
    try:
        data = await client.get_athlete_profile(params.athlete_id)
        return format_profile(data, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching athlete profile: {exc}") or ""


@mcp.tool(
    name="intervals_get_sport_settings",
    annotations=ToolAnnotations(
        title="Get Athlete Sport Settings & Zones",
        read_only_hint=True,
    ),
)
async def intervals_get_sport_settings(params: GetSportSettingsInput, ctx: Context) -> str:
    """Retrieve athlete sport settings: FTP, LTHR, Max HR, and power/HR zones."""
    client = _get_client_from_ctx(ctx)
    try:
        data = await client.get_sport_settings(params.athlete_id)
        return format_sport_settings(data, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching sport settings: {exc}") or ""


# ---------------------------------------------------------------------------
# Activity Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_list_activities",
    annotations=ToolAnnotations(
        title="List Athlete Activities",
        read_only_hint=True,
    ),
)
async def intervals_list_activities(params: ListActivitiesInput, ctx: Context) -> str:
    """List activities in a date range with duration, distance, power, HR, and TSS."""
    client = _get_client_from_ctx(ctx)
    try:
        activities = await client.list_activities(
            oldest=cast(str, params.oldest),
            newest=cast(str, params.newest),
            athlete_id=params.athlete_id,
            limit=params.limit or 50,
        )
        return format_activities_list(
            activities, fmt_json=(params.response_format == ResponseFormat.JSON)
        )
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error listing activities: {exc}") or ""


@mcp.tool(
    name="intervals_get_activity",
    annotations=ToolAnnotations(
        title="Get Activity Details",
        read_only_hint=True,
    ),
)
async def intervals_get_activity(params: GetActivityInput, ctx: Context) -> str:
    """Retrieve detailed activity data: NP, IF, TSS, training effects, RPE, feel."""
    client = _get_client_from_ctx(ctx)
    try:
        activity = await client.get_activity(params.activity_id)
        return format_activity_detail(
            activity, fmt_json=(params.response_format == ResponseFormat.JSON)
        )
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching activity '{params.activity_id}': {exc}") or ""


@mcp.tool(
    name="intervals_get_activity_streams",
    annotations=ToolAnnotations(
        title="Get Activity Time Series Streams",
        read_only_hint=True,
    ),
)
async def intervals_get_activity_streams(params: GetActivityStreamsInput, ctx: Context) -> str:
    """Retrieve second-by-second sensor streams: watts, HR, cadence, altitude, time, distance."""
    client = _get_client_from_ctx(ctx)
    try:
        streams = await client.get_activity_streams(params.activity_id, params.types)
        return format_activity_streams(
            streams, fmt_json=(params.response_format == ResponseFormat.JSON)
        )
    except IntervalsAPIError as exc:
        return (
            redact_sensitive(f"Error fetching streams for activity '{params.activity_id}': {exc}")
            or ""
        )


@mcp.tool(
    name="intervals_get_activity_intervals",
    annotations=ToolAnnotations(
        title="Get Activity Work Intervals",
        read_only_hint=True,
    ),
)
async def intervals_get_activity_intervals(params: GetActivityIntervalsInput, ctx: Context) -> str:
    """Retrieve detected work and recovery intervals with power, HR, cadence, and duration."""
    client = _get_client_from_ctx(ctx)
    try:
        intervals_data = await client.get_activity_intervals(params.activity_id)
        return to_json_str(intervals_data)
    except IntervalsAPIError as exc:
        return (
            redact_sensitive(f"Error fetching intervals for activity '{params.activity_id}': {exc}")
            or ""
        )


@mcp.tool(
    name="intervals_get_power_curve",
    annotations=ToolAnnotations(
        title="Get Power Curve",
        read_only_hint=True,
    ),
)
async def intervals_get_power_curve(params: GetPowerCurveInput, ctx: Context) -> str:
    """Retrieve mean-maximal power (MMP) curve for an athlete or a specific activity."""
    client = _get_client_from_ctx(ctx)
    try:
        if params.activity_id:
            data = await client.get_activity_power_curve(params.activity_id)
        else:
            data = await client.get_power_curve(params.athlete_id, params.sport_type)
        return format_power_curve(data, response_format=params.response_format)
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching power curve: {exc}") or ""


@mcp.tool(
    name="intervals_get_power_model",
    annotations=ToolAnnotations(
        title="Get Athlete Power Model (CP/W')",
        read_only_hint=True,
    ),
)
async def intervals_get_power_model(params: GetPowerModelInput, ctx: Context) -> str:
    """Retrieve athlete critical power (CP), anaerobic work capacity (W'), and Pmax model."""
    client = _get_client_from_ctx(ctx)
    try:
        data = await client.get_power_model(params.athlete_id, params.sport_type)
        return format_power_model(data, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching power model: {exc}") or ""


@mcp.tool(
    name="intervals_create_activity",
    annotations=ToolAnnotations(
        title="Create Manual Activity",
        read_only_hint=False,
        idempotent_hint=False,
    ),
)
async def intervals_create_activity(params: CreateActivityInput, ctx: Context) -> str:
    """Manually record a completed workout or activity on Intervals.icu."""
    client = _get_client_from_ctx(ctx)
    payload = {
        "name": params.name,
        "type": params.type,
        "start_date_local": params.start_date_local,
        "moving_time": params.moving_time_seconds,
        "elapsed_time": params.elapsed_time_seconds or params.moving_time_seconds,
    }
    if params.distance_meters is not None:
        payload["distance"] = params.distance_meters
    if params.average_watts is not None:
        payload["average_watts"] = params.average_watts
    if params.average_heartrate is not None:
        payload["average_heartrate"] = params.average_heartrate
    if params.icu_training_load is not None:
        payload["icu_training_load"] = params.icu_training_load
    if params.description:
        payload["description"] = params.description

    try:
        res = await client.create_activity(payload, athlete_id=params.athlete_id)
        return f"Successfully created activity: {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error creating activity: {exc}") or ""


@mcp.tool(
    name="intervals_update_activity",
    annotations=ToolAnnotations(
        title="Update Activity Notes and RPE",
        read_only_hint=False,
        idempotent_hint=False,
    ),
)
async def intervals_update_activity(params: UpdateActivityInput, ctx: Context) -> str:
    """Update activity title, feel (1-5), RPE (1-10), training load, or notes."""
    client = _get_client_from_ctx(ctx)
    payload: dict[str, Any] = {}
    if params.name:
        payload["name"] = params.name
    if params.description is not None:
        payload["description"] = params.description
    if params.perceived_exertion is not None:
        payload["perceived_exertion"] = params.perceived_exertion
    if params.feel is not None:
        payload["feel"] = params.feel
    if params.icu_training_load is not None:
        payload["icu_training_load"] = params.icu_training_load

    try:
        res = await client.update_activity(params.activity_id, payload)
        return f"Successfully updated activity '{params.activity_id}': {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error updating activity: {exc}") or ""


@mcp.tool(
    name="intervals_delete_activity",
    annotations=ToolAnnotations(
        title="Delete Activity",
        read_only_hint=False,
        destructive_hint=True,
    ),
)
async def intervals_delete_activity(params: DeleteActivityInput, ctx: Context) -> str:
    """Permanently delete an activity from Intervals.icu."""
    client = _get_client_from_ctx(ctx)
    try:
        res = await client.delete_activity(params.activity_id)
        return f"Successfully deleted activity '{params.activity_id}': {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error deleting activity: {exc}") or ""


# ---------------------------------------------------------------------------
# Wellness & Fitness Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_get_wellness",
    annotations=ToolAnnotations(
        title="Get Wellness & Recovery History",
        read_only_hint=True,
    ),
)
async def intervals_get_wellness(params: GetWellnessInput, ctx: Context) -> str:
    """Retrieve daily wellness: resting HR, HRV, sleep, readiness, fatigue, and soreness."""
    client = _get_client_from_ctx(ctx)
    try:
        data = await client.get_wellness(
            oldest=cast(str, params.oldest),
            newest=cast(str, params.newest),
            athlete_id=params.athlete_id,
        )
        return format_wellness_list(data, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching wellness records: {exc}") or ""


@mcp.tool(
    name="intervals_record_wellness",
    annotations=ToolAnnotations(
        title="Record Daily Wellness & Recovery",
        read_only_hint=False,
        idempotent_hint=False,
    ),
)
async def intervals_record_wellness(params: RecordWellnessInput, ctx: Context) -> str:
    """Record or update daily wellness metrics: HR, HRV, sleep, readiness, fatigue, weight."""
    client = _get_client_from_ctx(ctx)
    payload: dict[str, Any] = {}
    for key in (
        "restingHR",
        "hrv",
        "weight",
        "sleepSecs",
        "sleepQuality",
        "readiness",
        "soreness",
        "fatigue",
        "stress",
        "mood",
        "injury",
        "comments",
    ):
        val = getattr(params, key)
        if val is not None:
            payload[key] = val

    try:
        res = await client.record_wellness(params.date, payload, athlete_id=params.athlete_id)
        return f"Successfully recorded wellness for {params.date}: {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error recording wellness: {exc}") or ""


@mcp.tool(
    name="intervals_get_fitness_summary",
    annotations=ToolAnnotations(
        title="Get Fitness, Fatigue & Form Summary (CTL/ATL/TSB)",
        read_only_hint=True,
    ),
)
async def intervals_get_fitness_summary(params: GetFitnessSummaryInput, ctx: Context) -> str:
    """Calculate and summarize CTL (Fitness), ATL (Fatigue), and TSB (Form)."""
    client = _get_client_from_ctx(ctx)
    try:
        wellness_data = await client.get_wellness(
            oldest=cast(str, params.oldest),
            newest=cast(str, params.newest),
            athlete_id=params.athlete_id,
        )
        return format_fitness_summary(
            wellness_data, fmt_json=(params.response_format == ResponseFormat.JSON)
        )
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error calculating fitness summary: {exc}") or ""


@mcp.tool(
    name="intervals_get_readiness_dashboard",
    annotations=ToolAnnotations(
        title="Get Daily Readiness & Training Dashboard",
        read_only_hint=True,
    ),
)
async def intervals_get_readiness_dashboard(
    params: GetReadinessDashboardInput, ctx: Context
) -> str:
    """Fetch wellness and sport settings and synthesize a single readiness dashboard."""
    client = _get_client_from_ctx(ctx)
    try:
        oldest = (date.today() - timedelta(days=params.days - 1)).isoformat()
        newest = date.today().isoformat()
        wellness_data, sport_settings = await asyncio.gather(
            client.get_wellness(oldest=oldest, newest=newest, athlete_id=params.athlete_id),
            client.get_sport_settings(athlete_id=params.athlete_id),
        )
        return format_readiness_dashboard(
            wellness_data,
            sport_settings,
            fmt_json=(params.response_format == ResponseFormat.JSON),
        )
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching readiness dashboard: {exc}") or ""
    except Exception as exc:  # noqa: BLE001
        return redact_sensitive(f"Error fetching readiness dashboard: {exc}") or ""


# ---------------------------------------------------------------------------
# Planned Workouts & Events Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_list_events",
    annotations=ToolAnnotations(
        title="List Scheduled Workouts & Calendar Events",
        read_only_hint=True,
    ),
)
async def intervals_list_events(params: ListEventsInput, ctx: Context) -> str:
    """List scheduled workouts, calendar notes, and race targets in a date range."""
    client = _get_client_from_ctx(ctx)
    try:
        events = await client.list_events(
            oldest=cast(str, params.oldest),
            newest=cast(str, params.newest),
            athlete_id=params.athlete_id,
            category=params.category,
        )
        return format_events_list(events, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error listing calendar events: {exc}") or ""


@mcp.tool(
    name="intervals_get_event",
    annotations=ToolAnnotations(
        title="Get Scheduled Event Details",
        read_only_hint=True,
    ),
)
async def intervals_get_event(params: GetEventInput, ctx: Context) -> str:
    """Retrieve complete details and workout DSL definition of a scheduled workout event."""
    client = _get_client_from_ctx(ctx)
    try:
        event = await client.get_event(params.event_id)
        if params.response_format == ResponseFormat.JSON:
            return to_json_str(event)
        name = event.get("name", "Untitled")
        date_str = event.get("start_date_local", "N/A")
        doc = _format_event_workout_doc(event)
        lines = [
            f"# Scheduled Workout: {name} (ID: {params.event_id})",
            f"- **Date**: {date_str}",
            f"- **Type**: {event.get('type', 'Ride')} | "
            f"**Category**: {event.get('category', 'WORKOUT')}",
            f"- **Planned Load**: {event.get('icu_training_load', 'N/A')}",
            "",
            "## Structured Workout Steps (DSL)",
            "```",
            doc,
            "```",
        ]
        return "\n".join(lines)
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching event '{params.event_id}': {exc}") or ""
    except TypeError as exc:
        msg = f"Error formatting event '{params.event_id}': unexpected response type ({exc})"
        return redact_sensitive(msg) or ""
    except Exception as exc:  # noqa: BLE001
        return redact_sensitive(f"Error formatting event '{params.event_id}': {exc}") or ""


@mcp.tool(
    name="intervals_create_event",
    annotations=ToolAnnotations(
        title="Schedule Planned Workout / Event",
        read_only_hint=False,
        idempotent_hint=False,
    ),
)
async def intervals_create_event(params: CreateEventInput, ctx: Context) -> str:
    """Schedule a new structured workout or calendar event using workout DSL syntax."""
    client = _get_client_from_ctx(ctx)
    payload: dict[str, Any] = {
        "start_date_local": params.start_date_local,
        "name": params.name,
        "type": params.type,
        "category": params.category,
    }
    if params.description:
        payload["description"] = params.description
    if params.workout_doc:
        payload["workout_doc"] = params.workout_doc
    if params.moving_time_seconds:
        payload["moving_time"] = params.moving_time_seconds
    if params.icu_training_load is not None:
        payload["icu_training_load"] = params.icu_training_load

    try:
        res = await client.create_event(payload, athlete_id=params.athlete_id)
        return f"Successfully scheduled event '{params.name}': {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error scheduling event: {exc}") or ""


@mcp.tool(
    name="intervals_update_event",
    annotations=ToolAnnotations(
        title="Update Scheduled Workout / Event",
        read_only_hint=False,
        idempotent_hint=False,
    ),
)
async def intervals_update_event(params: UpdateEventInput, ctx: Context) -> str:
    """Update date, description, title, or structured workout steps on a scheduled event."""
    client = _get_client_from_ctx(ctx)
    payload: dict[str, Any] = {}
    if params.start_date_local:
        payload["start_date_local"] = params.start_date_local
    if params.name:
        payload["name"] = params.name
    if params.description is not None:
        payload["description"] = params.description
    if params.workout_doc is not None:
        payload["workout_doc"] = params.workout_doc
    if params.moving_time_seconds:
        payload["moving_time"] = params.moving_time_seconds
    if params.icu_training_load is not None:
        payload["icu_training_load"] = params.icu_training_load

    try:
        res = await client.update_event(params.event_id, payload, athlete_id=params.athlete_id)
        return f"Successfully updated event '{params.event_id}': {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error updating event: {exc}") or ""


@mcp.tool(
    name="intervals_delete_event",
    annotations=ToolAnnotations(
        title="Delete Scheduled Event",
        read_only_hint=False,
        destructive_hint=True,
    ),
)
async def intervals_delete_event(params: DeleteEventInput, ctx: Context) -> str:
    """Delete a scheduled workout or calendar event."""
    client = _get_client_from_ctx(ctx)
    try:
        res = await client.delete_event(params.event_id, athlete_id=params.athlete_id)
        return f"Successfully deleted event '{params.event_id}': {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error deleting event: {exc}") or ""


# ---------------------------------------------------------------------------
# Folders & Templates Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_list_folders",
    annotations=ToolAnnotations(
        title="List Workout Library Folders",
        read_only_hint=True,
    ),
)
async def intervals_list_folders(params: ListFoldersInput, ctx: Context) -> str:
    """List custom folders organizing workout templates in the athlete library."""
    client = _get_client_from_ctx(ctx)
    try:
        folders = await client.list_folders(athlete_id=params.athlete_id)
        return format_folders(folders, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error listing folders: {exc}") or ""


@mcp.tool(
    name="intervals_list_workouts",
    annotations=ToolAnnotations(
        title="List Workout Templates in Library",
        read_only_hint=True,
    ),
)
async def intervals_list_workouts(params: ListWorkoutsInput, ctx: Context) -> str:
    """List reusable workout templates from the Intervals.icu library."""
    client = _get_client_from_ctx(ctx)
    try:
        workouts = await client.list_workouts(
            folder_id=params.folder_id, athlete_id=params.athlete_id
        )
        return format_workouts(workouts, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error listing workouts: {exc}") or ""


def main() -> None:
    """Run Coach MCP Server in stdio or streamable-http transport mode."""
    transport = cast(
        Literal["stdio", "streamable-http", "sse"],
        settings.mcp_transport.replace("_", "-"),
    )
    if transport in ("streamable-http", "sse"):
        logger.info(
            f"Starting Coach MCP Server on {settings.mcp_host}:{settings.mcp_port} ({transport})..."
        )
        mcp.run(transport=transport, host=settings.mcp_host, port=settings.mcp_port)
    else:
        logger.info("Starting Coach MCP Server on stdio...")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
