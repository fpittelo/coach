"""Asynchronous HTTP Client for Intervals.icu REST API."""

import asyncio
import logging
import sys
from typing import Any, cast

import httpx

from coach_mcp.cache import TTLCache
from coach_mcp.config import settings
from coach_mcp.security import redact_sensitive

logger = logging.getLogger("coach_mcp.client")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class IntervalsAPIError(Exception):
    """Base exception for Intervals.icu API interactions."""

    def __init__(
        self, message: str, status_code: int | None = None, response_text: str | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

    def __str__(self) -> str:
        """Return a sanitized string representation with secrets redacted."""
        message = redact_sensitive(str(self.args[0])) if self.args else "IntervalsAPIError"
        message = message or "IntervalsAPIError"
        parts: list[str] = [message]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.response_text:
            parts.append(f"response_text={redact_sensitive(self.response_text)}")
        return " ".join(parts)


class IntervalsAuthError(IntervalsAPIError):
    """Authentication or authorization failed (401 / 403)."""


class IntervalsNotFoundError(IntervalsAPIError):
    """Requested resource not found (404)."""


class IntervalsRateLimitError(IntervalsAPIError):
    """Rate limit exceeded (429)."""


class IntervalsClient:
    """Async client with connection pooling, retries, and rate limit handling."""

    def __init__(
        self,
        api_key: str | None = None,
        athlete_id: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        cache_ttl: int | None = None,
    ) -> None:
        self.api_key = api_key or settings.intervals_api_key
        self.default_athlete_id = athlete_id or settings.intervals_athlete_id
        self.base_url = (base_url or settings.intervals_base_url).rstrip("/")
        self.timeout = timeout or settings.http_timeout_seconds
        self.max_retries = max_retries or settings.http_max_retries
        self.cache_ttl = cache_ttl if cache_ttl is not None else settings.cache_ttl_seconds
        self._client: httpx.AsyncClient | None = None
        self._cache = TTLCache(default_ttl=self.cache_ttl)

    async def get_client(self) -> httpx.AsyncClient:
        """Retrieve or create an active httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            auth = httpx.BasicAuth(username="API_KEY", password=self.api_key)
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=auth,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                headers={"Accept": "application/json", "User-Agent": "Coach-MCP-Server/0.1.0"},
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client session and clear the cache."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        await self._cache.clear()

    async def __aenter__(self) -> "IntervalsClient":
        """Async context manager entry."""
        await self.get_client()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
    ) -> Any:
        """Execute an HTTP request with exponential backoff on transient errors."""
        client = await self.get_client()
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}/{endpoint.lstrip('/')}"

        attempt = 0
        backoff_delay = 1.0

        while True:
            attempt += 1
            try:
                logger.debug(
                    "Request: %s %s (attempt %d/%d)",
                    method,
                    redact_sensitive(url),
                    attempt,
                    self.max_retries,
                )
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                )

                if response.status_code in (200, 201):
                    if response.headers.get("content-type", "").startswith("application/json"):
                        return response.json()
                    return response.text or {"status": "success"}

                if response.status_code == 204:
                    return {"status": "success", "message": "Resource deleted or updated"}

                if response.status_code == 401 or response.status_code == 403:
                    raise IntervalsAuthError(
                        f"Authentication failed ({response.status_code}). Check INTERVALS_API_KEY.",
                        status_code=response.status_code,
                        response_text=response.text,
                    )

                if response.status_code == 404:
                    raise IntervalsNotFoundError(
                        f"Resource not found at {endpoint}.",
                        status_code=404,
                        response_text=response.text,
                    )

                if response.status_code == 429:
                    if attempt < self.max_retries:
                        retry_after = float(response.headers.get("Retry-After", backoff_delay))
                        logger.warning(f"Rate limited (429). Retrying in {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        backoff_delay *= 2
                        continue
                    raise IntervalsRateLimitError(
                        "Intervals.icu rate limit exceeded. Please wait before retrying.",
                        status_code=429,
                        response_text=response.text,
                    )

                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        logger.warning(
                            f"Server error ({response.status_code}). "
                            f"Retrying in {backoff_delay}s..."
                        )
                        await asyncio.sleep(backoff_delay)
                        backoff_delay *= 2
                        continue
                    raise IntervalsAPIError(
                        f"Intervals.icu server error ({response.status_code}): {response.text}",
                        status_code=response.status_code,
                        response_text=response.text,
                    )

                raise IntervalsAPIError(
                    f"API error ({response.status_code}): {response.text}",
                    status_code=response.status_code,
                    response_text=response.text,
                )

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt < self.max_retries:
                    logger.warning(f"Network error ({exc}). Retrying in {backoff_delay}s...")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= 2
                    continue
                raise IntervalsAPIError(f"Connection timeout or network failure: {exc}") from exc

    def _resolve_athlete(self, athlete_id: str | None) -> str:
        return (
            athlete_id if athlete_id is not None and athlete_id.strip() else self.default_athlete_id
        )

    # ---------------------------------------------------------------------------
    # Athlete API Methods
    # ---------------------------------------------------------------------------

    async def get_athlete_profile(self, athlete_id: str | None = None) -> dict[str, Any]:
        """Fetch athlete profile details."""
        target_id = self._resolve_athlete(athlete_id)
        cache_key = f"profile:{target_id}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)
        result = await self._request("GET", f"athlete/{target_id}")
        await self._cache.set(cache_key, result)
        return cast(dict[str, Any], result)

    async def get_sport_settings(self, athlete_id: str | None = None) -> list[dict[str, Any]]:
        """Fetch athlete sport settings (power, HR, pace zones)."""
        target_id = self._resolve_athlete(athlete_id)
        cache_key = f"sport_settings:{target_id}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)
        result = await self._request("GET", f"athlete/{target_id}/sport-settings")
        await self._cache.set(cache_key, result)
        return cast(list[dict[str, Any]], result)

    # ---------------------------------------------------------------------------
    # Activities API Methods
    # ---------------------------------------------------------------------------

    async def list_activities(
        self,
        oldest: str,
        newest: str,
        athlete_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List activities between oldest and newest dates (YYYY-MM-DD)."""
        target_id = self._resolve_athlete(athlete_id)
        params = {"oldest": oldest, "newest": newest, "limit": limit}
        return cast(
            list[dict[str, Any]],
            await self._request("GET", f"athlete/{target_id}/activities", params=params),
        )

    async def get_activity(self, activity_id: str) -> dict[str, Any]:
        """Retrieve full details of an activity."""
        return cast(dict[str, Any], await self._request("GET", f"activity/{activity_id}"))

    async def get_activity_streams(
        self,
        activity_id: str,
        types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve time series streams (watts, heartrate, cadence, time, etc.)."""
        params = {}
        if types:
            params["types"] = ",".join(types)
        return cast(
            list[dict[str, Any]],
            await self._request("GET", f"activity/{activity_id}/streams", params=params),
        )

    async def get_activity_intervals(self, activity_id: str) -> dict[str, Any]:
        """Retrieve detected intervals for an activity."""
        return cast(dict[str, Any], await self._request("GET", f"activity/{activity_id}/intervals"))

    async def get_power_curve(
        self,
        athlete_id: str | None = None,
        sport_type: str = "Ride",
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Retrieve athlete mean-maximal power (MMP) curve for a sport type."""
        target_id = self._resolve_athlete(athlete_id)
        params = {"type": sport_type}
        return cast(
            dict[str, Any] | list[dict[str, Any]],
            await self._request("GET", f"athlete/{target_id}/power-curves", params=params),
        )

    async def get_power_model(
        self,
        athlete_id: str | None = None,
        sport_type: str = "Ride",
    ) -> dict[str, Any]:
        """Retrieve athlete critical power (CP), W', and Pmax model."""
        target_id = self._resolve_athlete(athlete_id)
        cache_key = f"power_model:{target_id}:{sport_type}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)
        params = {"type": sport_type}
        result = await self._request("GET", f"athlete/{target_id}/mmp-model", params=params)
        await self._cache.set(cache_key, result)
        return cast(dict[str, Any], result)

    async def get_activity_power_curve(
        self,
        activity_id: str,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Retrieve mean-maximal power (MMP) curve for a specific activity."""
        return cast(
            dict[str, Any] | list[dict[str, Any]],
            await self._request("GET", f"activity/{activity_id}/power-curve"),
        )

    async def create_activity(
        self,
        payload: dict[str, Any],
        athlete_id: str | None = None,
    ) -> dict[str, Any]:
        """Manually record a new activity via the events endpoint.

        Intervals.icu expects manual completed activities to be created as
        calendar events with category ``PAST_ACTIVITY``. The legacy
        ``POST /athlete/{id}/activities`` endpoint is reserved for uploading
        activity files (FIT/TCX/GPX) as multipart/form-data.
        """
        activity_payload = {**payload, "category": payload.get("category", "PAST_ACTIVITY")}
        result = await self.create_event(activity_payload, athlete_id=athlete_id)
        return result

    async def update_activity(
        self,
        activity_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Update activity fields (name, perceived exertion, feel, notes)."""
        return cast(
            dict[str, Any],
            await self._request("PUT", f"activity/{activity_id}", json_data=payload),
        )

    async def delete_activity(self, activity_id: str) -> dict[str, Any]:
        """Delete an activity."""
        return cast(dict[str, Any], await self._request("DELETE", f"activity/{activity_id}"))

    # ---------------------------------------------------------------------------
    # Wellness & Metrics API Methods
    # ---------------------------------------------------------------------------

    async def get_wellness(
        self,
        oldest: str,
        newest: str,
        athlete_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve wellness history over a date range."""
        target_id = self._resolve_athlete(athlete_id)
        params = {"oldest": oldest, "newest": newest}
        return cast(
            list[dict[str, Any]],
            await self._request("GET", f"athlete/{target_id}/wellness", params=params),
        )

    async def record_wellness(
        self,
        date_str: str,
        payload: dict[str, Any],
        athlete_id: str | None = None,
    ) -> dict[str, Any]:
        """Record or update wellness for a specific day."""
        target_id = self._resolve_athlete(athlete_id)
        return cast(
            dict[str, Any],
            await self._request(
                "PUT", f"athlete/{target_id}/wellness/{date_str}", json_data=payload
            ),
        )

    # ---------------------------------------------------------------------------
    # Planned Workouts & Events API Methods
    # ---------------------------------------------------------------------------

    async def list_events(
        self,
        oldest: str,
        newest: str,
        athlete_id: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """List calendar events and planned workouts."""
        target_id = self._resolve_athlete(athlete_id)
        params: dict[str, Any] = {"oldest": oldest, "newest": newest}
        if category:
            params["category"] = category
        return cast(
            list[dict[str, Any]],
            await self._request("GET", f"athlete/{target_id}/events", params=params),
        )

    async def get_event(self, event_id: str, athlete_id: str | None = None) -> dict[str, Any]:
        """Retrieve a specific calendar event."""
        target_id = self._resolve_athlete(athlete_id)
        return cast(
            dict[str, Any], await self._request("GET", f"athlete/{target_id}/events/{event_id}")
        )

    async def create_event(
        self,
        payload: dict[str, Any],
        athlete_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a planned workout or calendar event."""
        target_id = self._resolve_athlete(athlete_id)
        return cast(
            dict[str, Any],
            await self._request("POST", f"athlete/{target_id}/events", json_data=payload),
        )

    async def update_event(
        self,
        event_id: str,
        payload: dict[str, Any],
        athlete_id: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing calendar event or planned workout."""
        target_id = self._resolve_athlete(athlete_id)
        return cast(
            dict[str, Any],
            await self._request("PUT", f"athlete/{target_id}/events/{event_id}", json_data=payload),
        )

    async def delete_event(self, event_id: str, athlete_id: str | None = None) -> dict[str, Any]:
        """Delete a calendar event."""
        target_id = self._resolve_athlete(athlete_id)
        return cast(
            dict[str, Any], await self._request("DELETE", f"athlete/{target_id}/events/{event_id}")
        )

    # ---------------------------------------------------------------------------
    # Workout Library & Folders API Methods
    # ---------------------------------------------------------------------------

    async def list_folders(self, athlete_id: str | None = None) -> list[dict[str, Any]]:
        """List workout folders in library."""
        target_id = self._resolve_athlete(athlete_id)
        cache_key = f"folders:{target_id}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)
        result = await self._request("GET", f"athlete/{target_id}/folders")
        await self._cache.set(cache_key, result)
        return cast(list[dict[str, Any]], result)

    async def list_workouts(
        self,
        folder_id: str | None = None,
        athlete_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List workout templates in library."""
        target_id = self._resolve_athlete(athlete_id)
        params = {}
        if folder_id:
            params["folderId"] = folder_id
        return cast(
            list[dict[str, Any]],
            await self._request("GET", f"athlete/{target_id}/workouts", params=params),
        )
