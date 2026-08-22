"""Coach MCP Server: FastMCP implementation for Intervals.icu endurance coaching."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from mcp.server.fastmcp import Context, FastMCP

from coach_mcp.client import IntervalsAPIError, IntervalsClient
from coach_mcp.config import settings
from coach_mcp.formatters import (
    format_activities_list,
    format_activity_detail,
    format_activity_streams,
    format_events_list,
    format_fitness_summary,
    format_folders,
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

# Configure logging to stderr to prevent stdout JSON-RPC corruption
logger = logging.getLogger("coach_mcp")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# Lifespan manager to manage persistent HTTP client
@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Initialize and teardown server dependencies."""
    logger.info("Initializing Coach MCP Server & Intervals.icu client...")
    client = IntervalsClient()
    try:
        yield {"client": client}
    finally:
        logger.info("Shutting down Coach MCP Server & closing client session...")
        await client.close()


# Initialize FastMCP Server
mcp = FastMCP(
    name="coach_mcp",
    lifespan=server_lifespan,
    dependencies=["httpx", "pydantic", "pydantic-settings"],
)


def _get_client_from_ctx(ctx: Context) -> IntervalsClient:
    """Retrieve the shared client from lifespan state if available, or create a new one."""
    try:
        if hasattr(ctx, "request_context") and ctx.request_context and hasattr(ctx.request_context, "lifespan_state"):
            client = ctx.request_context.lifespan_state.get("client")
            if client:
                return client
    except Exception:
        pass
    return IntervalsClient()


