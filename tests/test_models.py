"""Comprehensive tests for Pydantic v2 input validation models."""

import json
from datetime import date
from typing import Any
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
    IcuActivityType,
    IcuAddSessionCommentInput,
    IcuBatchCreateEventsInput,
    IcuBatchEventOutcome,
    IcuEventDraft,
    IcuGetCompletedSessionsInput,
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
    WellnessRecordItem,
    WorkoutComplianceEvent,
    build_workout_compliance_report,
    project_completed_sessions,
    project_wellness_days,
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

    model_json = GetSportSettingsInput(athlete_id="0", response_format=ResponseFormat.JSON)
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


def test_wellness_record_item_valid():
    """Test WellnessRecordItem with all valid fields."""
    item = WellnessRecordItem(
        date="2026-08-22",
        restingHR=48,
        hrv=65.5,
        weight=72.5,
        sleepSecs=28800,
        sleepQuality=3,
        readiness=85.5,
        soreness=2,
        fatigue=2,
        stress=2,
        mood=3,
        injury=1,
        comments="Slept well",
    )
    assert item.date == "2026-08-22"
    assert item.restingHR == 48
    assert item.hrv == 65.5
    assert item.weight == 72.5
    assert item.sleepSecs == 28800
    assert item.sleepQuality == 3
    assert item.readiness == 85.5
    assert item.soreness == 2
    assert item.fatigue == 2
    assert item.stress == 2
    assert item.mood == 3
    assert item.injury == 1
    assert item.comments == "Slept well"


def test_wellness_record_item_defaults():
    """Test WellnessRecordItem defaults."""
    item = WellnessRecordItem(date="2026-08-22")
    assert item.restingHR is None
    assert item.hrv is None
    assert item.weight is None
    assert item.sleepSecs is None
    assert item.sleepQuality is None
    assert item.readiness is None
    assert item.soreness is None
    assert item.fatigue is None
    assert item.stress is None
    assert item.mood is None
    assert item.injury is None
    assert item.comments is None


def test_wellness_record_item_invalid_date():
    """Test WellnessRecordItem date format validation."""
    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026/08/22")

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="08-22-2026")


def test_wellness_record_item_range_validation():
    """Test bounds validation on WellnessRecordItem numeric fields."""
    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", restingHR=20)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", restingHR=200)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", weight=20.0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", weight=300.0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", sleepQuality=0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", sleepQuality=5)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", readiness=-1.0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", readiness=101.0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", hrv=-1.0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", soreness=0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", soreness=5)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", fatigue=0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", stress=5)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", mood=0)

    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", injury=5)


def test_wellness_record_item_extra_forbid():
    """Test WellnessRecordItem rejects extra fields."""
    with pytest.raises(ValidationError):
        WellnessRecordItem(date="2026-08-22", extra=True)  # type: ignore


def test_record_wellness_bulk_input_valid():
    """Test RecordWellnessBulkInput with valid records list."""
    model = RecordWellnessBulkInput(
        records=[
            WellnessRecordItem(date="2026-08-22", restingHR=48),
            WellnessRecordItem(date="2026-08-23", readiness=85.5),
        ],
        athlete_id="0",
        response_format=ResponseFormat.JSON,
    )
    assert len(model.records) == 2
    assert model.records[0].date == "2026-08-22"
    assert model.records[1].date == "2026-08-23"
    assert model.athlete_id == "0"
    assert model.response_format == ResponseFormat.JSON


def test_record_wellness_bulk_input_min_length():
    """Test RecordWellnessBulkInput requires at least one record."""
    with pytest.raises(ValidationError):
        RecordWellnessBulkInput(records=[])


def test_record_wellness_bulk_input_max_length():
    """Test RecordWellnessBulkInput enforces maximum 100 records."""
    valid = RecordWellnessBulkInput(records=[WellnessRecordItem(date="2026-08-22")] * 100)
    assert len(valid.records) == 100

    with pytest.raises(ValidationError):
        RecordWellnessBulkInput(records=[WellnessRecordItem(date="2026-08-22")] * 101)


def test_record_wellness_bulk_input_athlete_id_validation():
    """Test RecordWellnessBulkInput athlete_id regex validation."""
    valid = RecordWellnessBulkInput(
        records=[WellnessRecordItem(date="2026-08-22")], athlete_id="i12345"
    )
    assert valid.athlete_id == "i12345"

    with pytest.raises(ValidationError):
        RecordWellnessBulkInput(
            records=[WellnessRecordItem(date="2026-08-22")], athlete_id="invalid"
        )


def test_record_wellness_bulk_input_extra_forbid():
    """Test RecordWellnessBulkInput rejects extra fields."""
    with pytest.raises(ValidationError):
        RecordWellnessBulkInput(
            records=[WellnessRecordItem(date="2026-08-22")], extra=True  # type: ignore
        )


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


# ---------------------------------------------------------------------------
# ICU Bounded Wellness Models (#84)
# ---------------------------------------------------------------------------


@patch("coach_mcp.models.date")
def test_icu_get_wellness_input_default_dates(mock_date):
    """Test IcuGetWellnessInput defaults to a 30-day window ending today."""
    mock_date.today.return_value = date(2026, 10, 10)
    model = IcuGetWellnessInput()
    assert model.oldest == "2026-09-10"
    assert model.newest == "2026-10-10"
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN


@patch("coach_mcp.models.date")
def test_icu_get_wellness_input_explicit_dates_preserved(mock_date):
    """Test IcuGetWellnessInput keeps an explicit in-bounds date range."""
    mock_date.today.return_value = date(2026, 10, 10)
    model = IcuGetWellnessInput(oldest="2026-09-01", newest="2026-09-30")
    assert model.oldest == "2026-09-01"
    assert model.newest == "2026-09-30"


@patch("coach_mcp.models.date")
def test_icu_get_wellness_input_partial_override_oldest(mock_date):
    """Test IcuGetWellnessInput fills newest from today when only oldest given."""
    mock_date.today.return_value = date(2026, 10, 10)
    model = IcuGetWellnessInput(oldest="2026-10-01")
    assert model.oldest == "2026-10-01"
    assert model.newest == "2026-10-10"


@patch("coach_mcp.models.date")
def test_icu_get_wellness_input_clamps_oldest_to_90_day_span(mock_date):
    """Binding condition 1: oldest is clamped server-side to a <=90-day span."""
    mock_date.today.return_value = date(2026, 10, 10)
    model = IcuGetWellnessInput(oldest="2026-01-01", newest="2026-10-10")
    # 2026-01-01 -> 2026-10-10 spans 282 days; clamped to newest - 90 days.
    assert model.newest == "2026-10-10"
    assert model.oldest == "2026-07-12"


def test_icu_get_wellness_input_allows_full_90_day_span():
    """A range of exactly 90 days is accepted without clamping."""
    model = IcuGetWellnessInput(oldest="2026-07-12", newest="2026-10-10")
    assert model.oldest == "2026-07-12"
    assert model.newest == "2026-10-10"


def test_icu_get_wellness_input_rejects_oldest_after_newest():
    """Test IcuGetWellnessInput rejects an inverted date range."""
    with pytest.raises(ValidationError):
        IcuGetWellnessInput(oldest="2026-10-10", newest="2026-01-01")


def test_icu_get_wellness_input_rejects_impossible_calendar_dates():
    """Test IcuGetWellnessInput rejects well-formed but impossible dates."""
    with pytest.raises(ValidationError):
        IcuGetWellnessInput(oldest="2026-02-30", newest="2026-10-10")


def test_icu_get_wellness_input_rejects_bad_date_format():
    """Test IcuGetWellnessInput rejects non-ISO date shapes."""
    with pytest.raises(ValidationError):
        IcuGetWellnessInput(oldest="01/02/2026", newest="2026-10-10")


def test_icu_get_wellness_input_extra_forbid():
    """Test IcuGetWellnessInput rejects extra fields."""
    with pytest.raises(ValidationError):
        IcuGetWellnessInput(extra=True)  # type: ignore


