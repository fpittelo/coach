"""Comprehensive tests for Pydantic v2 input validation models."""

from datetime import date
from unittest.mock import patch

import pytest
from pydantic import ValidationError

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

# ---------------------------------------------------------------------------
# Athlete Models
# ---------------------------------------------------------------------------


def test_get_athlete_profile_input_defaults():
    """Test GetAthleteProfileInput defaults and response format choices."""
    model = GetAthleteProfileInput()
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN

    model_json = GetAthleteProfileInput(athlete_id="i12345", response_format=ResponseFormat.JSON)
    assert model_json.athlete_id == "i12345"
    assert model_json.response_format == ResponseFormat.JSON


def test_get_athlete_profile_input_extra_forbid():
    """Test GetAthleteProfileInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetAthleteProfileInput(extra_field="not_allowed")  # type: ignore


def test_get_sport_settings_input_defaults():
    """Test GetSportSettingsInput defaults and overrides."""
    model = GetSportSettingsInput()
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN

    model_json = GetSportSettingsInput(athlete_id="0", response_format="json")
    assert model_json.athlete_id == "0"
    assert model_json.response_format == ResponseFormat.JSON


def test_get_sport_settings_input_extra_forbid():
    """Test GetSportSettingsInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetSportSettingsInput(unknown=True)  # type: ignore


# ---------------------------------------------------------------------------
# Activity Models
# ---------------------------------------------------------------------------


def test_list_activities_input_valid():
    """Test valid ListActivitiesInput creation."""
    model = ListActivitiesInput(
        oldest="2026-08-01",
        newest="2026-08-22",
        limit=25,
        response_format=ResponseFormat.JSON,
    )
    assert model.oldest == "2026-08-01"
    assert model.newest == "2026-08-22"
    assert model.limit == 25
    assert model.response_format == ResponseFormat.JSON


def test_list_activities_input_defaults():
    """Test ListActivitiesInput default values."""
    model = ListActivitiesInput(oldest="2026-08-01", newest="2026-08-22")
    assert model.athlete_id is None
    assert model.limit == 50
    assert model.response_format == ResponseFormat.MARKDOWN


def test_list_activities_input_invalid_date():
    """Test invalid date format validation."""
    with pytest.raises(ValidationError):
        ListActivitiesInput(oldest="invalid-date", newest="2026-08-22")

    with pytest.raises(ValidationError):
        ListActivitiesInput(oldest="2026-08-01", newest="2026/08/22")

    with pytest.raises(ValidationError):
        ListActivitiesInput(oldest="08-01-2026", newest="2026-08-22")


def test_list_activities_input_limit_bounds():
    """Test ListActivitiesInput limit range bounds."""
    with pytest.raises(ValidationError):
        ListActivitiesInput(oldest="2026-08-01", newest="2026-08-22", limit=0)

    with pytest.raises(ValidationError):
        ListActivitiesInput(oldest="2026-08-01", newest="2026-08-22", limit=101)

    valid_min = ListActivitiesInput(oldest="2026-08-01", newest="2026-08-22", limit=1)
    assert valid_min.limit == 1

    valid_max = ListActivitiesInput(oldest="2026-08-01", newest="2026-08-22", limit=100)
    assert valid_max.limit == 100


def test_list_activities_input_extra_forbid():
    """Test ListActivitiesInput rejects extra fields."""
    with pytest.raises(ValidationError):
        ListActivitiesInput(
            oldest="2026-08-01",
            newest="2026-08-22",
            extra_field="disallowed",  # type: ignore
        )


@patch("coach_mcp.models.date")
def test_list_activities_input_default_dates(mock_date):
    """Test ListActivitiesInput computes default 30-day window."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = ListActivitiesInput()
    assert model.oldest == "2026-07-30"
    assert model.newest == "2026-08-29"
    assert model.limit == 50
    assert model.response_format == ResponseFormat.MARKDOWN


@patch("coach_mcp.models.date")
def test_list_activities_input_partial_override_oldest(mock_date):
    """Test ListActivitiesInput overrides oldest while defaulting newest."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = ListActivitiesInput(oldest="2026-07-01")
    assert model.oldest == "2026-07-01"
    assert model.newest == "2026-08-29"


