"""Coach MCP Server: MCPServer implementation for Intervals.icu endurance coaching."""

import asyncio
import hashlib
import json
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Any, Literal, cast

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from coach_mcp.audit import audit_tool_call, emit_tool_batch_outcome
from coach_mcp.client import IntervalsAPIError, IntervalsClient
from coach_mcp.config import settings
from coach_mcp.formatters import (
    format_activities_list,
    format_activity_detail,
    format_activity_streams,
    format_completed_sessions,
    format_events_list,
    format_fitness_summary,
    format_folders,
    format_icu_wellness,
    format_power_curve,
    format_power_model,
    format_profile,
    format_readiness_dashboard,
    format_sport_settings,
    format_trend_report,
    format_wellness_list,
    format_workout_compliance,
    format_workouts,
    to_json_str,
)
from coach_mcp.models import (
    ICU_EVENT_DEFAULT_START_TIME,
    CompletedSessionsPage,
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
    IcuBatchEventOutcome,
    IcuEventDraft,
    IcuGetCompletedSessionsInput,
    IcuGetTrendsInput,
    IcuGetWellnessInput,
    IcuGetWorkoutComplianceInput,
    ListActivitiesInput,
    ListEventsInput,
    ListFoldersInput,
    ListWorkoutsInput,
    RecordWellnessBulkInput,
    RecordWellnessInput,
    ResponseFormat,
    UpdateActivityInput,
    UpdateEventInput,
    build_trend_report,
    build_workout_compliance_report,
    project_completed_sessions,
    project_wellness_days,
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
    name="intervals_record_wellness_bulk",
    annotations=ToolAnnotations(
        title="Record Bulk Daily Wellness & Recovery",
        read_only_hint=False,
        idempotent_hint=False,
    ),
)
@audit_tool_call
async def intervals_record_wellness_bulk(params: RecordWellnessBulkInput, ctx: Context) -> str:
    """Record daily wellness metrics for multiple days in a single API call.

    Days managed by connected sync providers (Oura/Garmin/Polar) may be
    reverted on the next re-sync.
    """
    client = _get_client_from_ctx(ctx)
    records_payload: list[dict[str, Any]] = []
    for r in params.records:
        item: dict[str, Any] = {"date": r.date}
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
            val = getattr(r, key)
            if val is not None:
                item[key] = val
        records_payload.append(item)

    try:
        res = await client.record_wellness_bulk(records_payload, athlete_id=params.athlete_id)
        return (
            f"Successfully recorded bulk wellness for {len(params.records)} day(s): "
            f"{to_json_str(res)}"
        )
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error recording bulk wellness: {exc}") or ""


@mcp.tool(
    name="intervals_get_fitness_summary",
    annotations=ToolAnnotations(
        title="Get Fitness, Fatigue & Form Summary (CTL/ATL/TSB)",
        read_only_hint=True,
    ),
)
@audit_tool_call
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
@audit_tool_call
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
# ICU Bounded Read Tools (Epic #82)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="icu_get_wellness",
    annotations=ToolAnnotations(
        title="Get Bounded Wellness History (Health-Field Whitelist)",
        read_only_hint=True,
    ),
)
@audit_tool_call
async def icu_get_wellness(params: IcuGetWellnessInput, ctx: Context) -> str:
    """Read daily wellness records bounded to a 90-day window, whitelist-projected.

    Serves coach-web Epic 3/4 (debrief context, longitudinal trends). The
    date range is clamped server-side to at most 90 days (binding security
    condition 1) and the response exposes only the whitelisted health fields
    — sleep, HRV, soreness, fatigue, stress, readiness, CTL, ATL, and TSB
    derived as CTL - ATL (binding security condition 2). The raw
    Intervals.icu payload is never passed through: weight, resting HR, mood,
    injury, free-text comments, and provider measurements are dropped by the
    projection.

    Args:
        params (IcuGetWellnessInput): Validated date range (defaults to the
            last 30 days), optional athlete ID, and output format.
        ctx (Context): MCP request context carrying the shared client.

    Returns:
        str: Markdown table or JSON array of whitelisted daily projections.
    """
    client = _get_client_from_ctx(ctx)
    try:
        raw_records = await client.get_wellness(
            oldest=cast(str, params.oldest),
            newest=cast(str, params.newest),
            athlete_id=params.athlete_id,
        )
        projected = project_wellness_days(raw_records)
        return format_icu_wellness(
            projected, fmt_json=(params.response_format == ResponseFormat.JSON)
        )
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching bounded wellness records: {exc}") or ""
    except Exception as exc:  # noqa: BLE001
        return redact_sensitive(f"Error fetching bounded wellness records: {exc}") or ""