def test_wellness_day_projection_exposes_whitelist_only():
    """Binding condition 2: projection drops every non-whitelisted ICU field."""
    raw = {
        "id": "2026-10-09",
        "restingHR": 48,
        "hrv": 62.5,
        "weight": 70.2,
        "sleepSecs": 28800,
        "sleepQuality": 3,
        "readiness": 88.0,
        "soreness": 2,
        "fatigue": 2,
        "stress": 2,
        "mood": 2,
        "injury": 1,
        "comments": "felt great",
        "measurements": {"bp": "120/80"},
        "ctl": 55.0,
        "atl": 65.0,
        "tsbRaw": -10.0,
        "someUnknownIcuField": "leak-attempt",
    }
    projected = project_wellness_days([raw])
    assert len(projected) == 1
    dumped = projected[0].model_dump()
    assert set(dumped.keys()) == {
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
    assert dumped["date"] == "2026-10-09"
    assert dumped["sleep_hours"] == 8.0
    assert dumped["hrv"] == 62.5
    assert dumped["readiness"] == 88.0
    assert dumped["ctl"] == 55.0
    assert dumped["atl"] == 65.0
    # Never raw pass-through: non-whitelisted values are absent.
    assert "weight" not in dumped
    assert "restingHR" not in dumped
    assert "mood" not in dumped
    assert "injury" not in dumped
    assert "comments" not in dumped
    assert "measurements" not in dumped
    assert "someUnknownIcuField" not in dumped


def test_wellness_day_projection_derives_tsb_from_ctl_atl():
    """TSB is derived server-side as ctl - atl."""
    projected = project_wellness_days([{"id": "2026-10-09", "ctl": 55.0, "atl": 65.0}])
    assert projected[0].tsb == -10.0


def test_wellness_day_projection_tsb_none_when_load_missing():
    """TSB is None when ctl or atl is absent."""
    projected = project_wellness_days([{"id": "2026-10-09", "ctl": 55.0}])
    assert projected[0].tsb is None


def test_wellness_day_projection_missing_fields_are_none():
    """Missing whitelisted fields project as None, never as raw defaults."""
    projected = project_wellness_days([{"id": "2026-10-09"}])
    day = projected[0]
    assert day.sleep_hours is None
    assert day.hrv is None
    assert day.soreness is None
    assert day.fatigue is None
    assert day.stress is None
    assert day.readiness is None
    assert day.ctl is None
    assert day.atl is None
    assert day.tsb is None


def test_wellness_day_projection_ignores_non_numeric_values():
    """Non-numeric ICU values are dropped instead of passing through."""
    projected = project_wellness_days(
        [{"id": "2026-10-09", "hrv": "not-a-number", "readiness": True}]
    )
    day = projected[0]
    assert day.hrv is None
    assert day.readiness is None


def test_project_wellness_days_empty():
    """An empty ICU payload projects to an empty list."""
    assert project_wellness_days([]) == []


# ---------------------------------------------------------------------------
# ICU Session Comment Models (#85)
# ---------------------------------------------------------------------------


def test_icu_add_session_comment_input_defaults():
    """Test IcuAddSessionCommentInput defaults to unconfirmed (write gate shut)."""
    model = IcuAddSessionCommentInput(activity_id="i12345678", comment="Great effort today.")
    assert model.confirmed is False
    assert model.activity_id == "i12345678"


def test_icu_add_session_comment_input_accepts_valid_comment():
    """Test IcuAddSessionCommentInput accepts a confirmed, in-bounds comment."""
    model = IcuAddSessionCommentInput(
        activity_id="i12345678", comment="Solid debrief: 4x8min @ 300W, RPE 7.", confirmed=True
    )
    assert model.confirmed is True
    assert "4x8min" in model.comment


def test_icu_add_session_comment_input_rejects_comment_over_2000_chars():
    """AC3: a comment body over 2000 characters is rejected at validation."""
    with pytest.raises(ValidationError):
        IcuAddSessionCommentInput(activity_id="i12345678", comment="x" * 2001)


def test_icu_add_session_comment_input_accepts_2000_char_comment():
    """A comment of exactly 2000 characters is accepted."""
    model = IcuAddSessionCommentInput(activity_id="i12345678", comment="y" * 2000)
    assert len(model.comment) == 2000


def test_icu_add_session_comment_input_rejects_empty_comment():
    """Test IcuAddSessionCommentInput rejects an empty comment."""
    with pytest.raises(ValidationError):
        IcuAddSessionCommentInput(activity_id="i12345678", comment="")


def test_icu_add_session_comment_input_rejects_whitespace_only_comment():
    """Test IcuAddSessionCommentInput rejects a whitespace-only comment."""
    with pytest.raises(ValidationError):
        IcuAddSessionCommentInput(activity_id="i12345678", comment="   ")


def test_icu_add_session_comment_input_sanitizes_script_markup():
    """Binding condition 4: script blocks are stripped, never passed through."""
    model = IcuAddSessionCommentInput(
        activity_id="i12345678",
        comment="<script>alert('xss')</script>Great ride today.",
    )
    assert "<script>" not in model.comment
    assert "alert('xss')" not in model.comment
    assert "Great ride today." in model.comment


def test_icu_add_session_comment_input_sanitizes_event_handler_markup():
    """Binding condition 4: inline event-handler markup is stripped."""
    model = IcuAddSessionCommentInput(
        activity_id="i12345678",
        comment="<img src=x onerror=alert(1)>Solid work.",
    )
    assert "<img" not in model.comment
    assert "onerror" not in model.comment
    assert "Solid work." in model.comment


def test_icu_add_session_comment_input_strips_control_characters():
    """Binding condition 4: control characters are removed from the comment."""
    model = IcuAddSessionCommentInput(
        activity_id="i12345678", comment="Good\u0007 session\u001b today."
    )
    assert "\u0007" not in model.comment
    assert "\u001b" not in model.comment
    assert "Good session today." in model.comment


def test_icu_add_session_comment_input_rejects_comment_sanitizing_to_empty():
    """A comment made only of markup is rejected instead of posting emptiness."""
    with pytest.raises(ValidationError):
        IcuAddSessionCommentInput(activity_id="i12345678", comment="<script></script>")


def test_icu_add_session_comment_input_rejects_bad_activity_id():
    """Test IcuAddSessionCommentInput validates the activity id shape."""
    with pytest.raises(ValidationError):
        IcuAddSessionCommentInput(activity_id="../../etc/passwd", comment="ok")


def test_icu_add_session_comment_input_extra_forbid():
    """Test IcuAddSessionCommentInput rejects extra fields."""
    with pytest.raises(ValidationError):
        IcuAddSessionCommentInput(activity_id="i1", comment="ok", extra=True)  # type: ignore


# ---------------------------------------------------------------------------
# ICU Batch Event Models (#94)
# ---------------------------------------------------------------------------


def test_icu_event_draft_accepts_valid_draft():
    """A valid event draft constructs with all optional fields populated."""
    draft = IcuEventDraft(
        external_id="plan-w42-tue",
        date="2026-10-13",
        name="Tuesday Threshold",
        type="Ride",
        category="WORKOUT",
        description="3x10min @ 95% FTP",
        moving_time_seconds=3600,
        icu_training_load=90.0,
        workout_doc="- Warm up 10m 50-65%\n3x\n- 10m 95%\n- 5m 50%",
    )
    assert draft.external_id == "plan-w42-tue"
    assert draft.date == "2026-10-13"
    assert draft.name == "Tuesday Threshold"
    assert draft.type == "Ride"
    assert draft.category == "WORKOUT"
    assert draft.description == "3x10min @ 95% FTP"
    assert draft.moving_time_seconds == 3600
    assert draft.icu_training_load == 90.0
    assert draft.workout_doc is not None


def test_icu_event_draft_defaults():
    """Optional draft fields default to Ride / WORKOUT / None."""
    draft = IcuEventDraft(external_id="x1", date="2026-10-13", name="Rest Day Note")
    assert draft.type == "Ride"
    assert draft.category == "WORKOUT"
    assert draft.description is None
    assert draft.workout_doc is None
    assert draft.moving_time_seconds is None
    assert draft.icu_training_load is None


def test_icu_event_draft_rejects_malformed_date_shape():
    """AC5: a non-ISO date shape is a field-level error."""
    with pytest.raises(ValidationError):
        IcuEventDraft(external_id="x1", date="13/10/2026", name="Bad Date")


def test_icu_event_draft_rejects_impossible_calendar_date():
    """AC5: a shape-valid but impossible calendar date is rejected."""
    with pytest.raises(ValidationError):
        IcuEventDraft(external_id="x1", date="2026-02-30", name="Bad Date")


def test_icu_event_draft_rejects_bad_external_id():
    """The external_id reconciliation key rejects empty and unsafe values."""
    with pytest.raises(ValidationError):
        IcuEventDraft(external_id="", date="2026-10-13", name="Bad")

    with pytest.raises(ValidationError):
        IcuEventDraft(external_id="../../etc/passwd", date="2026-10-13", name="Bad")


def test_icu_event_draft_sanitizes_name_and_description():
    """Markdown-injection defense (#90): markup stripped from title and description."""
    draft = IcuEventDraft(
        external_id="x1",
        date="2026-10-13",
        name="<script>alert('xss')</script>Threshold Day",
        description="<img src=x onerror=alert(1)>Ride steady.",
    )
    assert "<script>" not in draft.name
    assert "alert" not in draft.name
    assert "Threshold Day" in draft.name
    assert "<img" not in str(draft.description)
    assert "onerror" not in str(draft.description)
    assert "Ride steady." in str(draft.description)


def test_icu_event_draft_name_newlines_collapsed():
    """A title is single-line: newlines collapse to single spaces."""
    draft = IcuEventDraft(external_id="x1", date="2026-10-13", name="Tuesday\nThreshold")
    assert draft.name == "Tuesday Threshold"


def test_icu_event_draft_rejects_name_sanitizing_to_empty():
    """A title that is empty after sanitization is rejected."""
    with pytest.raises(ValidationError):
        IcuEventDraft(external_id="x1", date="2026-10-13", name="<script>x</script>")


def test_icu_event_draft_rejects_description_sanitizing_to_empty():
    """A provided description that sanitizes to empty is rejected."""
    with pytest.raises(ValidationError):
        IcuEventDraft(
            external_id="x1", date="2026-10-13", name="Ok", description="<script>x</script>"
        )


def test_icu_event_draft_rejects_unknown_category():
    """AC5: a category outside the ICU event enum is a field-level error."""
    with pytest.raises(ValidationError):
        IcuEventDraft(external_id="x1", date="2026-10-13", name="Bad", category="BANANA")


def test_icu_batch_create_events_input_accepts_valid_batch():
    """A valid batch constructs; confirm_token defaults to None (preview phase)."""
    model = IcuBatchCreateEventsInput(
        events=[
            IcuEventDraft(external_id="a", date="2026-10-12", name="Mon"),
            IcuEventDraft(external_id="b", date="2026-10-13", name="Tue"),
        ]
    )
    assert len(model.events) == 2
    assert model.confirm_token is None
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN


def test_icu_batch_create_events_input_rejects_over_50_items():
    """AC4: a batch over 50 items is rejected at validation, before any network call."""
    drafts = [
        IcuEventDraft(external_id=f"e{idx}", date="2026-10-13", name=f"W{idx}") for idx in range(51)
    ]
    with pytest.raises(ValidationError) as excinfo:
        IcuBatchCreateEventsInput(events=drafts)
    assert "50" in str(excinfo.value)


def test_icu_batch_create_events_input_accepts_50_items():
    """The batch boundary of exactly 50 items is accepted."""
    drafts = [
        IcuEventDraft(external_id=f"e{idx}", date="2026-10-13", name=f"W{idx}") for idx in range(50)
    ]
    model = IcuBatchCreateEventsInput(events=drafts)
    assert len(model.events) == 50


def test_icu_batch_create_events_input_rejects_empty_batch():
    """An empty batch is rejected at validation."""
    with pytest.raises(ValidationError):
        IcuBatchCreateEventsInput(events=[])


def test_icu_batch_create_events_input_rejects_duplicate_external_ids():
    """Duplicate external_ids inside one batch are a caller error (upsert ambiguity)."""
    with pytest.raises(ValidationError) as excinfo:
        IcuBatchCreateEventsInput(
            events=[
                IcuEventDraft(external_id="dup", date="2026-10-12", name="Mon"),
                IcuEventDraft(external_id="dup", date="2026-10-13", name="Tue"),
            ]
        )
    assert "dup" in str(excinfo.value)


def test_icu_batch_create_events_input_extra_forbid():
    """Extra fields are rejected."""
    with pytest.raises(ValidationError):
        IcuBatchCreateEventsInput(
            events=[IcuEventDraft(external_id="a", date="2026-10-12", name="Mon")],
            extra=True,  # type: ignore
        )


def test_icu_event_draft_accepts_explicit_none_description():
    """An explicitly None description stays None (validator short-circuits)."""
    draft = IcuEventDraft(external_id="x1", date="2026-10-13", name="Ok", description=None)
    assert draft.description is None


def test_icu_batch_event_outcome_model():
    """The per-item outcome model validates its literal outcome values."""
    created = IcuBatchEventOutcome(external_id="a", outcome="created", event_id="101")
    assert created.outcome == "created"
    assert created.event_id == "101"
    assert created.reason is None

    updated = IcuBatchEventOutcome(external_id="b", outcome="updated", event_id="102")
    assert updated.outcome == "updated"

    failed = IcuBatchEventOutcome(external_id="c", outcome="failed", reason="upstream 500")
    assert failed.outcome == "failed"
    assert failed.event_id is None
    assert failed.reason == "upstream 500"

    with pytest.raises(ValidationError):
        IcuBatchEventOutcome(external_id="d", outcome="skipped")  # type: ignore


# ---------------------------------------------------------------------------
# ICU Workout Compliance Models (#95)
# ---------------------------------------------------------------------------


@patch("coach_mcp.models.date")
def test_icu_get_workout_compliance_input_default_dates(mock_date):
    """Test IcuGetWorkoutComplianceInput defaults to a 7-day debrief window."""
    mock_date.today.return_value = date(2026, 10, 11)
    model = IcuGetWorkoutComplianceInput()
    assert model.oldest == "2026-10-04"
    assert model.newest == "2026-10-11"
    assert model.athlete_id is None
    assert model.response_format == ResponseFormat.MARKDOWN


@patch("coach_mcp.models.date")
def test_icu_get_workout_compliance_input_explicit_dates_preserved(mock_date):
    """Test IcuGetWorkoutComplianceInput keeps an explicit in-bounds date range."""
    mock_date.today.return_value = date(2026, 10, 11)
    model = IcuGetWorkoutComplianceInput(oldest="2026-10-01", newest="2026-10-10")
    assert model.oldest == "2026-10-01"
    assert model.newest == "2026-10-10"


def test_icu_get_workout_compliance_input_rejects_range_over_90_days():
    """AC1: a range wider than 90 days is rejected with an explicit error."""
    with pytest.raises(ValidationError) as excinfo:
        IcuGetWorkoutComplianceInput(oldest="2026-01-01", newest="2026-10-11")
    message = str(excinfo.value)
    assert "90-day maximum" in message
    assert "283" in message  # 2026-01-01 -> 2026-10-11 spans 283 days


def test_icu_get_workout_compliance_input_allows_full_90_day_span():
    """A range of exactly 90 days is accepted."""
    model = IcuGetWorkoutComplianceInput(oldest="2026-07-13", newest="2026-10-11")
    assert model.oldest == "2026-07-13"
    assert model.newest == "2026-10-11"


def test_icu_get_workout_compliance_input_rejects_oldest_after_newest():
    """An inverted range is rejected with the house error message."""
    with pytest.raises(ValidationError) as excinfo:
        IcuGetWorkoutComplianceInput(oldest="2026-10-11", newest="2026-01-01")
    assert "oldest must be on or before newest" in str(excinfo.value)


def test_icu_get_workout_compliance_input_rejects_impossible_calendar_dates():
    """Well-formed but impossible calendar dates are rejected."""
    with pytest.raises(ValidationError):
        IcuGetWorkoutComplianceInput(oldest="2026-02-30", newest="2026-10-11")


def test_icu_get_workout_compliance_input_rejects_bad_date_format():
    """Non-ISO date shapes are rejected."""
    with pytest.raises(ValidationError):
        IcuGetWorkoutComplianceInput(oldest="01/02/2026", newest="2026-10-11")


def test_icu_get_workout_compliance_input_extra_forbid():
    """Extra fields are rejected."""
    with pytest.raises(ValidationError):
        IcuGetWorkoutComplianceInput(extra=True)  # type: ignore


def _compliance_event(
    event_id: int,
    date_str: str,
    name: str = "Threshold",
    category: str = "WORKOUT",
    workout_doc: Any | None = None,
) -> dict[str, Any]:
    """Build a planned-event fixture shaped like an ICU EventEx."""
    event: dict[str, Any] = {
        "id": event_id,
        "name": name,
        "category": category,
        "type": "Ride",
        "start_date_local": f"{date_str}T08:00:00",
        "moving_time": 3600,
        "icu_training_load": 90,
    }
    if workout_doc is not None:
        event["workout_doc"] = workout_doc
    return event


def _compliance_activity(
    activity_id: str,
    paired_event_id: int | None,
    compliance: float | None = 95.0,
    interval_summary: list[str] | None = None,
    name: str = "Threshold",
) -> dict[str, Any]:
    """Build an executed-activity fixture shaped like an ICU Activity."""
    activity: dict[str, Any] = {
        "id": activity_id,
        "name": name,
        "type": "Ride",
        "start_date_local": "2026-10-06T09:00:00",
        "moving_time": 3500,
        "average_heartrate": 150,
        "average_watts": 250.0,
    }
    if paired_event_id is not None:
        activity["paired_event_id"] = paired_event_id
    if compliance is not None:
        activity["compliance"] = compliance
    if interval_summary is not None:
        activity["interval_summary"] = interval_summary
    return activity


def test_build_workout_compliance_report_joins_via_paired_event_id():
    """AC2: the join is by paired_event_id, never by title or date proximity.

    Two identically-named events on adjacent dates; the executed activity is
    paired with the SECOND event only. Heuristic date/title matching would
    wrongly complete the first event.
    """
    events = [
        _compliance_event(201, "2026-10-06", name="Threshold"),
        _compliance_event(202, "2026-10-07", name="Threshold"),
    ]
    activities = [_compliance_activity("a1", paired_event_id=202)]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, activities, today=date(2026, 10, 11)
    )
    by_id = {event.event_id: event for event in report.events}
    assert by_id["201"].status == "missed"
    assert by_id["202"].status == "completed"
    assert by_id["202"].compliance == 95.0
    assert (report.completed, report.missed) == (1, 1)


