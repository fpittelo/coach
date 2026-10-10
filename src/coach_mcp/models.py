"""Pydantic v2 input and output models for Coach MCP."""

from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
