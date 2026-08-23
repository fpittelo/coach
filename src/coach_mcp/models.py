"""Pydantic v2 input and output models for Coach MCP."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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

    oldest: str = Field(
        ...,
        description="Start date in ISO format YYYY-MM-DD (e.g. '2026-08-01').",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str = Field(
        ...,
        description="End date in ISO format YYYY-MM-DD (e.g. '2026-08-22').",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(
        default=None,
        description="Athlete ID ('0' or None for self).",
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


class GetActivityInput(BaseToolModel):
    """Input parameters for retrieving detailed activity data."""

    activity_id: str = Field(
        ...,
        description="Unique activity ID (e.g. 'i12345678' or numeric ID '12345678').",
        min_length=1,
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
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")


class UpdateActivityInput(BaseToolModel):
    """Input parameters for modifying an existing activity."""

    activity_id: str = Field(..., description="Activity ID to update.")
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

    activity_id: str = Field(..., description="Activity ID to delete.")


# ---------------------------------------------------------------------------
# Wellness & Metrics Models
# ---------------------------------------------------------------------------


class GetWellnessInput(BaseToolModel):
    """Input parameters for fetching wellness & fitness history."""

    oldest: str = Field(
        ...,
        description="Start date in ISO format YYYY-MM-DD.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str = Field(
        ...,
        description="End date in ISO format YYYY-MM-DD.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )


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
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")


class GetFitnessSummaryInput(BaseToolModel):
    """Input parameters for calculating CTL (Fitness), ATL (Fatigue), and TSB (Form)."""

    oldest: str = Field(
        ...,
        description="Start date in ISO format YYYY-MM-DD.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str = Field(
        ...,
        description="End date in ISO format YYYY-MM-DD.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )


# ---------------------------------------------------------------------------
# Planned Workouts & Events Models
# ---------------------------------------------------------------------------


class ListEventsInput(BaseToolModel):
    """Input parameters for retrieving calendar events and scheduled workouts."""

    oldest: str = Field(
        ...,
        description="Start date in ISO format YYYY-MM-DD.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    newest: str = Field(
        ...,
        description="End date in ISO format YYYY-MM-DD.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")
    category: str | None = Field(
        default=None,
        description="Event category filter (e.g. 'WORKOUT', 'NOTE', 'TARGET', 'RACE_A', 'RACE_B').",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )


class GetEventInput(BaseToolModel):
    """Input parameters for retrieving a specific calendar event or workout."""

    event_id: str = Field(..., description="Unique event or planned workout ID.", min_length=1)
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


class CreateEventInput(BaseToolModel):
    """Input parameters for creating a planned workout or calendar event."""

    start_date_local: str = Field(
        ...,
        description="Local start timestamp 'YYYY-MM-DDTHH:MM:SS' (e.g. '2026-08-23T08:00:00').",
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
            "Intervals.icu structured workout DSL definition text. Example:\n"
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
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")


class UpdateEventInput(BaseToolModel):
    """Input parameters for modifying a planned workout or calendar event."""

    event_id: str = Field(..., description="ID of the event to update.")
    start_date_local: str | None = Field(default=None, description="Updated start date/time.")
    name: str | None = Field(default=None, description="Updated title.")
    description: str | None = Field(default=None, description="Updated instructions.")
    workout_doc: str | None = Field(default=None, description="Updated structured workout DSL.")
    moving_time_seconds: int | None = Field(
        default=None, description="Updated duration in seconds.", ge=1
    )
    icu_training_load: float | None = Field(
        default=None, description="Updated planned load.", ge=0.0
    )
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")


class DeleteEventInput(BaseToolModel):
    """Input parameters for deleting a planned event or workout."""

    event_id: str = Field(..., description="ID of the event to delete.")
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")


# ---------------------------------------------------------------------------
# Folders & Templates Models
# ---------------------------------------------------------------------------


class ListFoldersInput(BaseToolModel):
    """Input parameters for listing workout folders in library."""

    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )


class ListWorkoutsInput(BaseToolModel):
    """Input parameters for listing workout templates."""

    folder_id: str | None = Field(default=None, description="Filter by folder ID.")
    athlete_id: str | None = Field(default=None, description="Athlete ID ('0' or None for self).")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format."
    )