def test_build_workout_compliance_report_classifies_missed_event():
    """A past planned workout without a paired activity is missed."""
    events = [_compliance_event(301, "2026-10-06")]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, [], today=date(2026, 10, 11)
    )
    assert report.events[0].status == "missed"
    assert report.events[0].compliance is None
    assert (report.completed, report.missed, report.upcoming) == (0, 1, 0)
    assert report.adherence_rate == 0.0


def test_build_workout_compliance_report_upcoming_event_excluded_from_rate():
    """A future planned workout is upcoming, not missed, and not rate-counted."""
    events = [
        _compliance_event(401, "2026-10-06"),
        _compliance_event(402, "2026-10-20"),
    ]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-20", events, [], today=date(2026, 10, 11)
    )
    by_id = {event.event_id: event for event in report.events}
    assert by_id["401"].status == "missed"
    assert by_id["402"].status == "upcoming"
    assert (report.completed, report.missed, report.upcoming) == (0, 1, 1)
    assert report.adherence_rate == 0.0  # denominator excludes the upcoming event


def test_build_workout_compliance_report_structure_diff_match():
    """AC3 (match): planned step count equals executed interval count."""
    workout_doc = {"steps": [{"duration": 600}, {"duration": 600}, {"duration": 600}]}
    events = [_compliance_event(501, "2026-10-06", workout_doc=workout_doc)]
    activities = [
        _compliance_activity(
            "a1", paired_event_id=501, interval_summary=["4m 115%", "3m 50%", "4m 115%"]
        )
    ]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, activities, today=date(2026, 10, 11)
    )
    assert report.events[0].structure_diff == "match"


