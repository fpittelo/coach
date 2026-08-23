"""Configuration settings for Coach MCP."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
    )

    # Intervals.icu API Settings
    intervals_api_key: str = Field(
        default="",
        description="Intervals.icu API Key. Generate in Settings -> Developer Settings.",
        validation_alias="INTERVALS_API_KEY",
    )
    intervals_athlete_id: str = Field(
        default="0",
        description=(
            "Intervals.icu athlete ID ('0' for authenticated user, "
            "or specific ID 'iXXXXX')."
        ),
        validation_alias="INTERVALS_ATHLETE_ID",
    )
    intervals_base_url: str = Field(
        default="https://intervals.icu/api/v1",
        description="Intervals.icu API base endpoint URL.",
        validation_alias="INTERVALS_BASE_URL",
    )

    # Transport and Server Settings
    mcp_transport: Literal["stdio", "streamable_http", "sse"] = Field(
        default="stdio",
        description="MCP server transport mode: 'stdio' or 'streamable_http'/'sse'.",
        validation_alias="MCP_TRANSPORT",
    )
    mcp_host: str = Field(
        default="0.0.0.0",
        description="Host to bind streamable HTTP / SSE transport.",
        validation_alias="MCP_HOST",
    )
    mcp_port: int = Field(
        default=8000,
        description="Port for streamable HTTP / SSE transport.",
        validation_alias="MCP_PORT",
    )

    # HTTP Client Timeouts and Retries
    http_timeout_seconds: float = Field(
        default=30.0,
        description="HTTP timeout in seconds.",
        validation_alias="HTTP_TIMEOUT_SECONDS",
    )
    http_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts on 429 or 5xx responses.",
        validation_alias="HTTP_MAX_RETRIES",
    )


settings = Settings()