@mcp.tool(
    name="icu_add_session_comment",
    annotations=ToolAnnotations(
        title="Add Session Debrief Comment",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
    ),
)
@audit_tool_call
async def icu_add_session_comment(params: IcuAddSessionCommentInput, ctx: Context) -> str:
    """Post a debrief summary comment on a completed Intervals.icu activity.

    Serves coach-web Story 3.1 (debrief persistence): structured debrief data
    lives in coach-web's Fernet-encrypted DB; the Intervals.icu comment is the
    athlete-visible mirror.

    Contract (epic #82 binding security conditions 1, 3, 4):

    * **Confirmation gate** — the write is rejected server-side unless
      ``confirmed=True`` (mirror of coach-web's plan-approval gate); the
      rejection is audited as a failed write.
    * **Validated content only** — the comment must be server-generated from
      validated debrief data; this tool is never a raw-LLM passthrough
      channel. Text is sanitized (script/style blocks and HTML tags stripped,
      control characters removed) and hard-capped at 2000 characters at
      validation.
    * **Audit** — every invocation (success or failure) emits a structured
      audit record with secret redaction via the #64 hook.

    Args:
        params (IcuAddSessionCommentInput): Activity ID, sanitized comment
            body (<=2000 chars), and the explicit confirmation flag.
        ctx (Context): MCP request context carrying the shared client.

    Returns:
        str: Success message with the created message payload, or a handled
        ``Error ...`` string (audited at ERROR level).
    """
    client = _get_client_from_ctx(ctx)
    if not params.confirmed:
        return (
            "Error: session comment rejected — explicit confirmation is required "
            "for this write (set confirmed=true once the debrief payload has been "
            "human-approved)."
        )
    try:
        res = await client.add_activity_message(params.activity_id, params.comment)
        return (
            f"Successfully posted session comment on activity "
            f"'{params.activity_id}': {to_json_str(res)}"
        )
    except IntervalsAPIError as exc:
        return (
            redact_sensitive(
                f"Error posting session comment on activity '{params.activity_id}': {exc}"
            )
            or ""
        )


# ---------------------------------------------------------------------------
# ICU Batch Event Tools (#94)
# ---------------------------------------------------------------------------


def _build_batch_event_payload(draft: IcuEventDraft) -> dict[str, Any]:
    """Normalize one event draft into an Intervals.icu ``EventEx`` payload.

    The draft's calendar date is pinned to :data:`ICU_EVENT_DEFAULT_START_TIME`
    local time so the normalized payload (and therefore the confirmation token
    derived from it) is deterministic across the preview and execute phases.
    The workout DSL text is delivered via the ``description`` field exactly
    like the single-event tools (the API parses the DSL from the description).
    """
    payload: dict[str, Any] = {
        "external_id": draft.external_id,
        "start_date_local": f"{draft.date}T{ICU_EVENT_DEFAULT_START_TIME}",
        "name": draft.name,
        "type": draft.type,
        "category": draft.category,
    }
    description = draft.description
    if draft.workout_doc:
        description = f"{description}\n\n{draft.workout_doc}" if description else draft.workout_doc
    if description:
        payload["description"] = description
    if draft.moving_time_seconds is not None:
        payload["moving_time"] = draft.moving_time_seconds
    if draft.icu_training_load is not None:
        payload["icu_training_load"] = draft.icu_training_load
    return payload


def _derive_batch_confirm_token(payloads: list[dict[str, Any]]) -> str:
    """Derive the confirmation token fingerprinting the exact batch payload.

    The token is a SHA-256 prefix over the canonical JSON serialization of the
    normalized payloads. It is a payload fingerprint, not a secret: execution
    is only accepted when the caller re-supplies the token of the exact batch
    it previewed, so any draft change between preview and execute invalidates
    the confirmation.
    """
    canonical = json.dumps(payloads, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _format_batch_preview(
    params: IcuBatchCreateEventsInput,
    payloads: list[dict[str, Any]],
    token: str,
) -> str:
    """Render the dry-run preview: normalized payload summary + confirm token."""
    if params.response_format == ResponseFormat.JSON:
        return to_json_str(
            {
                "phase": "preview",
                "item_count": len(payloads),
                "confirm_token": token,
                "events": payloads,
                "note": "Re-invoke with confirm_token to place these events.",
            }
        )

    dates = [draft.date for draft in params.events]
    lines = [
        "# Batch Event Preview (dry-run — nothing written)",
        "",
        f"- **Items**: {len(payloads)}",
        f"- **Date span**: {min(dates)} → {max(dates)}",
        f"- **Confirmation token**: `{token}`",
        "",
        "| # | external_id | date | title | type | category |",
        "|---|-------------|------|-------|------|----------|",
    ]
    for idx, draft in enumerate(params.events, start=1):
        lines.append(
            f"| {idx} | {draft.external_id} | {draft.date} | {draft.name} "
            f"| {draft.type} | {draft.category} |"
        )
    lines.extend(
        [
            "",
            "Re-invoke with the same events and `confirm_token` set to the token above",
            "to place these events on the calendar. Execution requires the exact token",
            "derived from this preview.",
        ]
    )
    return "\n".join(lines)


def _format_batch_outcomes(
    params: IcuBatchCreateEventsInput,
    outcomes: list[IcuBatchEventOutcome],
) -> str:
    """Render the per-item outcome report (no-rollback semantics made visible)."""
    created = sum(1 for o in outcomes if o.outcome == "created")
    updated = sum(1 for o in outcomes if o.outcome == "updated")
    failed = sum(1 for o in outcomes if o.outcome == "failed")
    if params.response_format == ResponseFormat.JSON:
        return to_json_str(
            {
                "created": created,
                "updated": updated,
                "failed": failed,
                "outcomes": [o.model_dump() for o in outcomes],
            }
        )

    lines = [
        "# Batch Event Upsert Report",
        "",
        f"- **Created**: {created} | **Updated**: {updated} | **Failed**: {failed}",
        "",
        "No rollback: failed items leave no partial state changes behind;",
        "re-run the same batch (same external_ids) to retry failed items.",
        "",
        "| external_id | outcome | event_id | reason |",
        "|--------------|---------|----------|--------|",
    ]
    for outcome in outcomes:
        lines.append(
            f"| {outcome.external_id} | {outcome.outcome} | {outcome.event_id or '-'} "
            f"| {outcome.reason or '-'} |"
        )
    return "\n".join(lines)


@mcp.tool(
    name="icu_batch_create_events",
    annotations=ToolAnnotations(
        title="Batch Place Planned Workouts (Upsert)",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
    ),
)
@audit_tool_call
async def icu_batch_create_events(params: IcuBatchCreateEventsInput, ctx: Context) -> str:
    """Place a weekly batch of planned workouts on the Intervals.icu calendar.

    Two-phase confirmation gate (epic #82 binding security condition 2):

    * **Preview (dry-run)** — invoke without ``confirm_token``: the batch is
      validated and normalized (titles/descriptions sanitized, dates pinned
      to a default local start time) and a confirmation token derived from
      the exact normalized payload is returned. Nothing is written.
    * **Execute** — re-invoke with the same events and ``confirm_token`` set
      to the previewed token. A token mismatch (payload changed since the
      preview) is rejected before any network call.

    Upsert semantics: each draft carries a caller-supplied ``external_id``;
    re-submitting the same week upserts (updates) existing events instead of
    duplicating them. The upstream API has no rollback: the per-item outcome
    report (created / updated / failed + reason) makes partial success
    visible, never silent.

    Batch bound: at most 50 drafts per call, enforced at validation before
    any network call.

    Args:
        params (IcuBatchCreateEventsInput): Event drafts (1-50), optional
            athlete ID, optional confirmation token, and output format.
        ctx (Context): MCP request context carrying the shared client.

    Returns:
        str: Preview (dry-run) with the confirmation token, or the per-item
        outcome report, or a handled ``Error ...`` string (audited at ERROR).
    """
    client = _get_client_from_ctx(ctx)
    payloads = [_build_batch_event_payload(draft) for draft in params.events]
    token = _derive_batch_confirm_token(payloads)

    if params.confirm_token is None:
        return _format_batch_preview(params, payloads, token)

    if params.confirm_token != token:
        return (
            "Error: batch event upsert rejected — confirmation token mismatch "
            "(the payload changed since the preview or the token is invalid; "
            "re-run the preview and confirm the new token)."
        )

    try:
        oldest = min(draft.date for draft in params.events)
        newest = max(draft.date for draft in params.events)
        existing = await client.list_events(
            oldest=oldest, newest=newest, athlete_id=params.athlete_id
        )
        existing_external_ids = {
            str(event["external_id"])
            for event in existing
            if isinstance(event, dict) and event.get("external_id")
        }

        results = await client.bulk_create_events(payloads, athlete_id=params.athlete_id)
        if not isinstance(results, list):
            raise IntervalsAPIError("Unexpected response shape from events/bulk (expected a list)")
        returned_by_external_id = {
            str(row["external_id"]): row
            for row in results
            if isinstance(row, dict) and row.get("external_id")
        }

        outcomes: list[IcuBatchEventOutcome] = []
        for draft in params.events:
            row = returned_by_external_id.get(draft.external_id)
            if row is None:
                outcomes.append(
                    IcuBatchEventOutcome(
                        external_id=draft.external_id,
                        outcome="failed",
                        reason="missing from Intervals.icu response",
                    )
                )
            else:
                outcomes.append(
                    IcuBatchEventOutcome(
                        external_id=draft.external_id,
                        outcome=(
                            "updated" if draft.external_id in existing_external_ids else "created"
                        ),
                        event_id=str(row["id"]) if row.get("id") is not None else None,
                    )
                )
        emit_tool_batch_outcome(
            tool="icu_batch_create_events",
            outcomes=[outcome.model_dump() for outcome in outcomes],
            status="success" if all(o.outcome != "failed" for o in outcomes) else "error",
        )
        return _format_batch_outcomes(params, outcomes)
    except IntervalsAPIError as exc:
        reason = redact_sensitive(str(exc)) or "upstream error"
        emit_tool_batch_outcome(
            tool="icu_batch_create_events",
            outcomes=[
                {
                    "external_id": draft.external_id,
                    "outcome": "failed",
                    "event_id": None,
                    "reason": reason,
                }
                for draft in params.events
            ],
            status="error",
        )
        return redact_sensitive(f"Error placing batch events: {exc}") or ""


# ---------------------------------------------------------------------------
# ICU Workout Compliance Tools (#95)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="icu_get_workout_compliance",
    annotations=ToolAnnotations(
        title="Get Workout Compliance (Planned vs Executed)",
        read_only_hint=True,
    ),
)
@audit_tool_call
async def icu_get_workout_compliance(params: IcuGetWorkoutComplianceInput, ctx: Context) -> str:
    """Compare planned calendar workouts against executed activities over a bounded range.

    Serves coach-web Story 3.2 (weekly debrief adherence). The join is the
    native Intervals.icu link: an executed activity carries ``paired_event_id``
    pointing at its planned calendar event, plus ICU's own ``compliance``
    adherence score — the join is by ID, never by date or title heuristics.

    Exactly two GETs are issued per call (epic #82 binding condition 5), in
    parallel: the planned events list and the executed activities list over
    the requested range. The date range is bounded server-side to at most
    90 days (binding condition 1) — wider ranges are rejected with an
    explicit validation error before any network call.

    The response is a whitelist-only projection: per-event adherence
    classification (completed / missed / upcoming), the native compliance
    score, and a per-interval structure diff of the planned ``workout_doc``
    against the executed interval data — never a raw activity payload dump.

    Args:
        params (IcuGetWorkoutComplianceInput): Validated date range (defaults
            to the last 7 days), optional athlete ID, and output format.
        ctx (Context): MCP request context carrying the shared client.

    Returns:
        str: Markdown report with a plain-language adherence summary and a
        per-event table, or the JSON report model, or a handled ``Error ...``
        string (audited at ERROR level).
    """
    client = _get_client_from_ctx(ctx)
    oldest = cast(str, params.oldest)
    newest = cast(str, params.newest)
    try:
        events, activities = await asyncio.gather(
            client.list_events(oldest=oldest, newest=newest, athlete_id=params.athlete_id),
            client.list_activities(
                oldest=oldest, newest=newest, athlete_id=params.athlete_id, limit=100
            ),
        )
        report = build_workout_compliance_report(oldest, newest, events, activities)
        return format_workout_compliance(
            report, fmt_json=(params.response_format == ResponseFormat.JSON)
        )
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching workout compliance: {exc}") or ""
    except Exception as exc:  # noqa: BLE001
        return redact_sensitive(f"Error fetching workout compliance: {exc}") or ""