def test_build_workout_compliance_report_structure_diff_mismatch():
    """AC3 (mismatch): executed interval count differs from the planned steps."""
    workout_doc = {"steps": [{"duration": 600}, {"duration": 600}, {"duration": 600}]}
    events = [_compliance_event(502, "2026-10-06", workout_doc=workout_doc)]
    activities = [
        _compliance_activity("a2", paired_event_id=502, interval_summary=["4m 115%", "3m 50%"])
    ]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, activities, today=date(2026, 10, 11)
    )
    assert report.events[0].structure_diff == "mismatch"


def test_build_workout_compliance_report_structure_diff_unavailable_without_doc():
    """AC3: a DSL-string workout_doc cannot be structurally diffed -> unavailable."""
    events = [_compliance_event(503, "2026-10-06", workout_doc="- 10m warmup\n3x\n- 4m 115%")]
    activities = [_compliance_activity("a3", paired_event_id=503, interval_summary=["4m 115%"])]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, activities, today=date(2026, 10, 11)
    )
    assert report.events[0].structure_diff == "unavailable"


def test_build_workout_compliance_report_structure_diff_unavailable_without_intervals():
    """AC3: an activity without interval data yields an unavailable diff."""
    workout_doc = {"steps": [{"duration": 600}]}
    events = [_compliance_event(504, "2026-10-06", workout_doc=workout_doc)]
    activities = [_compliance_activity("a4", paired_event_id=504, interval_summary=None)]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, activities, today=date(2026, 10, 11)
    )
    assert report.events[0].structure_diff == "unavailable"


