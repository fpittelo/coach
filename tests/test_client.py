"""Comprehensive tests for IntervalsClient using respx mock server."""

import asyncio
import json

import httpx
import pytest
import respx

from coach_mcp.client import (
    IntervalsAPIError,
    IntervalsAuthError,
    IntervalsClient,
    IntervalsNotFoundError,
    IntervalsRateLimitError,
)

BASE_URL = "https://intervals.icu/api/v1"


@pytest.mark.asyncio
async def test_get_athlete_profile_success(client: IntervalsClient):
    """Test successful athlete profile retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0").respond(
            200,
            json={"athlete": {"id": "0", "name": "Athlete One", "weight": 72.5}},
        )

        data = await client.get_athlete_profile()
        assert data["athlete"]["name"] == "Athlete One"
        assert data["athlete"]["weight"] == 72.5
        await client.close()


@pytest.mark.asyncio
async def test_get_athlete_profile_with_athlete_id(client: IntervalsClient):
    """Test athlete profile retrieval with explicit athlete_id."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/i12345").respond(
            200,
            json={"athlete": {"id": "i12345", "name": "Coached Athlete"}},
        )

        data = await client.get_athlete_profile(athlete_id="i12345")
        assert data["athlete"]["name"] == "Coached Athlete"
        await client.close()


@pytest.mark.asyncio
async def test_get_sport_settings_success(client: IntervalsClient):
    """Test successful sport settings retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/sport-settings").respond(
            200,
            json=[{"types": ["Ride"], "ftp": 300, "lthr": 170, "max_hr": 190}],
        )

        data = await client.get_sport_settings()
        assert len(data) == 1
        assert data[0]["ftp"] == 300
        await client.close()


@pytest.mark.asyncio
async def test_list_activities_success(client: IntervalsClient):
    """Test listing activities with query parameters."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get(
            "/athlete/0/activities?oldest=2026-08-01&newest=2026-08-22&limit=10"
        ).respond(
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

        activities = await client.list_activities(
            oldest="2026-08-01", newest="2026-08-22", limit=10
        )
        assert len(activities) == 1
        assert activities[0]["id"] == "act1"
        assert activities[0]["name"] == "Endurance Ride"
        await client.close()


@pytest.mark.asyncio
async def test_get_activity_success(client: IntervalsClient):
    """Test successful activity retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/activity/i123").respond(
            200,
            json={
                "id": "i123",
                "name": "Threshold Intervals",
                "type": "Ride",
                "icu_training_load": 95.0,
            },
        )

        data = await client.get_activity("i123")
        assert data["id"] == "i123"
        assert data["name"] == "Threshold Intervals"
        await client.close()


@pytest.mark.asyncio
async def test_get_activity_streams_success(client: IntervalsClient):
    """Test successful activity streams retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/activity/i123/streams?types=watts%2Cheartrate").respond(
            200,
            json=[
                {"type": "watts", "data": [100, 200, 300]},
                {"type": "heartrate", "data": [120, 130, 140]},
            ],
        )

        data = await client.get_activity_streams("i123", types=["watts", "heartrate"])
        assert len(data) == 2
        assert data[0]["type"] == "watts"
        await client.close()


@pytest.mark.asyncio
async def test_get_activity_streams_no_types(client: IntervalsClient):
    """Test activity streams retrieval without explicit types."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/activity/i123/streams").respond(200, json=[])

        data = await client.get_activity_streams("i123")
        assert data == []
        await client.close()


@pytest.mark.asyncio
async def test_get_activity_intervals_success(client: IntervalsClient):
    """Test successful activity intervals retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/activity/i123/intervals").respond(
            200,
            json={
                "intervals": [
                    {"name": "Interval 1", "avg_watts": 250},
                    {"name": "Interval 2", "avg_watts": 255},
                ]
            },
        )

        data = await client.get_activity_intervals("i123")
        assert len(data["intervals"]) == 2
        assert data["intervals"][0]["avg_watts"] == 250
        await client.close()