@patch("coach_mcp.models.date")
def test_list_activities_input_partial_override_newest(mock_date):
    """Test ListActivitiesInput overrides newest while defaulting oldest."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = ListActivitiesInput(newest="2026-08-15")
    assert model.oldest == "2026-07-30"
    assert model.newest == "2026-08-15"


def test_list_activities_input_explicit_override():
    """Test ListActivitiesInput accepts explicit date range."""
    model = ListActivitiesInput(oldest="2026-07-01", newest="2026-08-15")
    assert model.oldest == "2026-07-01"
    assert model.newest == "2026-08-15"


def test_get_activity_input_valid():
    """Test GetActivityInput validation."""
    model = GetActivityInput(activity_id="i12345678")
    assert model.activity_id == "i12345678"
    assert model.response_format == ResponseFormat.MARKDOWN

    model_json = GetActivityInput(activity_id="12345678", response_format=ResponseFormat.JSON)
    assert model_json.activity_id == "12345678"
    assert model_json.response_format == ResponseFormat.JSON


def test_get_activity_input_requires_id():
    """Test GetActivityInput requires non-empty activity_id."""
    with pytest.raises(ValidationError):
        GetActivityInput(activity_id="")

    with pytest.raises(ValidationError):
        GetActivityInput(activity_id="   ")


def test_get_activity_input_extra_forbid():
    """Test GetActivityInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetActivityInput(activity_id="i123", extra=True)  # type: ignore


def test_get_activity_streams_input_defaults():
    """Test GetActivityStreamsInput defaults."""
    model = GetActivityStreamsInput(activity_id="i123")
    assert model.activity_id == "i123"
    assert model.types == ["watts", "heartrate", "cadence", "time", "distance", "altitude"]
    assert model.response_format == ResponseFormat.MARKDOWN


def test_get_activity_streams_input_custom_types():
    """Test GetActivityStreamsInput with custom stream types."""
    model = GetActivityStreamsInput(
        activity_id="i123", types=["watts", "temp"], response_format=ResponseFormat.JSON
    )
    assert model.types == ["watts", "temp"]
    assert model.response_format == ResponseFormat.JSON


def test_get_activity_streams_input_requires_id():
    """Test GetActivityStreamsInput requires non-empty activity_id."""
    with pytest.raises(ValidationError):
        GetActivityStreamsInput(activity_id="")


def test_get_activity_streams_input_extra_forbid():
    """Test GetActivityStreamsInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetActivityStreamsInput(activity_id="i123", streams=True)  # type: ignore


def test_get_activity_intervals_input_defaults():
    """Test GetActivityIntervalsInput defaults."""
    model = GetActivityIntervalsInput(activity_id="i123")
    assert model.activity_id == "i123"
    assert model.response_format == ResponseFormat.MARKDOWN


def test_get_activity_intervals_input_requires_id():
    """Test GetActivityIntervalsInput requires non-empty activity_id."""
    with pytest.raises(ValidationError):
        GetActivityIntervalsInput(activity_id="")


def test_get_activity_intervals_input_extra_forbid():
    """Test GetActivityIntervalsInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetActivityIntervalsInput(activity_id="i123", extra=True)  # type: ignore


# ---------------------------------------------------------------------------
# Power Curve Models
# ---------------------------------------------------------------------------


def test_get_power_curve_input_defaults():
    """Test GetPowerCurveInput defaults."""
    model = GetPowerCurveInput()
    assert model.athlete_id is None
    assert model.activity_id is None
    assert model.sport_type == "Ride"
    assert model.response_format == ResponseFormat.MARKDOWN


def test_get_power_curve_input_activity_override():
    """Test GetPowerCurveInput with explicit activity_id."""
    model = GetPowerCurveInput(activity_id="i123", response_format=ResponseFormat.JSON)
    assert model.activity_id == "i123"
    assert model.athlete_id is None
    assert model.sport_type == "Ride"
    assert model.response_format == ResponseFormat.JSON


def test_get_power_curve_input_athlete_and_sport():
    """Test GetPowerCurveInput with athlete_id and sport_type."""
    model = GetPowerCurveInput(athlete_id="i456", sport_type="Run")
    assert model.athlete_id == "i456"
    assert model.sport_type == "Run"
    assert model.activity_id is None


def test_get_power_curve_input_sport_type_validation():
    """Test GetPowerCurveInput sport_type default and custom values."""
    default_model = GetPowerCurveInput()
    assert default_model.sport_type == "Ride"

    run_model = GetPowerCurveInput(sport_type="Run")
    assert run_model.sport_type == "Run"

    swim_model = GetPowerCurveInput(sport_type="Swim")
    assert swim_model.sport_type == "Swim"


def test_get_power_curve_input_extra_forbid():
    """Test GetPowerCurveInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetPowerCurveInput(extra=True)  # type: ignore


# ---------------------------------------------------------------------------
# Power Model (CP/W'/Pmax) Models
# ---------------------------------------------------------------------------


def test_get_power_model_input_defaults():
    """Test GetPowerModelInput defaults."""
    model = GetPowerModelInput()
    assert model.athlete_id is None
    assert model.sport_type == "Ride"
    assert model.response_format == ResponseFormat.MARKDOWN


def test_get_power_model_input_athlete_and_sport():
    """Test GetPowerModelInput with athlete_id and sport_type."""
    model = GetPowerModelInput(athlete_id="i456", sport_type="Run")
    assert model.athlete_id == "i456"
    assert model.sport_type == "Run"


def test_get_power_model_input_response_format():
    """Test GetPowerModelInput response format choices."""
    model_json = GetPowerModelInput(athlete_id="0", response_format=ResponseFormat.JSON)
    assert model_json.athlete_id == "0"
    assert model_json.response_format == ResponseFormat.JSON


def test_get_power_model_input_athlete_id_validation():
    """Test GetPowerModelInput athlete_id regex validation."""
    valid = GetPowerModelInput(athlete_id="i12345")
    assert valid.athlete_id == "i12345"

    with pytest.raises(ValidationError):
        GetPowerModelInput(athlete_id="invalid")


def test_get_power_model_input_extra_forbid():
    """Test GetPowerModelInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetPowerModelInput(extra=True)  # type: ignore


def test_create_activity_input_valid():
    """Test CreateActivityInput with all valid fields."""
    model = CreateActivityInput(
        name="Tempo Ride",
        type="Ride",
        start_date_local="2026-08-22T09:00:00",
        moving_time_seconds=3600,
        elapsed_time_seconds=3700,
        distance_meters=45000.5,
        average_watts=210.5,
        average_heartrate=145.0,
        icu_training_load=85.0,
        description="Steady tempo effort",
        athlete_id="0",
    )
    assert model.name == "Tempo Ride"
    assert model.type == "Ride"
    assert model.moving_time_seconds == 3600
    assert model.elapsed_time_seconds == 3700
    assert model.distance_meters == 45000.5
    assert model.average_watts == 210.5
    assert model.average_heartrate == 145.0
    assert model.icu_training_load == 85.0
    assert model.description == "Steady tempo effort"
    assert model.athlete_id == "0"


def test_create_activity_input_defaults():
    """Test CreateActivityInput defaults for optional fields."""
    model = CreateActivityInput(
        name="Morning Run",
        type="Run",
        start_date_local="2026-08-22T07:00:00",
        moving_time_seconds=1800,
    )
    assert model.elapsed_time_seconds is None
    assert model.distance_meters is None
    assert model.average_watts is None
    assert model.average_heartrate is None
    assert model.icu_training_load is None
    assert model.description is None
    assert model.athlete_id is None


def test_create_activity_input_range_bounds():
    """Test CreateActivityInput numeric range bounds."""
    with pytest.raises(ValidationError):
        CreateActivityInput(
            name="Bad",
            type="Ride",
            start_date_local="2026-08-22T09:00:00",
            moving_time_seconds=0,
        )

    with pytest.raises(ValidationError):
        CreateActivityInput(
            name="Bad",
            type="Ride",
            start_date_local="2026-08-22T09:00:00",
            moving_time_seconds=3600,
            elapsed_time_seconds=0,
        )

    with pytest.raises(ValidationError):
        CreateActivityInput(
            name="Bad",
            type="Ride",
            start_date_local="2026-08-22T09:00:00",
            moving_time_seconds=3600,
            distance_meters=-1.0,
        )

    with pytest.raises(ValidationError):
        CreateActivityInput(
            name="Bad",
            type="Ride",
            start_date_local="2026-08-22T09:00:00",
            moving_time_seconds=3600,
            average_watts=-1.0,
        )