def test_build_workout_compliance_report_ignores_non_workout_events():
    """Only WORKOUT-category events are classified; notes are not 'missed'."""
    events = [
        _compliance_event(601, "2026-10-06", category="NOTE"),
        _compliance_event(602, "2026-10-07", category="WORKOUT"),
    ]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, [], today=date(2026, 10, 11)
    )
    assert [event.event_id for event in report.events] == ["602"]
    assert (report.total_planned, report.missed) == (1, 1)


def test_build_workout_compliance_report_empty_inputs():
    """AC5: an empty range yields a structured empty report, not an error."""
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", [], [], today=date(2026, 10, 11)
    )
    assert report.total_planned == 0
    assert report.completed == 0
    assert report.missed == 0
    assert report.upcoming == 0
    assert report.adherence_rate is None
    assert report.events == []


def test_build_workout_compliance_report_no_matching_workout_events():
    """AC5: events exist but none is a WORKOUT -> structured empty report."""
    events = [_compliance_event(701, "2026-10-06", category="NOTE")]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, [], today=date(2026, 10, 11)
    )
    assert report.total_planned == 0
    assert report.adherence_rate is None
    assert report.events == []


def test_build_workout_compliance_report_adherence_rate():
    """The summary adherence rate is completed / (completed + missed) in percent."""
    events = [
        _compliance_event(801, "2026-10-06"),
        _compliance_event(802, "2026-10-07"),
        _compliance_event(803, "2026-10-08"),
        _compliance_event(804, "2026-10-09"),
    ]
    activities = [_compliance_activity("a1", paired_event_id=801)]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-09", events, activities, today=date(2026, 10, 11)
    )
    assert (report.completed, report.missed) == (1, 3)
    assert report.adherence_rate == 25.0