# ---------------------------------------------------------------------------
# ICU Completed Sessions Tools (#96)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="icu_get_completed_sessions",
    annotations=ToolAnnotations(
        title="Get Completed Sessions (Bounded Activity Listing)",
        read_only_hint=True,
    ),
)
@audit_tool_call
async def icu_get_completed_sessions(params: IcuGetCompletedSessionsInput, ctx: Context) -> str:
    """List the athlete's completed sessions over a bounded date range.

    Serves coach-web #164 (debrief greeting source): completed sessions the
    coach can reference in debrief conversations, as structured data instead
    of memory. Read-only.

    Exactly one GET is issued per call against the verified Intervals.icu
    endpoint ``GET /api/v1/athlete/{id}/activities`` (official OpenAPI spec,
    operation ``listActivities``; query params ``oldest``, ``newest``,
    ``limit``). The date range is bounded server-side to at most 90 days
    (epic #82 binding condition 1) — wider ranges are rejected with an
    explicit validation error before any network call.

    The response is a whitelist-only projection: id, date, type, title,
    duration, and ICU-provided load/TSS — never a raw activity payload dump
    (no health or biometric values). The page size is capped (1-100) both on
    the upstream fetch and on the returned page; the optional strict
    activity-type filter narrows within the fetched page (the ICU activities
    endpoint has no server-side type parameter).

    Args:
        params (IcuGetCompletedSessionsInput): Validated date range (defaults
            to the last 7 days), optional athlete ID, optional strict
            activity-type filter, page-size cap, and output format.
        ctx (Context): MCP request context carrying the shared client.

    Returns:
        str: Markdown listing with a plain-language page summary, or the JSON
        page model, or a handled ``Error ...`` string (audited at ERROR level).
    """
    client = _get_client_from_ctx(ctx)
    oldest = cast(str, params.oldest)
    newest = cast(str, params.newest)
    try:
        activities = await client.list_activities(
            oldest=oldest,
            newest=newest,
            athlete_id=params.athlete_id,
            limit=params.limit,
        )
        projected = project_completed_sessions(activities, activity_type=params.activity_type)
        page_sessions = projected[: params.limit]
        page = CompletedSessionsPage(
            oldest=oldest,
            newest=newest,
            activity_type=(
                params.activity_type.value if params.activity_type is not None else None
            ),
            fetched=len(activities),
            returned=len(page_sessions),
            sessions=page_sessions,
        )
        return format_completed_sessions(
            page, fmt_json=(params.response_format == ResponseFormat.JSON)
        )
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching completed sessions: {exc}") or ""
    except Exception as exc:  # noqa: BLE001
        return redact_sensitive(f"Error fetching completed sessions: {exc}") or ""