def test_create_activity_input_extra_forbid():
    """Test CreateActivityInput rejects extra fields."""
    with pytest.raises(ValidationError):
        CreateActivityInput(
            name="Tempo Ride",
            type="Ride",
            start_date_local="2026-08-22T10:00:00",
            moving_time_seconds=3600,
            unexpected_field="disallowed",  # type: ignore
        )


def test_update_activity_input_valid():
    """Test UpdateActivityInput with valid fields."""
    model = UpdateActivityInput(
        activity_id="i123",
        name="Updated Ride",
        description="Felt good",
        perceived_exertion=7.5,
        feel=2,
        icu_training_load=90.0,
    )
    assert model.activity_id == "i123"
    assert model.name == "Updated Ride"
    assert model.description == "Felt good"
    assert model.perceived_exertion == 7.5
    assert model.feel == 2
    assert model.icu_training_load == 90.0


def test_update_activity_input_defaults():
    """Test UpdateActivityInput defaults."""
    model = UpdateActivityInput(activity_id="i123")
    assert model.name is None
    assert model.description is None
    assert model.perceived_exertion is None
    assert model.feel is None
    assert model.icu_training_load is None


def test_update_activity_input_range_bounds():
    """Test UpdateActivityInput numeric range bounds."""
    with pytest.raises(ValidationError):
        UpdateActivityInput(activity_id="i123", perceived_exertion=0.5)

    with pytest.raises(ValidationError):
        UpdateActivityInput(activity_id="i123", perceived_exertion=11.0)

    with pytest.raises(ValidationError):
        UpdateActivityInput(activity_id="i123", feel=0)

    with pytest.raises(ValidationError):
        UpdateActivityInput(activity_id="i123", feel=6)

    with pytest.raises(ValidationError):
        UpdateActivityInput(activity_id="i123", icu_training_load=-1.0)


def test_update_activity_input_extra_forbid():
    """Test UpdateActivityInput rejects extra fields."""
    with pytest.raises(ValidationError):
        UpdateActivityInput(activity_id="i123", extra=True)  # type: ignore


def test_delete_activity_input_valid():
    """Test DeleteActivityInput validation."""
    model = DeleteActivityInput(activity_id="i123")
    assert model.activity_id == "i123"


def test_delete_activity_input_extra_forbid():
    """Test DeleteActivityInput rejects extra fields."""
    with pytest.raises(ValidationError):
        DeleteActivityInput(activity_id="i123", extra=True)  # type: ignore


# ---------------------------------------------------------------------------
# Wellness & Metrics Models
# ---------------------------------------------------------------------------


def test_get_wellness_input_valid():
    """Test GetWellnessInput validation."""
    model = GetWellnessInput(
        oldest="2026-08-01",
        newest="2026-08-22",
        athlete_id="0",
        response_format=ResponseFormat.JSON,
    )
    assert model.oldest == "2026-08-01"
    assert model.newest == "2026-08-22"
    assert model.athlete_id == "0"
    assert model.response_format == ResponseFormat.JSON


def test_get_wellness_input_defaults():
    """Test GetWellnessInput defaults."""
    model = GetWellnessInput(oldest="2026-08-01", newest="2026-08-22")
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN


def test_get_wellness_input_invalid_date():
    """Test GetWellnessInput date format validation."""
    with pytest.raises(ValidationError):
        GetWellnessInput(oldest="not-a-date", newest="2026-08-22")

    with pytest.raises(ValidationError):
        GetWellnessInput(oldest="2026-08-01", newest="2026/08/22")


def test_get_wellness_input_extra_forbid():
    """Test GetWellnessInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetWellnessInput(oldest="2026-08-01", newest="2026-08-22", extra=True)  # type: ignore


@patch("coach_mcp.models.date")
def test_get_wellness_input_default_dates(mock_date):
    """Test GetWellnessInput computes default 7-day window."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = GetWellnessInput()
    assert model.oldest == "2026-08-22"
    assert model.newest == "2026-08-29"
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN


@patch("coach_mcp.models.date")
def test_get_wellness_input_partial_override_oldest(mock_date):
    """Test GetWellnessInput overrides oldest while defaulting newest."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = GetWellnessInput(oldest="2026-08-01")
    assert model.oldest == "2026-08-01"
    assert model.newest == "2026-08-29"


@patch("coach_mcp.models.date")
def test_get_wellness_input_partial_override_newest(mock_date):
    """Test GetWellnessInput overrides newest while defaulting oldest."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = GetWellnessInput(newest="2026-08-15")
    assert model.oldest == "2026-08-22"
    assert model.newest == "2026-08-15"


def test_get_wellness_input_explicit_override():
    """Test GetWellnessInput accepts explicit date range."""
    model = GetWellnessInput(oldest="2026-08-01", newest="2026-08-15")
    assert model.oldest == "2026-08-01"
    assert model.newest == "2026-08-15"


def test_record_wellness_input_valid():
    """Test RecordWellnessInput with all valid fields."""
    model = RecordWellnessInput(
        date="2026-08-22",
        restingHR=48,
        hrv=65.5,
        weight=72.5,
        sleepSecs=28800,
        sleepQuality=2,
        readiness=85.5,
        soreness=2,
        fatigue=2,
        stress=2,
        mood=1,
        injury=1,
        comments="Slept well",
        athlete_id="0",
    )
    assert model.date == "2026-08-22"
    assert model.restingHR == 48
    assert model.hrv == 65.5
    assert model.weight == 72.5
    assert model.sleepSecs == 28800
    assert model.sleepQuality == 2
    assert model.readiness == 85.5
    assert model.soreness == 2
    assert model.fatigue == 2
    assert model.stress == 2
    assert model.mood == 1
    assert model.injury == 1
    assert model.comments == "Slept well"
    assert model.athlete_id == "0"


def test_record_wellness_input_defaults():
    """Test RecordWellnessInput defaults."""
    model = RecordWellnessInput(date="2026-08-22")
    assert model.restingHR is None
    assert model.hrv is None
    assert model.weight is None
    assert model.sleepSecs is None
    assert model.sleepQuality is None
    assert model.readiness is None
    assert model.soreness is None
    assert model.fatigue is None
    assert model.stress is None
    assert model.mood is None
    assert model.injury is None
    assert model.comments is None
    assert model.athlete_id is None


def test_record_wellness_input_range_validation():
    """Test bounds validation on RecordWellnessInput numeric fields."""
    valid_model = RecordWellnessInput(
        date="2026-08-22",
        restingHR=48,
        readiness=85.5,
        soreness=2,
    )
    assert valid_model.restingHR == 48
    assert valid_model.readiness == 85.5

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", readiness=150.0)  # max is 100

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", restingHR=20)  # min is 30

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", restingHR=200)  # max is 150

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", weight=20.0)  # min is 30

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", weight=300.0)  # max is 250

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", sleepQuality=0)  # min is 1

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", sleepQuality=5)  # max is 4

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", soreness=0)  # min is 1

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", soreness=5)  # max is 4

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", hrv=-1.0)  # min is 0


def test_record_wellness_input_invalid_date():
    """Test RecordWellnessInput date format validation."""
    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026/08/22")

    with pytest.raises(ValidationError):
        RecordWellnessInput(date="08-22-2026")


def test_record_wellness_input_extra_forbid():
    """Test RecordWellnessInput rejects extra fields."""
    with pytest.raises(ValidationError):
        RecordWellnessInput(date="2026-08-22", extra=True)  # type: ignore


def test_get_fitness_summary_input_valid():
    """Test GetFitnessSummaryInput validation."""
    model = GetFitnessSummaryInput(
        oldest="2026-08-01", newest="2026-08-22", response_format=ResponseFormat.JSON
    )
    assert model.oldest == "2026-08-01"
    assert model.newest == "2026-08-22"
    assert model.response_format == ResponseFormat.JSON


def test_get_fitness_summary_input_defaults():
    """Test GetFitnessSummaryInput defaults."""
    model = GetFitnessSummaryInput(oldest="2026-08-01", newest="2026-08-22")
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN


def test_get_fitness_summary_input_invalid_date():
    """Test GetFitnessSummaryInput date format validation."""
    with pytest.raises(ValidationError):
        GetFitnessSummaryInput(oldest="2026-08-01", newest="not-a-date")


