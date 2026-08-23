"""Tests for Pydantic v2 input validation models."""

import pytest
from pydantic import ValidationError

from coach_mcp.models import (
    CreateActivityInput,
    CreateEventInput,
    GetEventInput,
    ListActivitiesInput,
    RecordWellnessInput,
    ResponseFormat,
)


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


def test_list_activities_input_invalid_date():
    """Test invalid date format validation."""
    with pytest.raises(ValidationError):
        ListActivitiesInput(oldest="invalid-date", newest="2026-08-22")


def test_create_activity_input_extra_forbid():
    """Test forbidding unexpected extra fields."""
    with pytest.raises(ValidationError):
        CreateActivityInput(
            name="Tempo Ride",
            type="Ride",
            start_date_local="2026-08-22T10:00:00",
            moving_time_seconds=3600,
            unexpected_field="disallowed",  # type: ignore
        )


def test_record_wellness_input_range_validation():
    """Test bounds validation on resting HR and readiness."""
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