@pytest.mark.asyncio
async def test_get_power_curve_success(client: IntervalsClient):
    """Test successful athlete power curve retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/power-curves?curves=Ride").respond(
            200,
            json={
                "Ride": {
                    "5": 850,
                    "60": 300,
                    "300": 280,
                    "1200": 250,
                }
            },
        )

        data = await client.get_power_curve()
        assert data["Ride"]["5"] == 850
        assert data["Ride"]["60"] == 300
        await client.close()


@pytest.mark.asyncio
async def test_get_power_curve_with_sport_type(client: IntervalsClient):
    """Test athlete power curve retrieval with explicit sport type."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/power-curves?curves=Run").respond(
            200,
            json={"Run": {"60": 320}},
        )

        data = await client.get_power_curve(sport_type="Run")
        assert data["Run"]["60"] == 320
        await client.close()


@pytest.mark.asyncio
async def test_get_power_curve_with_athlete_id(client: IntervalsClient):
    """Test athlete power curve retrieval with explicit athlete_id."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/i123/power-curves?curves=Ride").respond(
            200,
            json={"Ride": {"60": 310}},
        )

        data = await client.get_power_curve(athlete_id="i123")
        assert data["Ride"]["60"] == 310
        await client.close()


@pytest.mark.asyncio
async def test_get_activity_power_curve_success(client: IntervalsClient):
    """Test successful activity power curve retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/activity/i123/power-curve").respond(
            200,
            json={
                "5": 900,
                "60": 320,
                "300": 290,
            },
        )

        data = await client.get_activity_power_curve("i123")
        assert data["5"] == 900
        assert data["60"] == 320
        await client.close()


@pytest.mark.asyncio
async def test_get_activity_power_curve_not_found(client: IntervalsClient):
    """Test activity power curve 404 error handling."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/activity/missing/power-curve").respond(404, text="Activity not found")

        with pytest.raises(IntervalsNotFoundError):
            await client.get_activity_power_curve("missing")
        await client.close()


@pytest.mark.asyncio
async def test_create_activity_success(client: IntervalsClient):
    """Test successful activity creation."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.post("/athlete/0/activities").respond(
            201,
            json={"id": "i999", "name": "Manual Entry"},
        )

        payload = {
            "name": "Manual Entry",
            "type": "Ride",
            "start_date_local": "2026-08-22T10:00:00",
            "moving_time": 3600,
        }
        res = await client.create_activity(payload)
        assert res["id"] == "i999"
        assert json.loads(route.calls.last.request.content) == payload
        await client.close()


@pytest.mark.asyncio
async def test_update_activity_success(client: IntervalsClient):
    """Test successful activity update."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.put("/activity/i123").respond(
            200,
            json={"id": "i123", "name": "Updated Name"},
        )

        payload = {"name": "Updated Name", "perceived_exertion": 7.5}
        res = await client.update_activity("i123", payload)
        assert res["name"] == "Updated Name"
        assert json.loads(route.calls.last.request.content) == payload
        await client.close()


@pytest.mark.asyncio
async def test_delete_activity_success(client: IntervalsClient):
    """Test successful activity deletion."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.delete("/activity/i123").respond(
            204,
            json={"status": "deleted"},
        )

        res = await client.delete_activity("i123")
        assert res["status"] == "success"
        await client.close()


@pytest.mark.asyncio
async def test_get_wellness_success(client: IntervalsClient):
    """Test successful wellness retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/wellness?oldest=2026-08-01&newest=2026-08-22").respond(
            200,
            json=[
                {"id": "2026-08-22", "restingHR": 48, "readiness": 85.5},
                {"id": "2026-08-21", "restingHR": 50, "readiness": 82.0},
            ],
        )

        data = await client.get_wellness("2026-08-01", "2026-08-22")
        assert len(data) == 2
        assert data[0]["id"] == "2026-08-22"
        await client.close()


@pytest.mark.asyncio
async def test_record_wellness_success(client: IntervalsClient):
    """Test successful wellness recording."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.put("/athlete/0/wellness/2026-08-22").respond(
            200,
            json={"id": "2026-08-22", "restingHR": 48},
        )

        payload = {"restingHR": 48, "readiness": 85.5}
        res = await client.record_wellness("2026-08-22", payload)
        assert res["id"] == "2026-08-22"
        assert json.loads(route.calls.last.request.content) == payload
        await client.close()


@pytest.mark.asyncio
async def test_list_events_success(client: IntervalsClient):
    """Test successful events listing."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get(
            "/athlete/0/events?oldest=2026-08-01&newest=2026-08-22&category=WORKOUT"
        ).respond(
            200,
            json=[
                {"id": "evt1", "name": "VO2max Intervals", "category": "WORKOUT"},
            ],
        )

        data = await client.list_events(
            oldest="2026-08-01", newest="2026-08-22", category="WORKOUT"
        )
        assert len(data) == 1
        assert data[0]["name"] == "VO2max Intervals"
        await client.close()


@pytest.mark.asyncio
async def test_list_events_without_category(client: IntervalsClient):
    """Test events listing without category filter."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/events?oldest=2026-08-01&newest=2026-08-22").respond(
            200,
            json=[{"id": "evt1", "name": "Event"}],
        )

        data = await client.list_events(oldest="2026-08-01", newest="2026-08-22")
        assert len(data) == 1
        await client.close()


@pytest.mark.asyncio
async def test_get_event_success(client: IntervalsClient):
    """Test successful event retrieval."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/events/evt123").respond(
            200,
            json={"id": "evt123", "name": "Threshold 3x10", "category": "WORKOUT"},
        )

        data = await client.get_event("evt123")
        assert data["id"] == "evt123"
        assert data["name"] == "Threshold 3x10"
        await client.close()


@pytest.mark.asyncio
async def test_create_event_success(client: IntervalsClient):
    """Test successful event creation."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.post("/athlete/0/events").respond(
            201,
            json={"id": 98765, "name": "Threshold 3x10", "category": "WORKOUT"},
        )

        payload = {
            "name": "Threshold 3x10",
            "start_date_local": "2026-08-24T08:00:00",
            "category": "WORKOUT",
        }
        res = await client.create_event(payload)
        assert res["id"] == 98765
        assert res["name"] == "Threshold 3x10"
        assert json.loads(route.calls.last.request.content) == payload
        await client.close()


@pytest.mark.asyncio
async def test_update_event_success(client: IntervalsClient):
    """Test successful event update."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.put("/athlete/0/events/evt123").respond(
            200,
            json={"id": "evt123", "name": "Updated Event"},
        )

        payload = {"name": "Updated Event"}
        res = await client.update_event("evt123", payload)
        assert res["name"] == "Updated Event"
        assert json.loads(route.calls.last.request.content) == payload
        await client.close()


@pytest.mark.asyncio
async def test_delete_event_success(client: IntervalsClient):
    """Test successful event deletion."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.delete("/athlete/0/events/evt123").respond(
            204,
            json={"status": "deleted"},
        )

        res = await client.delete_event("evt123")
        assert res["status"] == "success"
        await client.close()


@pytest.mark.asyncio
async def test_list_folders_success(client: IntervalsClient):
    """Test successful folders listing."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/folders").respond(
            200,
            json=[{"id": "folder1", "name": "Base Training", "children": []}],
        )

        data = await client.list_folders()
        assert len(data) == 1
        assert data[0]["name"] == "Base Training"
        await client.close()


@pytest.mark.asyncio
async def test_list_workouts_success(client: IntervalsClient):
    """Test successful workouts listing."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/workouts?folderId=folder1").respond(
            200,
            json=[{"id": "w1", "name": "Sweet Spot", "type": "Ride"}],
        )

        data = await client.list_workouts(folder_id="folder1")
        assert len(data) == 1
        assert data[0]["name"] == "Sweet Spot"
        await client.close()


@pytest.mark.asyncio
async def test_list_workouts_without_folder(client: IntervalsClient):
    """Test workouts listing without folder filter."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0/workouts").respond(
            200,
            json=[{"id": "w1", "name": "Workout"}],
        )

        data = await client.list_workouts()
        assert len(data) == 1
        await client.close()


# ---------------------------------------------------------------------------
# Error Handling & Retry Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_athlete_auth_error(client: IntervalsClient):
    """Test handling 401 unauthorized error."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0").respond(401, text="Unauthorized API Key")

        with pytest.raises(IntervalsAuthError):
            await client.get_athlete_profile()
        await client.close()