def test_get_fitness_summary_input_extra_forbid():
    """Test GetFitnessSummaryInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetFitnessSummaryInput(oldest="2026-08-01", newest="2026-08-22", extra=True)  # type: ignore


@patch("coach_mcp.models.date")
def test_get_fitness_summary_input_default_dates(mock_date):
    """Test GetFitnessSummaryInput computes default 42-day window."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = GetFitnessSummaryInput()
    assert model.oldest == "2026-07-18"
    assert model.newest == "2026-08-29"
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN


@patch("coach_mcp.models.date")
def test_get_fitness_summary_input_partial_override_oldest(mock_date):
    """Test GetFitnessSummaryInput overrides oldest while defaulting newest."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = GetFitnessSummaryInput(oldest="2026-07-01")
    assert model.oldest == "2026-07-01"
    assert model.newest == "2026-08-29"


@patch("coach_mcp.models.date")
def test_get_fitness_summary_input_partial_override_newest(mock_date):
    """Test GetFitnessSummaryInput overrides newest while defaulting oldest."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = GetFitnessSummaryInput(newest="2026-08-15")
    assert model.oldest == "2026-07-18"
    assert model.newest == "2026-08-15"


def test_get_fitness_summary_input_explicit_override():
    """Test GetFitnessSummaryInput accepts explicit date range."""
    model = GetFitnessSummaryInput(oldest="2026-07-01", newest="2026-08-15")
    assert model.oldest == "2026-07-01"
    assert model.newest == "2026-08-15"


def test_get_readiness_dashboard_input_defaults():
    """Test GetReadinessDashboardInput defaults."""
    model = GetReadinessDashboardInput()
    assert model.athlete_id is None
    assert model.days == 7
    assert model.response_format == ResponseFormat.MARKDOWN


def test_get_readiness_dashboard_input_valid():
    """Test GetReadinessDashboardInput with explicit values."""
    model = GetReadinessDashboardInput(
        athlete_id="i12345", days=14, response_format=ResponseFormat.JSON
    )
    assert model.athlete_id == "i12345"
    assert model.days == 14
    assert model.response_format == ResponseFormat.JSON


def test_get_readiness_dashboard_input_days_bounds():
    """Test GetReadinessDashboardInput days range bounds."""
    with pytest.raises(ValidationError):
        GetReadinessDashboardInput(days=0)

    with pytest.raises(ValidationError):
        GetReadinessDashboardInput(days=31)

    valid_min = GetReadinessDashboardInput(days=1)
    assert valid_min.days == 1

    valid_max = GetReadinessDashboardInput(days=30)
    assert valid_max.days == 30


def test_get_readiness_dashboard_input_athlete_id_validation():
    """Test GetReadinessDashboardInput athlete_id regex validation."""
    valid = GetReadinessDashboardInput(athlete_id="0")
    assert valid.athlete_id == "0"

    with pytest.raises(ValidationError):
        GetReadinessDashboardInput(athlete_id="invalid")


def test_get_readiness_dashboard_input_extra_forbid():
    """Test GetReadinessDashboardInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetReadinessDashboardInput(extra=True)  # type: ignore


# ---------------------------------------------------------------------------
# Planned Workouts & Events Models
# ---------------------------------------------------------------------------


def test_list_events_input_valid():
    """Test ListEventsInput validation."""
    model = ListEventsInput(
        oldest="2026-08-01",
        newest="2026-08-22",
        category="WORKOUT",
        athlete_id="0",
        response_format=ResponseFormat.JSON,
    )
    assert model.oldest == "2026-08-01"
    assert model.newest == "2026-08-22"
    assert model.category == "WORKOUT"
    assert model.athlete_id == "0"
    assert model.response_format == ResponseFormat.JSON


def test_list_events_input_defaults():
    """Test ListEventsInput defaults."""
    model = ListEventsInput(oldest="2026-08-01", newest="2026-08-22")
    assert model.athlete_id is None
    assert model.category is None
    assert model.response_format == ResponseFormat.MARKDOWN


def test_list_events_input_invalid_date():
    """Test ListEventsInput date format validation."""
    with pytest.raises(ValidationError):
        ListEventsInput(oldest="2026-08-01", newest="2026.08.22")


def test_list_events_input_extra_forbid():
    """Test ListEventsInput rejects extra fields."""
    with pytest.raises(ValidationError):
        ListEventsInput(oldest="2026-08-01", newest="2026-08-22", extra=True)  # type: ignore


@patch("coach_mcp.models.date")
def test_list_events_input_default_dates(mock_date):
    """Test ListEventsInput computes default 30-day forward window."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = ListEventsInput()
    assert model.oldest == "2026-08-29"
    assert model.newest == "2026-09-28"
    assert model.athlete_id is None
    assert model.category is None
    assert model.response_format == ResponseFormat.MARKDOWN


