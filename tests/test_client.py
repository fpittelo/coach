"""Tests for IntervalsClient using respx mock server."""

import pytest
import respx
from coach_mcp.client import (
    IntervalsClient,
    IntervalsAuthError,
    IntervalsNotFoundError,
)


@pytest.mark.asyncio
async def test_get_athlete_profile_success(client: IntervalsClient):
    """Test successful athlete profile retrieval."""
    with respx.mock(base_url="https://intervals.icu/api/v1") as respx_mock:
        respx_mock.get("/athlete/0").respond(
            200,
            json={"athlete": {"id": "0", "name": "Athlete One", "weight": 72.5}},
        )

        data = await client.get_athlete_profile()
        assert data["athlete"]["name"] == "Athlete One"
        assert data["athlete"]["weight"] == 72.5
        await client.close()


@pytest.mark.asyncio
async def test_get_athlete_auth_error(client: IntervalsClient):
    """Test handling 401 unauthorized error."""
    with respx.mock(base_url="https://intervals.icu/api/v1") as respx_mock:
        respx_mock.get("/athlete/0").respond(401, text="Unauthorized API Key")

        with pytest.raises(IntervalsAuthError):
            await client.get_athlete_profile()
        await client.close()


@pytest.mark.asyncio
async def test_get_activity_not_found(client: IntervalsClient):
    """Test handling 404 not found error."""
    with respx.mock(base_url="https://intervals.icu/api/v1") as respx_mock:
        respx_mock.get("/activity/non_existent").respond(404, text="Activity not found")

        with pytest.raises(IntervalsNotFoundError):
            await client.get_activity("non_existent")
        await client.close()


@pytest.mark.asyncio
async def test_list_activities_success(client: IntervalsClient):
    """Test listing activities with query parameters."""
    with respx.mock(base_url="https://intervals.icu/api/v1") as respx_mock:
        respx_mock.get("/athlete/0/activities?oldest=2026-08-01&newest=2026-08-22&limit=10").respond(
            200,
            json=[
                {
                    "id": "act1",
                    "name": "Endurance Ride",
                    "type": "Ride",
                    "start_date_local": "2026-08-15T09:00:00",
                    "moving_time": 7200,
                    "icu_training_load": 110,
                }
            ],
        )

        activities = await client.list_activities(oldest="2026-08-01", newest="2026-08-22", limit=10)
        assert len(activities) == 1
        assert activities[0]["id"] == "act1"
        assert activities[0]["name"] == "Endurance Ride"
        await client.close()


@pytest.mark.asyncio
async def test_create_event_success(client: IntervalsClient):
    """Test creating a scheduled event."""
    with respx.mock(base_url="https://intervals.icu/api/v1") as respx_mock:
        respx_mock.post("/athlete/0/events").respond(
            201,
            json={"id": 98765, "name": "Threshold 3x10", "category": "WORKOUT"},
        )

        payload = {"name": "Threshold 3x10", "start_date_local": "2026-08-24T08:00:00", "category": "WORKOUT"}
        res = await client.create_event(payload)
        assert res["id"] == 98765
        assert res["name"] == "Threshold 3x10"
        await client.close()