@pytest.mark.asyncio
async def test_get_activity_not_found(client: IntervalsClient):
    """Test handling 404 not found error."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/activity/non_existent").respond(404, text="Activity not found")

        with pytest.raises(IntervalsNotFoundError):
            await client.get_activity("non_existent")
        await client.close()


@pytest.mark.asyncio
async def test_rate_limit_retry_then_success(client: IntervalsClient):
    """Test 429 rate limit triggers retry and eventual success."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.get("/athlete/0")
        route.side_effect = [
            httpx.Response(429, headers={"Retry-After": "0.01"}),
            httpx.Response(200, json={"athlete": {"id": "0", "name": "Recovered"}}),
        ]

        data = await client.get_athlete_profile()
        assert data["athlete"]["name"] == "Recovered"
        assert route.call_count == 2
        await client.close()


@pytest.mark.asyncio
async def test_rate_limit_exhaustion(client: IntervalsClient):
    """Test 429 rate limit exhausts retries and raises IntervalsRateLimitError."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0").respond(
            429,
            headers={"Retry-After": "0.01"},
            text="Rate limited",
        )

        with pytest.raises(IntervalsRateLimitError):
            await client.get_athlete_profile()
        await client.close()


@pytest.mark.asyncio
async def test_server_error_retry_then_success(client: IntervalsClient):
    """Test 500 server error triggers exponential backoff retry and success."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.get("/athlete/0")
        route.side_effect = [
            httpx.Response(500, text="Internal Server Error"),
            httpx.Response(200, json={"athlete": {"id": "0", "name": "Recovered"}}),
        ]

        data = await client.get_athlete_profile()
        assert data["athlete"]["name"] == "Recovered"
        assert route.call_count == 2
        await client.close()


@pytest.mark.asyncio
async def test_server_error_exhaustion(client: IntervalsClient):
    """Test 500 server error exhausts retries and raises IntervalsAPIError."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0").respond(500, text="Internal Server Error")

        with pytest.raises(IntervalsAPIError) as exc_info:
            await client.get_athlete_profile()
        assert exc_info.value.status_code == 500
        await client.close()


@pytest.mark.asyncio
async def test_service_unavailable_retry_exhaustion(client: IntervalsClient):
    """Test 503 service unavailable exhausts retries and raises IntervalsAPIError."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0").respond(503, text="Service Unavailable")

        with pytest.raises(IntervalsAPIError) as exc_info:
            await client.get_athlete_profile()
        assert exc_info.value.status_code == 503
        await client.close()