# ---------------------------------------------------------------------------
# Athlete Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_get_athlete_profile",
    annotations={
        "title": "Get Athlete Profile",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_get_athlete_profile(params: GetAthleteProfileInput, ctx: Context) -> str:
    """Retrieve athlete personal profile, resting HR, weight, and general settings from Intervals.icu."""
    client = _get_client_from_ctx(ctx)
    try:
        data = await client.get_athlete_profile(params.athlete_id)
        return format_profile(data, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error fetching athlete profile: {exc}"


@mcp.tool(
    name="intervals_get_sport_settings",
    annotations={
        "title": "Get Athlete Sport Settings & Zones",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_get_sport_settings(params: GetSportSettingsInput, ctx: Context) -> str:
    """Retrieve athlete sport settings including FTP, LTHR, Max HR, and power/heartrate training zones."""
    client = _get_client_from_ctx(ctx)
    try:
        data = await client.get_sport_settings(params.athlete_id)
        return format_sport_settings(data, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error fetching sport settings: {exc}"


# ---------------------------------------------------------------------------
# Activity Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_list_activities",
    annotations={
        "title": "List Athlete Activities",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_list_activities(params: ListActivitiesInput, ctx: Context) -> str:
    """List activities within a specific date range with duration, distance, average power, HR, and training load (TSS)."""
    client = _get_client_from_ctx(ctx)
    try:
        activities = await client.list_activities(
            oldest=params.oldest,
            newest=params.newest,
            athlete_id=params.athlete_id,
            limit=params.limit or 50,
        )
        return format_activities_list(activities, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error listing activities: {exc}"


@mcp.tool(
    name="intervals_get_activity",
    annotations={
        "title": "Get Activity Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_get_activity(params: GetActivityInput, ctx: Context) -> str:
    """Retrieve in-depth activity data: NP, IF, TSS, aerobic/anaerobic training effects, RPE, feel, and power curves."""
    client = _get_client_from_ctx(ctx)
    try:
        activity = await client.get_activity(params.activity_id)
        return format_activity_detail(activity, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error fetching activity '{params.activity_id}': {exc}"


@mcp.tool(
    name="intervals_get_activity_streams",
    annotations={
        "title": "Get Activity Time Series Streams",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_get_activity_streams(params: GetActivityStreamsInput, ctx: Context) -> str:
    """Retrieve second-by-second sensor streams (watts, heartrate, cadence, altitude, time, distance)."""
    client = _get_client_from_ctx(ctx)
    try:
        streams = await client.get_activity_streams(params.activity_id, params.types)
        return format_activity_streams(streams, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error fetching streams for activity '{params.activity_id}': {exc}"


@mcp.tool(
    name="intervals_get_activity_intervals",
    annotations={
        "title": "Get Activity Work Intervals",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_get_activity_intervals(params: GetActivityIntervalsInput, ctx: Context) -> str:
    """Retrieve detected work and recovery intervals with average power, HR, cadence, and duration."""
    client = _get_client_from_ctx(ctx)
    try:
        intervals_data = await client.get_activity_intervals(params.activity_id)
        return to_json_str(intervals_data)
    except IntervalsAPIError as exc:
        return f"Error fetching intervals for activity '{params.activity_id}': {exc}"


@mcp.tool(
    name="intervals_create_activity",
    annotations={
        "title": "Create Manual Activity",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
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
        return f"Error creating activity: {exc}"


@mcp.tool(
    name="intervals_update_activity",
    annotations={
        "title": "Update Activity Notes and RPE",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_update_activity(params: UpdateActivityInput, ctx: Context) -> str:
    """Update title, subjective feel (1-5), RPE (1-10), training load, or athlete notes on an existing activity."""
    client = _get_client_from_ctx(ctx)
    payload: Dict[str, Any] = {}
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
        return f"Error updating activity: {exc}"


@mcp.tool(
    name="intervals_delete_activity",
    annotations={
        "title": "Delete Activity",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_delete_activity(params: DeleteActivityInput, ctx: Context) -> str:
    """Permanently delete an activity from Intervals.icu."""
    client = _get_client_from_ctx(ctx)
    try:
        res = await client.delete_activity(params.activity_id)
        return f"Successfully deleted activity '{params.activity_id}': {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return f"Error deleting activity: {exc}"


# ---------------------------------------------------------------------------
# Wellness & Fitness Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_get_wellness",
    annotations={
        "title": "Get Wellness & Recovery History",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_get_wellness(params: GetWellnessInput, ctx: Context) -> str:
    """Retrieve daily resting HR, HRV (rMSSD), sleep duration/quality, subjective readiness, fatigue, and soreness."""
    client = _get_client_from_ctx(ctx)
    try:
        data = await client.get_wellness(oldest=params.oldest, newest=params.newest, athlete_id=params.athlete_id)
        return format_wellness_list(data, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error fetching wellness records: {exc}"


@mcp.tool(
    name="intervals_record_wellness",
    annotations={
        "title": "Record Daily Wellness & Recovery",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_record_wellness(params: RecordWellnessInput, ctx: Context) -> str:
    """Record or update daily wellness metrics (resting HR, HRV, sleep, readiness, fatigue, soreness, weight)."""
    client = _get_client_from_ctx(ctx)
    payload: Dict[str, Any] = {}
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
        return f"Error recording wellness: {exc}"


@mcp.tool(
    name="intervals_get_fitness_summary",
    annotations={
        "title": "Get Fitness, Fatigue & Form Summary (CTL/ATL/TSB)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_get_fitness_summary(params: GetFitnessSummaryInput, ctx: Context) -> str:
    """Calculate and summarize Chronic Training Load (CTL / Fitness), Acute Training Load (ATL / Fatigue), and Training Stress Balance (TSB / Form)."""
    client = _get_client_from_ctx(ctx)
    try:
        wellness_data = await client.get_wellness(
            oldest=params.oldest,
            newest=params.newest,
            athlete_id=params.athlete_id,
        )
        return format_fitness_summary(wellness_data, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error calculating fitness summary: {exc}"


# ---------------------------------------------------------------------------
# Planned Workouts & Events Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_list_events",
    annotations={
        "title": "List Scheduled Workouts & Calendar Events",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_list_events(params: ListEventsInput, ctx: Context) -> str:
    """List scheduled workouts, calendar notes, and race targets in a date range."""
    client = _get_client_from_ctx(ctx)
    try:
        events = await client.list_events(
            oldest=params.oldest,
            newest=params.newest,
            athlete_id=params.athlete_id,
            category=params.category,
        )
        return format_events_list(events, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error listing calendar events: {exc}"


@mcp.tool(
    name="intervals_get_event",
    annotations={
        "title": "Get Scheduled Event Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
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
        doc = event.get("workout_doc", "No structured definition")
        lines = [
            f"# Scheduled Workout: {name} (ID: {params.event_id})",
            f"- **Date**: {date_str}",
            f"- **Type**: {event.get('type', 'Ride')} | **Category**: {event.get('category', 'WORKOUT')}",
            f"- **Planned Load**: {event.get('icu_training_load', 'N/A')}",
            "",
            "## Structured Workout Steps (DSL)",
            "```",
            doc,
            "```",
        ]
        return "\n".join(lines)
    except IntervalsAPIError as exc:
        return f"Error fetching event '{params.event_id}': {exc}"


@mcp.tool(
    name="intervals_create_event",
    annotations={
        "title": "Schedule Planned Workout / Event",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def intervals_create_event(params: CreateEventInput, ctx: Context) -> str:
    """Schedule a new structured workout or calendar event using Intervals.icu workout DSL syntax."""
    client = _get_client_from_ctx(ctx)
    payload: Dict[str, Any] = {
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
        return f"Error scheduling event: {exc}"


@mcp.tool(
    name="intervals_update_event",
    annotations={
        "title": "Update Scheduled Workout / Event",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_update_event(params: UpdateEventInput, ctx: Context) -> str:
    """Update date, description, title, or structured workout steps on a scheduled event."""
    client = _get_client_from_ctx(ctx)
    payload: Dict[str, Any] = {}
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
        return f"Error updating event: {exc}"


@mcp.tool(
    name="intervals_delete_event",
    annotations={
        "title": "Delete Scheduled Event",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_delete_event(params: DeleteEventInput, ctx: Context) -> str:
    """Delete a scheduled workout or calendar event."""
    client = _get_client_from_ctx(ctx)
    try:
        res = await client.delete_event(params.event_id, athlete_id=params.athlete_id)
        return f"Successfully deleted event '{params.event_id}': {to_json_str(res)}"
    except IntervalsAPIError as exc:
        return f"Error deleting event: {exc}"


# ---------------------------------------------------------------------------
# Folders & Templates Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="intervals_list_folders",
    annotations={
        "title": "List Workout Library Folders",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_list_folders(params: ListFoldersInput, ctx: Context) -> str:
    """List custom folders organizing workout templates in the athlete library."""
    client = _get_client_from_ctx(ctx)
    try:
        folders = await client.list_folders(athlete_id=params.athlete_id)
        return format_folders(folders, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error listing folders: {exc}"


@mcp.tool(
    name="intervals_list_workouts",
    annotations={
        "title": "List Workout Templates in Library",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def intervals_list_workouts(params: ListWorkoutsInput, ctx: Context) -> str:
    """List reusable workout templates from the Intervals.icu library."""
    client = _get_client_from_ctx(ctx)
    try:
        workouts = await client.list_workouts(folder_id=params.folder_id, athlete_id=params.athlete_id)
        return format_workouts(workouts, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return f"Error listing workouts: {exc}"


def main() -> None:
    """Run Coach MCP Server in stdio or streamable_http transport mode."""
    if settings.mcp_transport in ("streamable_http", "sse"):
        logger.info(f"Starting Coach MCP Server on {settings.mcp_host}:{settings.mcp_port} ({settings.mcp_transport})...")
        mcp.run(transport=settings.mcp_transport, host=settings.mcp_host, port=settings.mcp_port)
    else:
        logger.info("Starting Coach MCP Server on stdio...")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