def test_build_workout_compliance_report_compliance_missing_is_none():
    """A paired activity without a native compliance value projects None."""
    events = [_compliance_event(901, "2026-10-06")]
    activities = [_compliance_activity("a1", paired_event_id=901, compliance=None)]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, activities, today=date(2026, 10, 11)
    )
    assert report.events[0].status == "completed"
    assert report.events[0].compliance is None


def test_workout_compliance_report_whitelist_only_fields():
    """AC4: the report exposes whitelisted fields only — no raw activity dump."""
    workout_doc = {"steps": [{"duration": 600}]}
    events = [_compliance_event(1001, "2026-10-06", workout_doc=workout_doc)]
    activities = [
        _compliance_activity(
            "a1",
            paired_event_id=1001,
            interval_summary=["4m 115%"],
        )
    ]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, activities, today=date(2026, 10, 11)
    )
    dumped = report.model_dump()
    assert set(dumped.keys()) == {
        "oldest",
        "newest",
        "total_planned",
        "completed",
        "missed",
        "upcoming",
        "adherence_rate",
        "events",
    }
    assert set(dumped["events"][0].keys()) == {
        "event_id",
        "date",
        "name",
        "status",
        "compliance",
        "structure_diff",
    }
    # Raw activity payload values (HR, watts) never surface.
    serialized = json.dumps(dumped)
    assert "150" not in serialized
    assert "250.0" not in serialized


def test_workout_compliance_event_model_rejects_unknown_status():
    """The per-event status is a closed literal set."""
    with pytest.raises(ValidationError):
        WorkoutComplianceEvent(
            event_id="1",
            date="2026-10-06",
            name="X",
            status="postponed",  # type: ignore
            compliance=None,
            structure_diff="unavailable",
        )


def test_build_workout_compliance_report_skips_malformed_payloads():
    """Defensive guards: malformed events/activities are skipped, never crash."""
    events = [
        "not-a-dict",  # type: ignore[list-item]
        _compliance_event("bad-id", "2026-10-06"),  # non-numeric event id
        _compliance_event(1101, "2026-10-06"),
    ]
    activities = [
        "not-a-dict",  # type: ignore[list-item]
        _compliance_activity("a0", paired_event_id="not-an-int"),  # type: ignore[arg-item]
        _compliance_activity("a1", paired_event_id=1101),
    ]
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", events, activities, today=date(2026, 10, 11)
    )
    assert [event.event_id for event in report.events] == ["1101"]
    assert report.events[0].status == "completed"


def test_build_workout_compliance_report_unparseable_event_date_is_missed():
    """An event with an unparseable date cannot be upcoming; unpaired -> missed."""
    event = _compliance_event(1201, "2026-10-06")
    event["start_date_local"] = "not-a-timestamp"
    report = build_workout_compliance_report(
        "2026-10-06", "2026-10-07", [event], [], today=date(2026, 10, 11)
    )
    assert report.events[0].status == "missed"


# ---------------------------------------------------------------------------
# ICU Completed Sessions Models (#96)
# ---------------------------------------------------------------------------


@patch("coach_mcp.models.date")
def test_icu_get_completed_sessions_input_default_dates(mock_date):
    """Test IcuGetCompletedSessionsInput defaults to a 7-day debrief window."""
    mock_date.today.return_value = date(2026, 10, 11)
    model = IcuGetCompletedSessionsInput()
    assert model.oldest == "2026-10-04"
    assert model.newest == "2026-10-11"
    assert model.athlete_id is None
    assert model.activity_type is None
    assert model.limit == 50
    assert model.response_format == ResponseFormat.MARKDOWN


def test_icu_get_completed_sessions_input_explicit_dates_preserved():
    """Test IcuGetCompletedSessionsInput keeps an explicit in-bounds date range."""
    model = IcuGetCompletedSessionsInput(oldest="2026-10-01", newest="2026-10-10")
    assert model.oldest == "2026-10-01"
    assert model.newest == "2026-10-10"


def test_icu_get_completed_sessions_input_rejects_range_over_90_days():
    """AC1: a >90-day span is rejected with an explicit validation error."""
    with pytest.raises(ValidationError) as excinfo:
        IcuGetCompletedSessionsInput(oldest="2026-01-01", newest="2026-10-11")
    assert "90-day maximum" in str(excinfo.value)


def test_icu_get_completed_sessions_input_allows_full_90_day_span():
    """A range of exactly 90 days is accepted."""
    model = IcuGetCompletedSessionsInput(oldest="2026-07-13", newest="2026-10-11")
    assert model.oldest == "2026-07-13"
    assert model.newest == "2026-10-11"


def test_icu_get_completed_sessions_input_rejects_oldest_after_newest():
    """Test IcuGetCompletedSessionsInput rejects an inverted date range."""
    with pytest.raises(ValidationError):
        IcuGetCompletedSessionsInput(oldest="2026-10-11", newest="2026-01-01")


def test_icu_get_completed_sessions_input_rejects_impossible_calendar_dates():
    """Test IcuGetCompletedSessionsInput rejects well-formed but impossible dates."""
    with pytest.raises(ValidationError):
        IcuGetCompletedSessionsInput(oldest="2026-02-30", newest="2026-10-11")


def test_icu_get_completed_sessions_input_rejects_bad_date_format():
    """Test IcuGetCompletedSessionsInput rejects non-ISO date shapes."""
    with pytest.raises(ValidationError):
        IcuGetCompletedSessionsInput(oldest="01/02/2026", newest="2026-10-11")