# ---------------------------------------------------------------------------
# ICU Trends Tools (#97)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="icu_get_trends",
    annotations=ToolAnnotations(
        title="Get Fitness & Fatigue Trends (Bounded Aggregates)",
        read_only_hint=True,
    ),
)
@audit_tool_call
async def icu_get_trends(params: IcuGetTrendsInput, ctx: Context) -> str:
    """Read bounded fitness/fatigue/form trend aggregates over a date range.

    Serves coach-web Epic 4 (longitudinal memory): trajectory data so
    planning conversations reason from trends, not single-day snapshots.
    Read-only; closes out the epic #82 tool set.

    Exactly one GET is issued per call against the verified Intervals.icu
    endpoint ``GET /api/v1/athlete/{id}/wellness`` (official OpenAPI spec,
    operation ``listWellnessRecords``; query params ``oldest``, ``newest``)
    — the only spec operation providing the ctl/atl/rampRate series. The
    date range is bounded server-side to at most 90 days (epic #82 binding
    condition 1) — wider ranges are rejected with an explicit validation
    error before any network call.

    The response is a whitelist-only aggregate projection: per-point ctl,
    atl, tsb (derived server-side as ctl - atl), and rampRate — never a raw
    wellness payload dump (no weight, resting HR, HRV, sleep, or other
    health values). The series is downsampled to the requested granularity
    (weekly by default: the last available day's values per 7-day bucket,
    at most 13 points for a 90-day window; daily: one point per available
    record day) and a current snapshot is included.

    Args:
        params (IcuGetTrendsInput): Validated date range (defaults to the
            last 42 days), optional athlete ID, aggregation granularity,
            and output format.
        ctx (Context): MCP request context carrying the shared client.

    Returns:
        str: Markdown report with a plain-language trend direction and the
        structured series, or the JSON report model, or a handled
        ``Error ...`` string (audited at ERROR level).
    """
    client = _get_client_from_ctx(ctx)
    oldest = cast(str, params.oldest)
    newest = cast(str, params.newest)
    try:
        records = await client.get_wellness(
            oldest=oldest,
            newest=newest,
            athlete_id=params.athlete_id,
        )
        report = build_trend_report(
            oldest,
            newest,
            records,
            granularity=params.granularity,
        )
        return format_trend_report(report, fmt_json=(params.response_format == ResponseFormat.JSON))
    except IntervalsAPIError as exc:
        return redact_sensitive(f"Error fetching fitness trends: {exc}") or ""
    except Exception as exc:  # noqa: BLE001
        return redact_sensitive(f"Error fetching fitness trends: {exc}") or ""


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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
async def intervals_create_event(params: CreateEventInput, ctx: Context) -> str:
    """Schedule a new structured workout or calendar event using workout DSL syntax.

    The workout DSL text (``workout_doc``) is delivered via the API ``description``
    field: the Intervals.icu server parses the DSL from ``description`` and compiles
    the structured workout on its side. A raw DSL string is never sent in the API
    ``workout_doc`` field (which expects a structured JSON object on write).
    """
    client = _get_client_from_ctx(ctx)
    payload: dict[str, Any] = {
        "start_date_local": params.start_date_local,
        "name": params.name,
        "type": params.type,
        "category": params.category,
    }
    if params.workout_doc:
        payload["description"] = (
            f"{params.description}\n\n{params.workout_doc}"
            if params.description
            else params.workout_doc
        )
    elif params.description:
        payload["description"] = params.description
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
@audit_tool_call
async def intervals_update_event(params: UpdateEventInput, ctx: Context) -> str:
    """Update date, description, title, or structured workout steps on a scheduled event.

    The workout DSL text (``workout_doc``) is delivered via the API ``description``
    field: the Intervals.icu server parses the DSL from ``description`` and compiles
    the structured workout on its side. A raw DSL string is never sent in the API
    ``workout_doc`` field (which expects a structured JSON object on write).
    """
    client = _get_client_from_ctx(ctx)
    payload: dict[str, Any] = {}
    if params.start_date_local:
        payload["start_date_local"] = params.start_date_local
    if params.name:
        payload["name"] = params.name
    if params.workout_doc is not None:
        payload["description"] = (
            f"{params.description}\n\n{params.workout_doc}"
            if params.description is not None
            else params.workout_doc
        )
    elif params.description is not None:
        payload["description"] = params.description
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
@audit_tool_call
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
@audit_tool_call
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
@audit_tool_call
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
