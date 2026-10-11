"""Pydantic v2 input and output models for Coach MCP."""

from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from coach_mcp.security import sanitize_comment_text


class ResponseFormat(StrEnum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class BaseToolModel(BaseModel):
    """Base model with standard configuration."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )


# ---------------------------------------------------------------------------
# Athlete Models
# ---------------------------------------------------------------------------


class GetAthleteProfileInput(BaseToolModel):
    """Input parameters for fetching athlete profile."""

    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self, or 'iXXXXX' for coached athlete).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (summary) or 'json' (raw data).",
    )


class GetSportSettingsInput(BaseToolModel):
    """Input parameters for fetching athlete sport settings & zones."""

    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (summary) or 'json' (raw data).",
    )


# ---------------------------------------------------------------------------
# Activity Models
# ---------------------------------------------------------------------------


class ListActivitiesInput(BaseToolModel):
    """Input parameters for listing athlete activities."""

    oldest: str | None = Field(
        default=None,
        description="Oldest date (YYYY-MM-DD). Defaults to 30 days ago.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str | None = Field(
        default=None,
        description="Newest date (YYYY-MM-DD). Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    limit: int | None = Field(
        default=50,
        description="Maximum number of activities to return (1-100).",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )

    @model_validator(mode="after")
    def _set_default_dates(self) -> "ListActivitiesInput":
        """Populate default date range when not provided."""
        if self.oldest is None:
            self.oldest = (date.today() - timedelta(days=30)).isoformat()
        if self.newest is None:
            self.newest = date.today().isoformat()
        return self


class GetActivityInput(BaseToolModel):
    """Input parameters for retrieving detailed activity data."""

    activity_id: str = Field(
        ...,
        description="Unique activity ID (e.g. 'i12345678' or numeric ID '12345678').",
        min_length=1,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


class GetActivityStreamsInput(BaseToolModel):
    """Input parameters for retrieving time series streams for an activity."""

    activity_id: str = Field(
        ...,
        description="Unique activity ID.",
        min_length=1,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    types: list[str] | None = Field(
        default_factory=lambda: ["watts", "heartrate", "cadence", "time", "distance", "altitude"],
        description=(
            "Stream types to retrieve "
            "(e.g. watts, heartrate, cadence, time, distance, altitude, temp)."
        ),
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


class GetActivityIntervalsInput(BaseToolModel):
    """Input parameters for retrieving detected intervals of an activity."""

    activity_id: str = Field(
        ...,
        description="Unique activity ID.",
        min_length=1,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


class GetPowerCurveInput(BaseToolModel):
    """Input parameters for retrieving athlete or activity power curves."""

    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    activity_id: str | None = Field(
        default=None,
        description=(
            "Optional activity ID. If provided, fetches power curve "
            "for this specific activity instead of athlete power curves."
        ),
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    sport_type: str = Field(
        default="Ride",
        description="Sport type for athlete power curve (e.g., 'Ride', 'Run').",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


class GetPowerModelInput(BaseToolModel):
    """Input parameters for retrieving athlete critical power model."""

    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self, or 'iXXXXX' for coached athlete).",
        pattern=r"^(0|i\d+)$",
    )
    sport_type: str = Field(
        default="Ride",
        description="Sport type for the power model (e.g., 'Ride', 'Run').",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


class CreateActivityInput(BaseToolModel):
    """Input parameters for manually recording an activity."""

    name: str = Field(
        ..., description="Name of the activity (e.g. 'Morning VO2max Intervals').", min_length=1
    )
    type: str = Field(
        ...,
        description="Activity type (e.g. 'Ride', 'VirtualRide', 'Run', 'Swim', 'WeightTraining').",
    )
    start_date_local: str = Field(
        ...,
        description=(
            "Local start timestamp in ISO format 'YYYY-MM-DDTHH:MM:SS' "
            "(e.g. '2026-08-22T09:00:00')."
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
    )
    moving_time_seconds: int = Field(..., description="Moving duration in seconds.", ge=1)
    elapsed_time_seconds: int | None = Field(
        default=None, description="Total elapsed duration in seconds.", ge=1
    )
    distance_meters: float | None = Field(
        default=None, description="Total distance in meters.", ge=0.0
    )
    average_watts: float | None = Field(default=None, description="Average power in Watts.", ge=0.0)
    average_heartrate: float | None = Field(
        default=None, description="Average heart rate in BPM.", ge=0.0
    )
    icu_training_load: float | None = Field(
        default=None, description="Training Load / TSS score.", ge=0.0
    )
    description: str | None = Field(default=None, description="Detailed activity notes.")
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )


class UpdateActivityInput(BaseToolModel):
    """Input parameters for modifying an existing activity."""

    activity_id: str = Field(..., description="Activity ID to update.", pattern=r"^[a-zA-Z0-9_-]+$")
    name: str | None = Field(default=None, description="Updated activity title.")
    description: str | None = Field(default=None, description="Updated notes or athlete feedback.")
    perceived_exertion: float | None = Field(
        default=None,
        description="Rating of Perceived Exertion (RPE 1-10).",
        ge=1.0,
        le=10.0,
    )
    feel: int | None = Field(
        default=None,
        description="Subjective feeling (1=Strong, 2=Good, 3=Normal, 4=Poor, 5=Terrible).",
        ge=1,
        le=5,
    )
    icu_training_load: float | None = Field(
        default=None, description="Adjusted training load (TSS).", ge=0.0
    )


class DeleteActivityInput(BaseToolModel):
    """Input parameters for deleting an activity."""

    activity_id: str = Field(..., description="Activity ID to delete.", pattern=r"^[a-zA-Z0-9_-]+$")


# ---------------------------------------------------------------------------
# Wellness & Metrics Models
# ---------------------------------------------------------------------------


class GetWellnessInput(BaseToolModel):
    """Input parameters for fetching wellness & fitness history."""

    oldest: str | None = Field(
        default=None,
        description="Oldest date (YYYY-MM-DD). Defaults to 7 days ago.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str | None = Field(
        default=None,
        description="Newest date (YYYY-MM-DD). Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )

    @model_validator(mode="after")
    def _set_default_dates(self) -> "GetWellnessInput":
        """Populate default date range when not provided."""
        if self.oldest is None:
            self.oldest = (date.today() - timedelta(days=7)).isoformat()
        if self.newest is None:
            self.newest = date.today().isoformat()
        return self


class RecordWellnessInput(BaseToolModel):
    """Input parameters for recording daily wellness and subjective recovery."""

    date: str = Field(
        ...,
        description="Date in ISO format YYYY-MM-DD (e.g. '2026-08-22').",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    restingHR: int | None = Field(
        default=None, description="Resting Heart Rate in BPM.", ge=30, le=150
    )
    hrv: float | None = Field(default=None, description="HRV (rMSSD in ms or SDNN).", ge=0.0)
    weight: float | None = Field(default=None, description="Weight in kg.", ge=30.0, le=250.0)
    sleepSecs: int | None = Field(default=None, description="Sleep duration in seconds.", ge=0)
    sleepQuality: int | None = Field(
        default=None, description="Sleep quality rating (1=Great, 4=Poor).", ge=1, le=4
    )
    readiness: float | None = Field(
        default=None, description="Overall readiness score (0-100).", ge=0.0, le=100.0
    )
    soreness: int | None = Field(
        default=None, description="Muscle soreness (1=None, 4=Extreme).", ge=1, le=4
    )
    fatigue: int | None = Field(
        default=None, description="Subjective fatigue (1=None, 4=Extreme).", ge=1, le=4
    )
    stress: int | None = Field(
        default=None, description="Life/training stress (1=Low, 4=Extreme).", ge=1, le=4
    )
    mood: int | None = Field(default=None, description="Mood rating (1=Great, 4=Poor).", ge=1, le=4)
    injury: int | None = Field(
        default=None, description="Injury status (1=None, 4=Injured).", ge=1, le=4
    )
    comments: str | None = Field(default=None, description="Notes on sleep, recovery, or health.")
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )


class WellnessRecordItem(BaseToolModel):
    """Single daily wellness record for bulk upload."""

    date: str = Field(
        ...,
        description="Date in ISO format YYYY-MM-DD.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    restingHR: int | None = Field(
        default=None, description="Resting heart rate in bpm (30-150).", ge=30, le=150
    )
    hrv: float | None = Field(
        default=None, description="Heart rate variability (rMSSD in ms >= 0.0).", ge=0.0
    )
    weight: float | None = Field(
        default=None, description="Weight in kilograms (30.0-250.0).", ge=30.0, le=250.0
    )
    sleepSecs: int | None = Field(
        default=None, description="Sleep duration in seconds (>= 0).", ge=0
    )
    sleepQuality: int | None = Field(
        default=None,
        description="Sleep quality rating (1: Poor, 2: Average, 3: Good, 4: Excellent).",
        ge=1,
        le=4,
    )
    readiness: float | None = Field(
        default=None, description="Readiness score (0.0-100.0).", ge=0.0, le=100.0
    )
    soreness: int | None = Field(
        default=None,
        description="Muscle soreness (1: None, 2: Low, 3: Medium, 4: High).",
        ge=1,
        le=4,
    )
    fatigue: int | None = Field(
        default=None,
        description="Fatigue level (1: None, 2: Low, 3: Medium, 4: High).",
        ge=1,
        le=4,
    )
    stress: int | None = Field(
        default=None,
        description="Stress level (1: Low, 2: Normal, 3: High, 4: Very High).",
        ge=1,
        le=4,
    )
    mood: int | None = Field(
        default=None,
        description="Mood rating (1: Poor, 2: Ok, 3: Good, 4: Great).",
        ge=1,
        le=4,
    )
    injury: int | None = Field(
        default=None,
        description="Injury status (1: None, 2: Niggle, 3: Injured, 4: Severe).",
        ge=1,
        le=4,
    )
    comments: str | None = Field(default=None, description="Subjective wellness notes or comments.")


class RecordWellnessBulkInput(BaseToolModel):
    """Input parameters for recording multiple daily wellness records at once."""

    records: list[WellnessRecordItem] = Field(
        ...,
        description="List of daily wellness records to upload (1-100 items).",
        min_length=1,
        max_length=100,
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for authenticated athlete).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format ('markdown' or 'json')."
    )


class GetFitnessSummaryInput(BaseToolModel):
    """Input parameters for calculating CTL (Fitness), ATL (Fatigue), and TSB (Form)."""

    oldest: str | None = Field(
        default=None,
        description="Oldest date (YYYY-MM-DD). Defaults to 42 days ago (6 weeks).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str | None = Field(
        default=None,
        description="Newest date (YYYY-MM-DD). Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )

    @model_validator(mode="after")
    def _set_default_dates(self) -> "GetFitnessSummaryInput":
        """Populate default date range when not provided."""
        if self.oldest is None:
            self.oldest = (date.today() - timedelta(days=42)).isoformat()
        if self.newest is None:
            self.newest = date.today().isoformat()
        return self


class GetReadinessDashboardInput(BaseToolModel):
    """Input parameters for composite daily readiness dashboard."""

    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self, or 'iXXXXX' for coached athlete).",
        pattern=r"^(0|i\d+)$",
    )
    days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Number of days of wellness/fitness history to analyze (default: 7).",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


# ---------------------------------------------------------------------------
# ICU Bounded Wellness Models (#84)
# ---------------------------------------------------------------------------

#: Maximum date-range span (in days) the bounded wellness read may cover per
#: call. Epic #82 binding security condition 1: ``oldest`` is clamped
#: server-side so an exfiltration-prone health read can never exceed this
#: window regardless of the requested range.
ICU_WELLNESS_MAX_SPAN_DAYS = 90

#: Default look-back window (in days) when no date range is provided.
ICU_WELLNESS_DEFAULT_DAYS = 30


def _parse_iso_date(value: str, field_name: str) -> date:
    """Parse a strict ``YYYY-MM-DD`` string into a real calendar date.

    Uses :meth:`datetime.strptime` (not ``date.fromisoformat``) so date
    parsing stays functional in tests that patch the module-level ``date``
    symbol to mock ``date.today()``.

    Raises:
        ValueError: If the string is not a real calendar date.
    """
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid calendar date: {value!r}") from exc


class IcuGetWellnessInput(BaseToolModel):
    """Input parameters for the bounded daily wellness read (``icu_get_wellness``).

    The requested date range is validated and bounded server-side: ``oldest``
    is clamped so that the ``oldest``→``newest`` span never exceeds
    :data:`ICU_WELLNESS_MAX_SPAN_DAYS` (90) days, regardless of what the
    caller requests.
    """

    oldest: str | None = Field(
        default=None,
        description=(
            "Oldest date (YYYY-MM-DD). Defaults to 30 days ago. Clamped "
            "server-side to a maximum 90-day span before newest."
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str | None = Field(
        default=None,
        description="Newest date (YYYY-MM-DD). Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self, or 'iXXXXX' for coached athlete).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )

    @model_validator(mode="after")
    def _set_and_clamp_dates(self) -> "IcuGetWellnessInput":
        """Apply smart defaults, validate calendar dates, and clamp the span.

        Raises:
            ValueError: If either date is not a real calendar date or if
                ``oldest`` is after ``newest``.
        """
        if self.newest is None:
            self.newest = date.today().isoformat()
        if self.oldest is None:
            self.oldest = (date.today() - timedelta(days=ICU_WELLNESS_DEFAULT_DAYS)).isoformat()

        newest_date = _parse_iso_date(self.newest, "newest")
        oldest_date = _parse_iso_date(self.oldest, "oldest")
        if oldest_date > newest_date:
            raise ValueError("oldest must be on or before newest")

        span_days = (newest_date - oldest_date).days
        if span_days > ICU_WELLNESS_MAX_SPAN_DAYS:
            self.oldest = (newest_date - timedelta(days=ICU_WELLNESS_MAX_SPAN_DAYS)).isoformat()
        return self


class WellnessDayProjection(BaseToolModel):
    """Whitelisted projection of one daily Intervals.icu wellness record.

    Epic #82 binding security condition 2: the bounded wellness read exposes
    only the health fields coach-web needs (sleep, HRV, soreness, fatigue,
    stress, readiness, ctl, atl) — never a raw pass-through of the ICU
    payload. ``tsb`` is derived server-side as ``ctl - atl``.
    """

    date: str = Field(..., description="Calendar date (YYYY-MM-DD).")
    sleep_hours: float | None = Field(
        default=None, description="Sleep duration in hours (derived from sleepSecs)."
    )
    hrv: float | None = Field(default=None, description="HRV (rMSSD in ms).")
    soreness: float | None = Field(default=None, description="Muscle soreness level (1-4).")
    fatigue: float | None = Field(default=None, description="Fatigue level (1-4).")
    stress: float | None = Field(default=None, description="Stress level (1-4).")
    readiness: float | None = Field(default=None, description="Readiness score (0-100).")
    ctl: float | None = Field(default=None, description="Chronic training load (fitness).")
    atl: float | None = Field(default=None, description="Acute training load (fatigue).")
    tsb: float | None = Field(
        default=None, description="Training stress balance (derived as ctl - atl)."
    )


def _numeric_or_none(value: Any) -> float | None:
    """Coerce an ICU payload value to a finite float, or None if not numeric.

    Booleans and non-numeric types (strings, dicts, lists) are dropped so a
    malformed upstream payload can never smuggle unexpected content through
    the whitelist projection.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def project_wellness_days(records: list[dict[str, Any]]) -> list[WellnessDayProjection]:
    """Project raw Intervals.icu wellness records onto the health-field whitelist.

    This is the security boundary for the bounded wellness read: every field
    not present on :class:`WellnessDayProjection` is discarded here, so raw
    ICU payload content (weight, resting HR, mood, injury, free-text comments,
    provider measurements, unknown future fields) can never reach tool output.

    Args:
        records: Raw wellness records as returned by the ICU API.

    Returns:
        Whitelisted daily projections with ``tsb`` derived as ``ctl - atl``.
    """
    projected: list[WellnessDayProjection] = []
    for record in records:
        ctl = _numeric_or_none(record.get("ctl"))
        atl = _numeric_or_none(record.get("atl"))
        tsb = round(ctl - atl, 2) if ctl is not None and atl is not None else None

        sleep_secs = _numeric_or_none(record.get("sleepSecs"))
        sleep_hours = round(sleep_secs / 3600.0, 2) if sleep_secs is not None else None

        projected.append(
            WellnessDayProjection(
                date=str(record.get("id", "")),
                sleep_hours=sleep_hours,
                hrv=_numeric_or_none(record.get("hrv")),
                soreness=_numeric_or_none(record.get("soreness")),
                fatigue=_numeric_or_none(record.get("fatigue")),
                stress=_numeric_or_none(record.get("stress")),
                readiness=_numeric_or_none(record.get("readiness")),
                ctl=ctl,
                atl=atl,
                tsb=tsb,
            )
        )
    return projected


# ---------------------------------------------------------------------------
# ICU Session Comment Models (#85)
# ---------------------------------------------------------------------------

#: Maximum length of a session comment posted to Intervals.icu chat
#: (epic #82 binding security condition 4).
SESSION_COMMENT_MAX_LENGTH = 2000


class IcuAddSessionCommentInput(BaseToolModel):
    """Input parameters for posting a debrief comment on an ICU activity.

    Contract (epic #82 binding security conditions 1 and 4):

    * ``confirmed`` must be ``True`` — the write is rejected server-side
      otherwise (mirror of coach-web's plan-approval gate);
    * ``comment`` must be server-generated from validated debrief data —
      this tool is never a raw-LLM passthrough channel. The text is
      sanitized (script/style blocks and HTML tags stripped, control
      characters removed) and hard-capped at 2000 characters.
    """

    activity_id: str = Field(
        ...,
        description="Intervals.icu activity ID to comment on (e.g. 'i12345678').",
        min_length=1,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    comment: str = Field(
        ...,
        description=(
            "Debrief summary text, server-generated from validated debrief data "
            "(never raw LLM output). Sanitized and capped at 2000 characters."
        ),
        min_length=1,
        max_length=SESSION_COMMENT_MAX_LENGTH,
    )
    confirmed: bool = Field(
        default=False,
        description=(
            "Explicit write confirmation. The comment is posted only when True; "
            "unconfirmed invocations are rejected server-side."
        ),
    )

    @field_validator("comment")
    @classmethod
    def _sanitize_comment(cls, value: str) -> str:
        """Strip markup and control characters from the comment body.

        Raises:
            ValueError: If the comment is empty once sanitized.
        """
        sanitized = sanitize_comment_text(value)
        if not sanitized:
            raise ValueError("comment is empty after sanitization")
        return sanitized


# ---------------------------------------------------------------------------
# ICU Batch Event Models (#94)
# ---------------------------------------------------------------------------

#: Maximum number of event drafts accepted per ``icu_batch_create_events``
#: call. A 7-day microcycle needs at most a handful of entries; the bound
#: caps abuse surface (payload size) on the highest-scrutiny write path.
ICU_BATCH_MAX_ITEMS = 50

#: Local start time assigned to batch-placed events when the draft carries
#: only a calendar date. Deterministic so the confirmation token derived
#: from the normalized payload is stable across preview and execute phases.
ICU_EVENT_DEFAULT_START_TIME = "08:00:00"

#: Maximum length of a batch event title (abuse bound on the write payload).
ICU_EVENT_NAME_MAX_LENGTH = 200

#: Maximum length of a batch event description (human-readable instructions).
ICU_EVENT_DESCRIPTION_MAX_LENGTH = 5000

#: Maximum length of a batch event workout DSL definition (structured steps
#: can be long; the DSL is delivered via the description field like the
#: single-event tools).
ICU_EVENT_WORKOUT_DOC_MAX_LENGTH = 20000

#: Maximum length of a caller-supplied external_id reconciliation key.
ICU_EVENT_EXTERNAL_ID_MAX_LENGTH = 128

#: Calendar event categories accepted by the Intervals.icu EventEx schema
#: (official OpenAPI spec, ``components.schemas.EventEx.category``).
IcuEventCategory = Literal[
    "WORKOUT",
    "RACE_A",
    "RACE_B",
    "RACE_C",
    "NOTE",
    "PLAN",
    "HOLIDAY",
    "SICK",
    "INJURED",
    "SET_EFTP",
    "FITNESS_DAYS",
    "SEASON_START",
    "TARGET",
    "SET_FITNESS",
]


class IcuEventDraft(BaseToolModel):
    """One planned-workout draft inside an ``icu_batch_create_events`` batch.

    Each draft carries a caller-supplied ``external_id`` reconciliation key:
    re-submitting the same key upserts (updates) the existing event instead
    of creating a duplicate (epic #82 batch semantics, PO decision 4a).

    Markdown-injection defense (#90): ``name`` and ``description`` are
    sanitized at validation (script/style blocks and HTML tags stripped,
    control characters removed); titles are additionally collapsed to a
    single line. ``workout_doc`` carries Intervals.icu workout DSL text and
    is delivered raw via the description field, exactly like the
    single-event tools.
    """

    external_id: str = Field(
        ...,
        description=(
            "Caller-supplied reconciliation key. Re-submitting the same "
            "external_id upserts the existing event instead of duplicating it."
        ),
        min_length=1,
        max_length=ICU_EVENT_EXTERNAL_ID_MAX_LENGTH,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    date: str = Field(
        ...,
        description="Calendar date for the event (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    name: str = Field(
        ...,
        description=(
            "Event title. Sanitized (markup stripped) and collapsed to a "
            "single line at validation."
        ),
        min_length=1,
        max_length=ICU_EVENT_NAME_MAX_LENGTH,
    )
    type: str = Field(
        default="Ride",
        description="Sport type ('Ride', 'Run', 'Swim', 'WeightTraining', etc.).",
        min_length=1,
    )
    category: IcuEventCategory = Field(
        default="WORKOUT",
        description="Intervals.icu calendar event category.",
    )
    description: str | None = Field(
        default=None,
        description=(
            "Human-readable instructions. Sanitized (markup stripped) at "
            "validation; newlines preserved."
        ),
        max_length=ICU_EVENT_DESCRIPTION_MAX_LENGTH,
    )
    moving_time_seconds: int | None = Field(
        default=None, description="Planned duration in seconds.", ge=1
    )
    icu_training_load: float | None = Field(default=None, description="Planned TSS / load.", ge=0.0)
    workout_doc: str | None = Field(
        default=None,
        description=(
            "Intervals.icu structured workout DSL definition text, delivered "
            "via the calendar 'description' field (the API parses the DSL and "
            "compiles the structured workout on its side)."
        ),
        max_length=ICU_EVENT_WORKOUT_DOC_MAX_LENGTH,
    )

    @field_validator("date")
    @classmethod
    def _validate_calendar_date(cls, value: str) -> str:
        """Reject shape-valid but impossible calendar dates (e.g. 2026-02-30).

        Raises:
            ValueError: If the date is not a real calendar date.
        """
        _parse_iso_date(value, "date")
        return value

    @field_validator("name")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        """Sanitize the title and collapse it to a single line.

        Raises:
            ValueError: If the title is empty once sanitized.
        """
        sanitized = " ".join(sanitize_comment_text(value).split())
        if not sanitized:
            raise ValueError("name is empty after sanitization")
        return sanitized

    @field_validator("description")
    @classmethod
    def _sanitize_description(cls, value: str | None) -> str | None:
        """Sanitize the description, preserving newlines for multi-line text.

        Raises:
            ValueError: If a provided description is empty once sanitized.
        """
        if value is None:
            return None
        sanitized = sanitize_comment_text(value)
        if not sanitized:
            raise ValueError("description is empty after sanitization")
        return sanitized


class IcuBatchCreateEventsInput(BaseToolModel):
    """Input parameters for the confirmation-gated batch event upsert.

    Two-phase confirmation gate (epic #82 binding security condition 2):
    omit ``confirm_token`` to obtain a dry-run preview with a token derived
    from the exact normalized payload; re-invoke with that token to execute.
    A token mismatch (payload changed since the preview) is rejected before
    any network call.

    The batch is bounded to :data:`ICU_BATCH_MAX_ITEMS` (50) drafts and
    duplicate ``external_id`` keys are rejected at validation — both before
    any network call.
    """

    events: list[IcuEventDraft] = Field(
        ...,
        description="Event drafts to place on the calendar (1-50 items).",
        min_length=1,
        max_length=ICU_BATCH_MAX_ITEMS,
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self, or 'iXXXXX' for coached athlete).",
        pattern=r"^(0|i\d+)$",
    )
    confirm_token: str | None = Field(
        default=None,
        description=(
            "Confirmation token returned by a dry-run preview of the exact "
            "same batch. Omit to preview; provide to execute."
        ),
        max_length=64,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )

    @model_validator(mode="after")
    def _reject_duplicate_external_ids(self) -> "IcuBatchCreateEventsInput":
        """Reject two drafts sharing an external_id (upsert ambiguity).

        Raises:
            ValueError: If any external_id appears more than once.
        """
        seen: set[str] = set()
        for draft in self.events:
            if draft.external_id in seen:
                raise ValueError(f"duplicate external_id in batch: {draft.external_id!r}")
            seen.add(draft.external_id)
        return self


class IcuBatchEventOutcome(BaseToolModel):
    """Per-item outcome of a batch event upsert (no-rollback semantics).

    The Intervals.icu bulk endpoint has no transactional rollback, so partial
    success must be visible, never silent: every draft is reported as
    ``created``, ``updated``, or ``failed`` with a reason when failed.
    """

    external_id: str = Field(..., description="Caller-supplied reconciliation key.")
    outcome: Literal["created", "updated", "failed"] = Field(
        ..., description="Per-item outcome of the upsert."
    )
    event_id: str | None = Field(
        default=None, description="Intervals.icu event ID when the item was written."
    )
    reason: str | None = Field(
        default=None, description="Failure reason (redacted) when the item failed."
    )


# ---------------------------------------------------------------------------
# ICU Workout Compliance Models (#95)
# ---------------------------------------------------------------------------

#: Maximum date-range span (in days) the compliance read may cover per call.
#: Epic #82 binding security condition 1 — same bound as the wellness read;
#: per issue #95 AC1 a wider range is REJECTED with an explicit validation
#: error (not clamped) before any network call.
ICU_COMPLIANCE_MAX_SPAN_DAYS = 90

#: Default look-back window (in days) — the weekly debrief cadence of the
#: consuming story (coach-web Story 3.2).
ICU_COMPLIANCE_DEFAULT_DAYS = 7


class IcuGetWorkoutComplianceInput(BaseToolModel):
    """Input parameters for the bounded planned-vs-executed compliance read.

    The requested date range is validated server-side before any network
    call: dates must be real calendar dates, ``oldest`` must be on or before
    ``newest``, and the span is hard-capped at
    :data:`ICU_COMPLIANCE_MAX_SPAN_DAYS` (90) days — wider ranges are
    rejected with an explicit validation error (issue #95 AC1).
    """

    oldest: str | None = Field(
        default=None,
        description=(
            "Oldest date (YYYY-MM-DD). Defaults to 7 days ago. Ranges wider "
            "than 90 days are rejected server-side."
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str | None = Field(
        default=None,
        description="Newest date (YYYY-MM-DD). Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self, or 'iXXXXX' for coached athlete).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )

    @model_validator(mode="after")
    def _set_and_bound_dates(self) -> "IcuGetWorkoutComplianceInput":
        """Apply smart defaults, validate calendar dates, and bound the span.

        Raises:
            ValueError: If either date is not a real calendar date, if
                ``oldest`` is after ``newest``, or if the span exceeds the
                90-day maximum.
        """
        if self.newest is None:
            self.newest = date.today().isoformat()
        if self.oldest is None:
            self.oldest = (date.today() - timedelta(days=ICU_COMPLIANCE_DEFAULT_DAYS)).isoformat()

        newest_date = _parse_iso_date(self.newest, "newest")
        oldest_date = _parse_iso_date(self.oldest, "oldest")
        if oldest_date > newest_date:
            raise ValueError("oldest must be on or before newest")

        span_days = (newest_date - oldest_date).days
        if span_days > ICU_COMPLIANCE_MAX_SPAN_DAYS:
            raise ValueError(
                f"date range spans {span_days} days, exceeding the "
                f"{ICU_COMPLIANCE_MAX_SPAN_DAYS}-day maximum for compliance reads"
            )
        return self


class WorkoutComplianceEvent(BaseToolModel):
    """Whitelisted per-event adherence classification (``icu_get_workout_compliance``).

    One planned WORKOUT calendar event joined to its executed activity via
    the native ``paired_event_id`` link (never heuristic date/title
    matching). ``compliance`` is Intervals.icu's own planned-vs-executed
    score for the paired activity; ``structure_diff`` is the server-side
    cross-check of the planned ``workout_doc`` structure against the
    executed interval data.
    """

    event_id: str = Field(..., description="Planned calendar event ID.")
    date: str = Field(..., description="Planned event date (YYYY-MM-DD).")
    name: str = Field(..., description="Planned workout title.")
    status: Literal["completed", "missed", "upcoming"] = Field(
        ...,
        description=(
            "Adherence classification: completed (paired activity found), "
            "missed (past event with no paired activity), upcoming (future "
            "event, excluded from the adherence rate)."
        ),
    )
    compliance: float | None = Field(
        default=None,
        description="Native Intervals.icu compliance score of the paired activity.",
    )
    structure_diff: Literal["match", "mismatch", "unavailable"] = Field(
        ...,
        description=(
            "Per-interval diff of the planned workout_doc structure against "
            "the executed interval data: match, mismatch, or unavailable "
            "when either side carries no comparable structure."
        ),
    )


class WorkoutComplianceReport(BaseToolModel):
    """Whitelisted compliance report over a bounded date range.

    Exposes only the adherence summary and per-event classifications — never
    a raw pass-through of the executed activity payload (no biometric or
    sensor values).
    """

    oldest: str = Field(..., description="Reported range start (YYYY-MM-DD).")
    newest: str = Field(..., description="Reported range end (YYYY-MM-DD).")
    total_planned: int = Field(
        ..., description="Planned WORKOUT events counted for the adherence rate.", ge=0
    )
    completed: int = Field(..., description="Planned workouts with a paired activity.", ge=0)
    missed: int = Field(..., description="Past planned workouts without a paired activity.", ge=0)
    upcoming: int = Field(
        ..., description="Future planned workouts (excluded from the rate).", ge=0
    )
    adherence_rate: float | None = Field(
        default=None,
        description=(
            "Completed share of rateable planned workouts in percent "
            "(0-100); None when no workout was rateable."
        ),
    )
    events: list[WorkoutComplianceEvent] = Field(
        default_factory=list, description="Per-event adherence classifications."
    )


def _planned_interval_count(workout_doc: Any) -> int | None:
    """Best-effort work-interval count from a planned ``workout_doc``.

    Compiled docs (a dict carrying a ``steps`` list) yield the step count.
    DSL strings are not structurally parsed — a full DSL grammar is out of
    scope — so they yield ``None`` and the diff reports ``unavailable``
    instead of a guessed number.
    """
    if isinstance(workout_doc, dict):
        steps = workout_doc.get("steps")
        if isinstance(steps, list):
            return len(steps)
    return None


def _executed_interval_count(interval_summary: Any) -> int | None:
    """Executed interval count from the activity's ``interval_summary``."""
    if isinstance(interval_summary, list) and interval_summary:
        return len(interval_summary)
    return None


def _structure_diff(
    planned_doc: Any,
    executed_summary: Any,
) -> Literal["match", "mismatch", "unavailable"]:
    """Compare the planned workout structure against the executed intervals.

    The diff is a count comparison: planned work steps extracted from the
    compiled ``workout_doc`` versus the executed ``interval_summary`` entries
    carried by the activity payload. Either side missing structure yields
    ``unavailable`` — never a guessed verdict.
    """
    planned_count = _planned_interval_count(planned_doc)
    executed_count = _executed_interval_count(executed_summary)
    if planned_count is None or executed_count is None:
        return "unavailable"
    return "match" if planned_count == executed_count else "mismatch"


def build_workout_compliance_report(
    oldest: str,
    newest: str,
    events: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    today: date | None = None,
) -> WorkoutComplianceReport:
    """Join planned events to executed activities into a compliance report.

    This is the security boundary of the compliance read: every field not
    present on :class:`WorkoutComplianceEvent` /
    :class:`WorkoutComplianceReport` is discarded here, so raw activity
    payload content (heart rate, power, sensor streams, unknown future
    fields) can never reach tool output.

    Join semantics (issue #95 AC2): an executed activity is paired with the
    planned event whose integer ``id`` equals the activity's native
    ``paired_event_id`` — never by date or title heuristics.

    Args:
        oldest: Reported range start (YYYY-MM-DD).
        newest: Reported range end (YYYY-MM-DD).
        events: Planned calendar events as returned by the ICU events list.
        activities: Executed activities as returned by the ICU activities list.
        today: Reference date for the upcoming/missed split; defaults to
            the current date.

    Returns:
        The whitelisted compliance report with per-event classifications
        and the summary adherence rate.
    """
    reference = today or date.today()

    activities_by_event_id: dict[int, dict[str, Any]] = {}
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        paired = activity.get("paired_event_id")
        if isinstance(paired, bool) or not isinstance(paired, int):
            continue
        activities_by_event_id[paired] = activity

    classified: list[WorkoutComplianceEvent] = []
    completed = 0
    missed = 0
    upcoming = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        if str(event.get("category", "")).upper() != "WORKOUT":
            continue
        event_id = event.get("id")
        if isinstance(event_id, bool) or not isinstance(event_id, int):
            continue  # cannot join without the native numeric event id

        paired_activity = activities_by_event_id.get(event_id)
        event_date_str = str(event.get("start_date_local", ""))[:10]
        try:
            event_date = _parse_iso_date(event_date_str, "event date")
        except ValueError:
            event_date = None

        if paired_activity is not None:
            status: Literal["completed", "missed", "upcoming"] = "completed"
            completed += 1
        elif event_date is not None and event_date > reference:
            status = "upcoming"
            upcoming += 1
        else:
            status = "missed"
            missed += 1

        compliance = (
            _numeric_or_none(paired_activity.get("compliance")) if paired_activity else None
        )
        executed_summary = paired_activity.get("interval_summary") if paired_activity else None
        classified.append(
            WorkoutComplianceEvent(
                event_id=str(event_id),
                date=event_date_str,
                name=str(event.get("name", "Untitled")),
                status=status,
                compliance=compliance,
                structure_diff=_structure_diff(event.get("workout_doc"), executed_summary),
            )
        )

    total_planned = completed + missed
    adherence_rate = round(completed / total_planned * 100.0, 1) if total_planned else None
    return WorkoutComplianceReport(
        oldest=oldest,
        newest=newest,
        total_planned=total_planned,
        completed=completed,
        missed=missed,
        upcoming=upcoming,
        adherence_rate=adherence_rate,
        events=classified,
    )


# ---------------------------------------------------------------------------
# ICU Completed Sessions Models (#96)
# ---------------------------------------------------------------------------

#: Maximum date-range span (in days) the completed-sessions read may cover per
#: call. Epic #82 binding security condition 1 — same bound as the wellness and
#: compliance reads; per issue #96 AC1 a wider range is REJECTED with an
#: explicit validation error (not clamped) before any network call.
ICU_SESSIONS_MAX_SPAN_DAYS = 90

#: Default look-back window (in days) — the weekly debrief cadence of the
#: consuming story (coach-web #164 greeting source).
ICU_SESSIONS_DEFAULT_DAYS = 7

#: Maximum page size (activities per call) for the completed-sessions read.
#: Bounds the tool payload regardless of how many activities the range holds.
ICU_SESSIONS_MAX_PAGE_SIZE = 100


class IcuActivityType(StrEnum):
    """Strict activity-type filter for ``icu_get_completed_sessions``.

    Core endurance/coaching types from the Intervals.icu ``Activity.type``
    enum (official OpenAPI spec, ``GET https://intervals.icu/api/v1/docs``).
    The filter is strict per issue #96 AC3 / #90 enum gating: values outside
    this enum are rejected at validation with field-level errors — no loose
    strings or booleans.
    """

    RIDE = "Ride"
    VIRTUAL_RIDE = "VirtualRide"
    RUN = "Run"
    SWIM = "Swim"
    WEIGHT_TRAINING = "WeightTraining"
    WORKOUT = "Workout"
    OTHER = "Other"


class IcuGetCompletedSessionsInput(BaseToolModel):
    """Input parameters for the bounded completed-sessions read.

    The requested date range is validated server-side before any network
    call: dates must be real calendar dates, ``oldest`` must be on or before
    ``newest``, and the span is hard-capped at
    :data:`ICU_SESSIONS_MAX_SPAN_DAYS` (90) days — wider ranges are rejected
    with an explicit validation error (issue #96 AC1).
    """

    oldest: str | None = Field(
        default=None,
        description=(
            "Oldest date (YYYY-MM-DD). Defaults to 7 days ago. Ranges wider "
            "than 90 days are rejected server-side."
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str | None = Field(
        default=None,
        description="Newest date (YYYY-MM-DD). Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self, or 'iXXXXX' for coached athlete).",
        pattern=r"^(0|i\d+)$",
    )
    activity_type: IcuActivityType | None = Field(
        default=None,
        description=(
            "Optional strict activity-type filter (e.g. 'Ride', 'VirtualRide', "
            "'Run', 'Swim', 'WeightTraining'). Invalid values are rejected."
        ),
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=ICU_SESSIONS_MAX_PAGE_SIZE,
        description="Page-size cap: maximum sessions returned per call (1-100).",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )

    @model_validator(mode="after")
    def _set_and_bound_dates(self) -> "IcuGetCompletedSessionsInput":
        """Apply smart defaults, validate calendar dates, and bound the span.

        Raises:
            ValueError: If either date is not a real calendar date, if
                ``oldest`` is after ``newest``, or if the span exceeds the
                90-day maximum.
        """
        if self.newest is None:
            self.newest = date.today().isoformat()
        if self.oldest is None:
            self.oldest = (date.today() - timedelta(days=ICU_SESSIONS_DEFAULT_DAYS)).isoformat()

        newest_date = _parse_iso_date(self.newest, "newest")
        oldest_date = _parse_iso_date(self.oldest, "oldest")
        if oldest_date > newest_date:
            raise ValueError("oldest must be on or before newest")

        span_days = (newest_date - oldest_date).days
        if span_days > ICU_SESSIONS_MAX_SPAN_DAYS:
            raise ValueError(
                f"date range spans {span_days} days, exceeding the "
                f"{ICU_SESSIONS_MAX_SPAN_DAYS}-day maximum for completed-session reads"
            )
        return self


class CompletedSessionSummary(BaseToolModel):
    """Whitelisted summary of one completed session (``icu_get_completed_sessions``).

    Epic #82 binding security condition 2: summary fields only — id, date,
    type, title, duration, and ICU-provided load/TSS. Never a raw pass-through
    of the activity payload: no heart rate, power, cadence, calories, sensor
    streams, or athlete notes reach tool output.
    """

    id: str = Field(..., description="Intervals.icu activity ID.")
    date: str = Field(..., description="Session date (YYYY-MM-DD, from start_date_local).")
    type: str = Field(..., description="Activity type (e.g. 'Ride', 'VirtualRide').")
    title: str = Field(..., description="Session title.")
    duration_seconds: float | None = Field(default=None, description="Moving duration in seconds.")
    load: float | None = Field(
        default=None, description="ICU-provided training load (TSS) when available."
    )


class CompletedSessionsPage(BaseToolModel):
    """Whitelisted, page-bounded listing of completed sessions.

    ``fetched`` is the number of raw activities Intervals.icu returned for the
    range (the API page); ``returned`` is the number of whitelisted sessions
    in this page after the optional type filter and the page-size cap. When
    ``fetched`` reaches the requested page size, more sessions may exist
    beyond the page.
    """

    oldest: str = Field(..., description="Reported range start (YYYY-MM-DD).")
    newest: str = Field(..., description="Reported range end (YYYY-MM-DD).")
    activity_type: str | None = Field(
        default=None, description="Applied activity-type filter (None = all types)."
    )
    fetched: int = Field(
        ...,
        description="Raw activities fetched from Intervals.icu for the range.",
        ge=0,
    )
    returned: int = Field(
        ...,
        description="Whitelisted sessions in this page (after filter and cap).",
        ge=0,
    )
    sessions: list[CompletedSessionSummary] = Field(
        default_factory=list, description="Whitelisted session summaries."
    )


def project_completed_sessions(
    records: list[dict[str, Any]],
    activity_type: IcuActivityType | None = None,
) -> list[CompletedSessionSummary]:
    """Project raw Intervals.icu activities onto the completed-session whitelist.

    This is the security boundary for the completed-sessions read: every field
    not present on :class:`CompletedSessionSummary` is discarded here, so raw
    activity payload content (heart rate, power, calories, athlete notes,
    sensor streams, unknown future fields) can never reach tool output.

    Args:
        records: Raw activities as returned by the ICU activities list.
        activity_type: Optional strict type filter; when set, only activities
            whose ``type`` equals the enum value are projected.

    Returns:
        Whitelisted session summaries in the upstream (descending date) order.
    """
    projected: list[CompletedSessionSummary] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        raw_type = str(record.get("type", ""))
        if activity_type is not None and raw_type != activity_type.value:
            continue
        projected.append(
            CompletedSessionSummary(
                id=str(record.get("id", "")),
                date=str(record.get("start_date_local", ""))[:10],
                type=raw_type,
                title=str(record.get("name", "Untitled")),
                duration_seconds=_numeric_or_none(record.get("moving_time")),
                load=_numeric_or_none(record.get("icu_training_load")),
            )
        )
    return projected


# ---------------------------------------------------------------------------
# ICU Trends Models (#97)
# ---------------------------------------------------------------------------

#: Maximum date-range span (in days) the trends read may cover per call.
#: Epic #82 binding security condition 1 — same bound as the wellness,
#: compliance, and completed-sessions reads; per issue #97 AC1 a wider range
#: is REJECTED with an explicit validation error (not clamped) before any
#: network call.
ICU_TRENDS_MAX_SPAN_DAYS = 90

#: Default look-back window (in days) — six weeks, giving six weekly points
#: for a meaningful trajectory by default.
ICU_TRENDS_DEFAULT_DAYS = 42


class IcuTrendGranularity(StrEnum):
    """Aggregation granularity for ``icu_get_trends`` (issue #97 AC4).

    Strict enum per #90 gating: values outside this enum are rejected at
    validation with field-level errors — no loose strings or booleans.
    """

    DAILY = "daily"
    WEEKLY = "weekly"


class IcuGetTrendsInput(BaseToolModel):
    """Input parameters for the bounded fitness/fatigue trends read.

    The requested date range is validated server-side before any network
    call: dates must be real calendar dates, ``oldest`` must be on or before
    ``newest``, and the span is hard-capped at
    :data:`ICU_TRENDS_MAX_SPAN_DAYS` (90) days — wider ranges are rejected
    with an explicit validation error (issue #97 AC1).
    """

    oldest: str | None = Field(
        default=None,
        description=(
            "Oldest date (YYYY-MM-DD). Defaults to 42 days ago. Ranges wider "
            "than 90 days are rejected server-side."
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str | None = Field(
        default=None,
        description="Newest date (YYYY-MM-DD). Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self, or 'iXXXXX' for coached athlete).",
        pattern=r"^(0|i\d+)$",
    )
    granularity: IcuTrendGranularity = Field(
        default=IcuTrendGranularity.WEEKLY,
        description="Aggregation granularity: 'weekly' (default) or 'daily'.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )

    @model_validator(mode="after")
    def _set_and_bound_dates(self) -> "IcuGetTrendsInput":
        """Apply smart defaults, validate calendar dates, and bound the span.

        Raises:
            ValueError: If either date is not a real calendar date, if
                ``oldest`` is after ``newest``, or if the span exceeds the
                90-day maximum.
        """
        if self.newest is None:
            self.newest = date.today().isoformat()
        if self.oldest is None:
            self.oldest = (date.today() - timedelta(days=ICU_TRENDS_DEFAULT_DAYS)).isoformat()

        newest_date = _parse_iso_date(self.newest, "newest")
        oldest_date = _parse_iso_date(self.oldest, "oldest")
        if oldest_date > newest_date:
            raise ValueError("oldest must be on or before newest")

        span_days = (newest_date - oldest_date).days
        if span_days > ICU_TRENDS_MAX_SPAN_DAYS:
            raise ValueError(
                f"date range spans {span_days} days, exceeding the "
                f"{ICU_TRENDS_MAX_SPAN_DAYS}-day maximum for trend reads"
            )
        return self


class TrendPoint(BaseToolModel):
    """Whitelisted single point of the fitness/fatigue trend series.

    Epic #82 binding security condition 2: aggregate training-load fields
    only — ctl, atl, tsb (derived server-side as ``ctl - atl``), and
    rampRate. Never a raw pass-through of the wellness payload: no weight,
    resting HR, HRV, sleep, mood, or any other health field reaches tool
    output.
    """

    date: str = Field(..., description="Point date (YYYY-MM-DD).")
    ctl: float | None = Field(default=None, description="Chronic training load (fitness).")
    atl: float | None = Field(default=None, description="Acute training load (fatigue).")
    tsb: float | None = Field(
        default=None, description="Training stress balance (derived as ctl - atl)."
    )
    ramp_rate: float | None = Field(
        default=None, description="ICU-provided CTL ramp rate for the day."
    )


class TrendReport(BaseToolModel):
    """Whitelisted, point-bounded fitness/fatigue trend report.

    ``points`` is the series downsampled to the requested granularity
    (weekly buckets keep the last available day's values per 7-day bucket
    ending at ``newest`` — at most 13 points for a 90-day window; daily
    keeps one point per available record day, at most 91 for 90 days).
    ``snapshot`` carries the most recent available daily values (None when
    the range holds no data).
    """

    oldest: str = Field(..., description="Reported range start (YYYY-MM-DD).")
    newest: str = Field(..., description="Reported range end (YYYY-MM-DD).")
    granularity: str = Field(..., description="Applied aggregation granularity.")
    points: list[TrendPoint] = Field(
        default_factory=list, description="Downsampled trend series (ascending date)."
    )
    snapshot: TrendPoint | None = Field(
        default=None, description="Most recent available daily values."
    )


def build_trend_report(
    oldest: str,
    newest: str,
    records: list[dict[str, Any]],
    granularity: IcuTrendGranularity = IcuTrendGranularity.WEEKLY,
) -> TrendReport:
    """Project raw wellness records into a bounded, downsampled trend report.

    This is the security boundary for the trends read: every field not
    present on :class:`TrendPoint` / :class:`TrendReport` is discarded here,
    so raw wellness payload content (weight, resting HR, HRV, sleep, mood,
    free-text comments, unknown future fields) can never reach tool output.

    Downsampling (issue #97 AC2): ``daily`` keeps one point per available
    record day; ``weekly`` groups records into 7-day buckets ending at
    ``newest`` and keeps the last available day's values per bucket, so a
    90-day window yields at most 13 points. Records outside
    ``[oldest, newest]`` or without a parseable date are skipped, keeping
    the point-count bound robust against unexpected upstream payloads.
    ``tsb`` is derived server-side as ``ctl - atl``.

    Args:
        oldest: Reported range start (YYYY-MM-DD).
        newest: Reported range end (YYYY-MM-DD).
        records: Raw wellness records as returned by the ICU wellness list.
        granularity: Aggregation granularity (weekly by default).

    Returns:
        The whitelisted trend report with the downsampled series and the
        current snapshot (None when the range holds no data).
    """
    oldest_date = _parse_iso_date(oldest, "oldest")
    newest_date = _parse_iso_date(newest, "newest")

    daily: list[TrendPoint] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        date_str = str(record.get("id", ""))[:10]
        try:
            record_date = _parse_iso_date(date_str, "record date")
        except ValueError:
            continue
        if record_date < oldest_date or record_date > newest_date:
            continue
        ctl = _numeric_or_none(record.get("ctl"))
        atl = _numeric_or_none(record.get("atl"))
        tsb = round(ctl - atl, 2) if ctl is not None and atl is not None else None
        daily.append(
            TrendPoint(
                date=date_str,
                ctl=ctl,
                atl=atl,
                tsb=tsb,
                ramp_rate=_numeric_or_none(record.get("rampRate")),
            )
        )
    daily.sort(key=lambda point: point.date)

    if granularity == IcuTrendGranularity.DAILY:
        points = daily
    else:
        # Bucket index counts 7-day windows backwards from newest (index 0 is
        # the most recent bucket); daily is sorted ascending so the last
        # write per bucket is its latest day. Iterating buckets in reverse
        # index order yields the series in ascending date order.
        buckets: dict[int, TrendPoint] = {}
        for point in daily:
            record_date = _parse_iso_date(point.date, "point date")
            buckets[(newest_date - record_date).days // 7] = point
        points = [buckets[index] for index in sorted(buckets, reverse=True)]

    return TrendReport(
        oldest=oldest,
        newest=newest,
        granularity=granularity.value,
        points=points,
        snapshot=daily[-1] if daily else None,
    )


# ---------------------------------------------------------------------------
# Planned Workouts & Events Models
# ---------------------------------------------------------------------------


class ListEventsInput(BaseToolModel):
    """Input parameters for retrieving calendar events and scheduled workouts."""

    oldest: str | None = Field(
        default=None,
        description="Oldest date (YYYY-MM-DD). Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str | None = Field(
        default=None,
        description="Newest date (YYYY-MM-DD). Defaults to 30 days from today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    category: str | None = Field(
        default=None,
        description="Event category filter (e.g. 'WORKOUT', 'NOTE', 'TARGET', 'RACE_A', 'RACE_B').",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )

    @model_validator(mode="after")
    def _set_default_dates(self) -> "ListEventsInput":
        """Populate default date range when not provided."""
        if self.oldest is None:
            self.oldest = date.today().isoformat()
        if self.newest is None:
            self.newest = (date.today() + timedelta(days=30)).isoformat()
        return self


class GetEventInput(BaseToolModel):
    """Input parameters for retrieving a specific calendar event or workout."""

    event_id: str = Field(
        ...,
        description="Unique event or planned workout ID.",
        min_length=1,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


class CreateEventInput(BaseToolModel):
    """Input parameters for creating a planned workout or calendar event."""

    start_date_local: str = Field(
        ...,
        description="Local start timestamp 'YYYY-MM-DDTHH:MM:SS' (e.g. '2026-08-23T08:00:00').",
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
    )
    name: str = Field(
        ..., description="Workout or event title (e.g. 'Over-Unders 3x10min').", min_length=1
    )
    type: str = Field(
        default="Ride", description="Sport type ('Ride', 'Run', 'Swim', 'WeightTraining', etc.)."
    )
    category: str = Field(
        default="WORKOUT",
        description="Category ('WORKOUT', 'NOTE', 'TARGET', 'RACE_A', 'RACE_B', 'RACE_C').",
    )
    description: str | None = Field(
        default=None, description="Human description or instructions for the workout."
    )
    workout_doc: str | None = Field(
        default=None,
        description=(
            "Intervals.icu structured workout DSL definition text, delivered via the "
            "calendar 'description' field (the API parses the DSL and compiles the "
            "structured workout on its side). Example:\n"
            "- Warm up 10m 50-65%\n"
            "3x\n"
            "- 2m 105% 90rpm\n"
            "- 2m 90% 85rpm\n"
            "- Cool down 10m 55%"
        ),
    )
    moving_time_seconds: int | None = Field(
        default=None, description="Planned duration in seconds.", ge=1
    )
    icu_training_load: float | None = Field(default=None, description="Planned TSS / load.", ge=0.0)
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )


class UpdateEventInput(BaseToolModel):
    """Input parameters for modifying a planned workout or calendar event."""

    event_id: str = Field(
        ...,
        description="ID of the event to update.",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    start_date_local: str | None = Field(
        default=None,
        description="Updated start date/time.",
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
    )
    name: str | None = Field(default=None, description="Updated title.")
    description: str | None = Field(default=None, description="Updated instructions.")
    workout_doc: str | None = Field(
        default=None,
        description=(
            "Updated structured workout DSL text, delivered via the calendar "
            "'description' field (the API parses the DSL and compiles the structured "
            "workout on its side)."
        ),
    )
    moving_time_seconds: int | None = Field(
        default=None, description="Updated duration in seconds.", ge=1
    )
    icu_training_load: float | None = Field(
        default=None, description="Updated planned load.", ge=0.0
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )


class DeleteEventInput(BaseToolModel):
    """Input parameters for deleting a planned event or workout."""

    event_id: str = Field(
        ...,
        description="ID of the event to delete.",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )


# ---------------------------------------------------------------------------
# Folders & Templates Models
# ---------------------------------------------------------------------------


class ListFoldersInput(BaseToolModel):
    """Input parameters for listing workout folders in library."""

    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )


class ListWorkoutsInput(BaseToolModel):
    """Input parameters for listing workout templates."""

    folder_id: str | None = Field(
        default=None,
        description="Filter by folder ID.",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
        pattern=r"^(0|i\d+)$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )
