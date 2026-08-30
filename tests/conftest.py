"""Test configuration and fixtures for Coach MCP."""

import pytest

from coach_mcp.client import IntervalsClient
from coach_mcp.config import Settings


@pytest.fixture
def mock_settings() -> Settings:
    """Fixture providing test configuration."""
    return Settings(
        intervals_api_key="test_secret_key",
        intervals_athlete_id="0",
        intervals_base_url="https://intervals.icu/api/v1",
        http_max_retries=2,
    )


@pytest.fixture
def client(mock_settings: Settings) -> IntervalsClient:
    """Fixture providing initialized client."""
    return IntervalsClient(
        api_key=mock_settings.intervals_api_key,
        athlete_id=mock_settings.intervals_athlete_id,
        base_url=mock_settings.intervals_base_url,
        max_retries=mock_settings.http_max_retries,
    )