@pytest.mark.asyncio
async def test_network_error_retry_exhaustion(client: IntervalsClient):
    """Test network timeout error exhausts retries and raises IntervalsAPIError."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0").mock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(IntervalsAPIError) as exc_info:
            await client.get_athlete_profile()
        assert "Connection timeout or network failure" in str(exc_info.value)
        await client.close()


@pytest.mark.asyncio
async def test_client_close():
    """Test explicit client close."""
    client = IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
    )
    await client.get_client()
    assert client._client is not None
    assert not client._client.is_closed

    await client.close()
    assert client._client is None


@pytest.mark.asyncio
async def test_client_async_context_manager():
    """Test client as async context manager."""
    async with IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
    ) as client:
        assert isinstance(client, IntervalsClient)
        assert client._client is not None
        assert not client._client.is_closed


@pytest.mark.asyncio
async def test_client_context_manager_closes_on_exit():
    """Test async context manager closes client on exit."""
    client = IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
    )
    async with client:
        pass
    assert client._client is None


@pytest.mark.asyncio
async def test_resolve_athlete_fallback(client: IntervalsClient):
    """Test athlete ID resolution falls back to default when empty."""
    with respx.mock(base_url=BASE_URL) as respx_mock:
        respx_mock.get("/athlete/0").respond(200, json={"athlete": {"id": "0"}})

        data = await client.get_athlete_profile(athlete_id="")
        assert data["athlete"]["id"] == "0"
        await client.close()


# ---------------------------------------------------------------------------
# TTL Cache Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_prevents_duplicate_http_call():
    """A second call with the same key should not trigger another HTTP request."""
    client = IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
        cache_ttl=300,
    )
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.get("/athlete/0").respond(
            200,
            json={"athlete": {"id": "0", "name": "Cached Athlete"}},
        )

        first = await client.get_athlete_profile()
        second = await client.get_athlete_profile()

        assert first["athlete"]["name"] == "Cached Athlete"
        assert second["athlete"]["name"] == "Cached Athlete"
        assert route.call_count == 1

    await client.close()


@pytest.mark.asyncio
async def test_cache_expiration_triggers_fresh_request():
    """After TTL expires, a fresh HTTP request should be made."""
    client = IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
        cache_ttl=0,
    )
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.get("/athlete/0")
        route.side_effect = [
            httpx.Response(200, json={"athlete": {"id": "0", "name": "First"}}),
            httpx.Response(200, json={"athlete": {"id": "0", "name": "Second"}}),
        ]

        first = await client.get_athlete_profile()
        await asyncio.sleep(0.01)
        second = await client.get_athlete_profile()

        assert first["athlete"]["name"] == "First"
        assert second["athlete"]["name"] == "Second"
        assert route.call_count == 2

    await client.close()


@pytest.mark.asyncio
async def test_cache_cleared_on_client_close():
    """Closing the client should clear the cache."""
    client = IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
        cache_ttl=300,
    )
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.get("/athlete/0")
        route.side_effect = [
            httpx.Response(200, json={"athlete": {"id": "0", "name": "First"}}),
            httpx.Response(200, json={"athlete": {"id": "0", "name": "Second"}}),
        ]

        first = await client.get_athlete_profile()
        await client.close()
        second = await client.get_athlete_profile()

        assert first["athlete"]["name"] == "First"
        assert second["athlete"]["name"] == "Second"
        assert route.call_count == 2

    await client.close()


@pytest.mark.asyncio
async def test_sport_settings_are_cached():
    """Sport settings should be cached and not trigger duplicate HTTP calls."""
    client = IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
        cache_ttl=300,
    )
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.get("/athlete/0/sport-settings").respond(
            200,
            json=[{"types": ["Ride"], "ftp": 300}],
        )

        first = await client.get_sport_settings()
        second = await client.get_sport_settings()

        assert first[0]["ftp"] == 300
        assert second[0]["ftp"] == 300
        assert route.call_count == 1

    await client.close()


@pytest.mark.asyncio
async def test_folders_are_cached():
    """Folders should be cached and not trigger duplicate HTTP calls."""
    client = IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
        cache_ttl=300,
    )
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.get("/athlete/0/folders").respond(
            200,
            json=[{"id": "folder1", "name": "Base Training"}],
        )

        first = await client.list_folders()
        second = await client.list_folders()

        assert first[0]["name"] == "Base Training"
        assert second[0]["name"] == "Base Training"
        assert route.call_count == 1

    await client.close()


@pytest.mark.asyncio
async def test_dynamic_endpoints_are_not_cached():
    """Dynamic endpoints like activities should always hit the API."""
    client = IntervalsClient(
        api_key="test_key",
        athlete_id="0",
        base_url=BASE_URL,
        max_retries=1,
        cache_ttl=300,
    )
    with respx.mock(base_url=BASE_URL) as respx_mock:
        route = respx_mock.get(
            "/athlete/0/activities?oldest=2026-08-01&newest=2026-08-22&limit=10"
        ).respond(
            200,
            json=[{"id": "act1", "name": "Endurance Ride"}],
        )

        first = await client.list_activities(
            oldest="2026-08-01", newest="2026-08-22", limit=10
        )
        second = await client.list_activities(
            oldest="2026-08-01", newest="2026-08-22", limit=10
        )

        assert first[0]["name"] == "Endurance Ride"
        assert second[0]["name"] == "Endurance Ride"
        assert route.call_count == 2

    await client.close()