def test_icu_get_completed_sessions_input_page_size_cap():
    """AC2: the page size is capped to 1-100."""
    with pytest.raises(ValidationError):
        IcuGetCompletedSessionsInput(oldest="2026-10-01", newest="2026-10-11", limit=0)

    with pytest.raises(ValidationError):
        IcuGetCompletedSessionsInput(oldest="2026-10-01", newest="2026-10-11", limit=101)

    valid_max = IcuGetCompletedSessionsInput(oldest="2026-10-01", newest="2026-10-11", limit=100)
    assert valid_max.limit == 100


def test_icu_get_completed_sessions_input_type_filter_accepts_enum_values():
    """AC3: defined enum values are accepted (member and raw string)."""
    model = IcuGetCompletedSessionsInput(
        oldest="2026-10-01", newest="2026-10-11", activity_type=IcuActivityType.RIDE
    )
    assert model.activity_type == IcuActivityType.RIDE

    model_string = IcuGetCompletedSessionsInput(
        oldest="2026-10-01", newest="2026-10-11", activity_type="VirtualRide"
    )
    assert model_string.activity_type == IcuActivityType.VIRTUAL_RIDE


def test_icu_get_completed_sessions_input_type_filter_rejects_unknown_value():
    """AC3: values outside the enum are rejected with field-level errors."""
    with pytest.raises(ValidationError) as excinfo:
        IcuGetCompletedSessionsInput(
            oldest="2026-10-01", newest="2026-10-11", activity_type="Cycling"
        )
    assert "activity_type" in str(excinfo.value)


def test_icu_get_completed_sessions_input_type_filter_rejects_loose_boolean():
    """#90 gating: a loose boolean is never a valid activity-type filter."""
    with pytest.raises(ValidationError):
        IcuGetCompletedSessionsInput(oldest="2026-10-01", newest="2026-10-11", activity_type=True)


def test_icu_get_completed_sessions_input_extra_forbid():
    """Test IcuGetCompletedSessionsInput rejects extra fields."""
    with pytest.raises(ValidationError):
        IcuGetCompletedSessionsInput(extra=True)  # type: ignore


def _completed_session_raw(**overrides: Any) -> dict[str, Any]:
    """Raw ICU activity payload including non-whitelisted exfiltration bait."""
    record: dict[str, Any] = {
        "id": "a1",
        "name": "Zwift Tempo",
        "type": "VirtualRide",
        "start_date_local": "2026-10-08T09:00:00",
        "moving_time": 3600,
        "icu_training_load": 85,
        "average_heartrate": 150,
        "average_watts": 250.0,
        "max_heartrate": 180,
        "calories": 900,
        "description": "secret-athlete-notes",
        "paired_event_id": 101,
        "someUnknownIcuField": "leak-attempt",
    }
    record.update(overrides)
    return record


def test_completed_session_summary_exposes_whitelist_only():
    """Binding condition 2: projection drops every non-whitelisted ICU field."""
    projected = project_completed_sessions([_completed_session_raw()])
    assert len(projected) == 1
    dumped = projected[0].model_dump()
    assert set(dumped.keys()) == {
        "id",
        "date",
        "type",
        "title",
        "duration_seconds",
        "load",
    }
    assert dumped["id"] == "a1"
    assert dumped["date"] == "2026-10-08"
    assert dumped["type"] == "VirtualRide"
    assert dumped["title"] == "Zwift Tempo"
    assert dumped["duration_seconds"] == 3600.0
    assert dumped["load"] == 85.0
    # Never raw pass-through: non-whitelisted values are absent.
    for banned in (
        "average_heartrate",
        "average_watts",
        "max_heartrate",
        "calories",
        "description",
        "paired_event_id",
        "someUnknownIcuField",
    ):
        assert banned not in dumped


def test_completed_session_summary_missing_fields_are_none():
    """Missing whitelisted fields project as None, never as raw defaults."""
    projected = project_completed_sessions([{"id": "a2", "type": "Run"}])
    session = projected[0]
    assert session.date == ""
    assert session.title == "Untitled"
    assert session.duration_seconds is None
    assert session.load is None


def test_completed_session_summary_ignores_non_numeric_values():
    """Non-numeric ICU values are dropped instead of passing through."""
    projected = project_completed_sessions(
        [{"id": "a3", "type": "Ride", "moving_time": "not-a-number", "icu_training_load": True}]
    )
    assert projected[0].duration_seconds is None
    assert projected[0].load is None


def test_project_completed_sessions_filters_by_type():
    """AC3: the strict enum filter keeps only matching activity types."""
    records = [
        _completed_session_raw(id="a1", type="VirtualRide"),
        _completed_session_raw(id="a2", type="Run"),
        _completed_session_raw(id="a3", type="Ride"),
    ]
    rides = project_completed_sessions(records, activity_type=IcuActivityType.RIDE)
    assert [session.id for session in rides] == ["a3"]

    all_sessions = project_completed_sessions(records)
    assert [session.id for session in all_sessions] == ["a1", "a2", "a3"]


def test_project_completed_sessions_skips_malformed_records():
    """Defensive guard: malformed records are skipped, never crash."""
    projected = project_completed_sessions(["not-a-dict"])  # type: ignore[list-item]
    assert projected == []


def test_project_completed_sessions_empty():
    """An empty ICU payload projects to an empty list."""
    assert project_completed_sessions([]) == []