@patch("coach_mcp.models.date")
def test_list_events_input_partial_override_oldest(mock_date):
    """Test ListEventsInput overrides oldest while defaulting newest."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = ListEventsInput(oldest="2026-08-01")
    assert model.oldest == "2026-08-01"
    assert model.newest == "2026-09-28"


@patch("coach_mcp.models.date")
def test_list_events_input_partial_override_newest(mock_date):
    """Test ListEventsInput overrides newest while defaulting oldest."""
    mock_date.today.return_value = date(2026, 8, 29)
    model = ListEventsInput(newest="2026-09-15")
    assert model.oldest == "2026-08-29"
    assert model.newest == "2026-09-15"


def test_list_events_input_explicit_override():
    """Test ListEventsInput accepts explicit date range."""
    model = ListEventsInput(oldest="2026-08-01", newest="2026-09-15")
    assert model.oldest == "2026-08-01"
    assert model.newest == "2026-09-15"


def test_get_event_input_defaults():
    """Test GetEventInput defaults and validation."""
    model = GetEventInput(event_id="evt_12345")
    assert model.event_id == "evt_12345"
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN


def test_get_event_input_requires_event_id():
    """Test GetEventInput requires a non-empty event_id."""
    with pytest.raises(ValidationError):
        GetEventInput(event_id="")

    with pytest.raises(ValidationError):
        GetEventInput(event_id="   ")


def test_get_event_input_extra_forbid():
    """Test GetEventInput rejects extra fields."""
    with pytest.raises(ValidationError):
        GetEventInput(event_id="evt_123", extra=True)  # type: ignore


def test_create_event_input_valid():
    """Test CreateEventInput with all valid fields."""
    model = CreateEventInput(
        start_date_local="2026-08-23T08:00:00",
        name="VO2max 4x4min",
        type="Ride",
        category="WORKOUT",
        description="Hard intervals",
        workout_doc="- 10m warmup\n4x\n- 4m 115%\n- 3m 50%\n- 10m cooldown",
        moving_time_seconds=3600,
        icu_training_load=120.0,
        athlete_id="0",
    )
    assert model.start_date_local == "2026-08-23T08:00:00"
    assert model.name == "VO2max 4x4min"
    assert model.type == "Ride"
    assert model.category == "WORKOUT"
    assert model.description == "Hard intervals"
    assert model.workout_doc is not None
    assert model.moving_time_seconds == 3600
    assert model.icu_training_load == 120.0
    assert model.athlete_id == "0"


def test_create_event_input_defaults():
    """Test CreateEventInput defaults."""
    model = CreateEventInput(start_date_local="2026-08-23T08:00:00", name="Easy Ride")
    assert model.type == "Ride"
    assert model.category == "WORKOUT"
    assert model.description is None
    assert model.workout_doc is None
    assert model.moving_time_seconds is None
    assert model.icu_training_load is None
    assert model.athlete_id is None


def test_create_event_dsl():
    """Test creating structured workout event input."""
    model = CreateEventInput(
        start_date_local="2026-08-23T08:00:00",
        name="VO2max 4x4min",
        type="Ride",
        workout_doc="- 10m warmup\n4x\n- 4m 115%\n- 3m 50%\n- 10m cooldown",
    )
    assert "VO2max" in model.name
    assert model.workout_doc is not None


def test_create_event_input_range_bounds():
    """Test CreateEventInput numeric range bounds."""
    with pytest.raises(ValidationError):
        CreateEventInput(
            start_date_local="2026-08-23T08:00:00",
            name="Bad",
            moving_time_seconds=0,
        )

    with pytest.raises(ValidationError):
        CreateEventInput(
            start_date_local="2026-08-23T08:00:00",
            name="Bad",
            icu_training_load=-1.0,
        )


def test_create_event_input_extra_forbid():
    """Test CreateEventInput rejects extra fields."""
    with pytest.raises(ValidationError):
        CreateEventInput(
            start_date_local="2026-08-23T08:00:00",
            name="Bad",
            extra=True,  # type: ignore
        )


def test_update_event_input_valid():
    """Test UpdateEventInput with valid fields."""
    model = UpdateEventInput(
        event_id="evt_123",
        start_date_local="2026-08-24T08:00:00",
        name="Updated Workout",
        description="Updated instructions",
        workout_doc="- 10m warmup",
        moving_time_seconds=3600,
        icu_training_load=100.0,
        athlete_id="0",
    )
    assert model.event_id == "evt_123"
    assert model.start_date_local == "2026-08-24T08:00:00"
    assert model.name == "Updated Workout"
    assert model.description == "Updated instructions"
    assert model.workout_doc == "- 10m warmup"
    assert model.moving_time_seconds == 3600
    assert model.icu_training_load == 100.0
    assert model.athlete_id == "0"


def test_update_event_input_defaults():
    """Test UpdateEventInput defaults."""
    model = UpdateEventInput(event_id="evt_123")
    assert model.start_date_local is None
    assert model.name is None
    assert model.description is None
    assert model.workout_doc is None
    assert model.moving_time_seconds is None
    assert model.icu_training_load is None
    assert model.athlete_id is None


def test_update_event_input_range_bounds():
    """Test UpdateEventInput numeric range bounds."""
    with pytest.raises(ValidationError):
        UpdateEventInput(event_id="evt_123", moving_time_seconds=0)

    with pytest.raises(ValidationError):
        UpdateEventInput(event_id="evt_123", icu_training_load=-1.0)


def test_update_event_input_extra_forbid():
    """Test UpdateEventInput rejects extra fields."""
    with pytest.raises(ValidationError):
        UpdateEventInput(event_id="evt_123", extra=True)  # type: ignore


def test_delete_event_input_valid():
    """Test DeleteEventInput validation."""
    model = DeleteEventInput(event_id="evt_123")
    assert model.event_id == "evt_123"

    model_with_athlete = DeleteEventInput(event_id="evt_123", athlete_id="i456")
    assert model_with_athlete.athlete_id == "i456"


def test_delete_event_input_extra_forbid():
    """Test DeleteEventInput rejects extra fields."""
    with pytest.raises(ValidationError):
        DeleteEventInput(event_id="evt_123", extra=True)  # type: ignore


# ---------------------------------------------------------------------------
# Folders & Templates Models
# ---------------------------------------------------------------------------


def test_list_folders_input_defaults():
    """Test ListFoldersInput defaults."""
    model = ListFoldersInput()
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN

    model_json = ListFoldersInput(athlete_id="0", response_format=ResponseFormat.JSON)
    assert model_json.athlete_id == "0"
    assert model_json.response_format == ResponseFormat.JSON


def test_list_folders_input_extra_forbid():
    """Test ListFoldersInput rejects extra fields."""
    with pytest.raises(ValidationError):
        ListFoldersInput(extra=True)  # type: ignore


def test_list_workouts_input_defaults():
    """Test ListWorkoutsInput defaults."""
    model = ListWorkoutsInput()
    assert model.folder_id is None
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN

    model_filtered = ListWorkoutsInput(
        folder_id="folder_1", athlete_id="0", response_format=ResponseFormat.JSON
    )
    assert model_filtered.folder_id == "folder_1"
    assert model_filtered.athlete_id == "0"
    assert model_filtered.response_format == ResponseFormat.JSON


def test_list_workouts_input_extra_forbid():
    """Test ListWorkoutsInput rejects extra fields."""
    with pytest.raises(ValidationError):
        ListWorkoutsInput(extra=True)  # type: ignore


def test_list_workouts_input_folder_id_validation():
    """Test ListWorkoutsInput validates folder_id regex."""
    valid = ListWorkoutsInput(folder_id="folder-123_abc")
    assert valid.folder_id == "folder-123_abc"

    with pytest.raises(ValidationError):
        ListWorkoutsInput(folder_id="../../etc/passwd")
