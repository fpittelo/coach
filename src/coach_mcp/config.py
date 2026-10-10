"""Configuration settings for Coach MCP."""

import logging
import os
from pathlib import Path
from typing import Final, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class SecretResolutionError(RuntimeError):
    """Raised when a secret referenced via a *_FILE env var cannot be resolved.

    Deliberately derives from RuntimeError (not ValueError) so pydantic does
    not wrap it into a ValidationError — the fail-fast startup message stays
    intact and actionable.
    """


def _read_secret_file(file_env_var: str, file_path: str) -> str:
    """Read a secret from a Docker-secrets style file, failing fast on problems.

    Missing, unreadable, or empty files raise immediately: a silently-empty
    API key would only surface as confusing 401s downstream. The file path may
    appear in error messages and logs; the secret content must never.
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SecretResolutionError(
            f"{file_env_var}={file_path}: cannot read secret file "
            f"({exc.strerror or type(exc).__name__})"
        ) from exc
    secret = content.strip()
    if not secret:
        raise SecretResolutionError(f"{file_env_var}={file_path}: secret file is empty")
    return secret


# Secret-bearing env vars and their Docker-secrets _FILE variants (issue #63).
_SECRET_FILE_ENV_VARS: Final[dict[str, str]] = {
    "INTERVALS_API_KEY": "INTERVALS_API_KEY_FILE",
    "COACH_MCP_AUTH_TOKEN": "COACH_MCP_AUTH_TOKEN_FILE",
}


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
            "Intervals.icu athlete ID ('0' for authenticated user, or specific ID 'iXXXXX')."
        ),
        validation_alias="INTERVALS_ATHLETE_ID",
    )
    intervals_base_url: str = Field(
        default="https://intervals.icu/api/v1",
        description="Intervals.icu API base endpoint URL.",
        validation_alias="INTERVALS_BASE_URL",
    )

    # MCP HTTP bearer auth (consumed by the HTTP auth layer; config-only here)
    coach_mcp_auth_token: str = Field(
        default="",
        description="Bearer token protecting the MCP HTTP endpoint (streamable-http/SSE).",
        validation_alias="COACH_MCP_AUTH_TOKEN",
    )

    # Transport and Server Settings
    mcp_transport: Literal["stdio", "streamable-http", "streamable_http", "sse"] = Field(
        default="stdio",
        description=(
            "MCP server transport mode: 'stdio', 'streamable-http', 'streamable_http' or 'sse'."
        ),
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

    # Caching
    cache_ttl_seconds: int = Field(
        default=300,
        description="Default TTL in seconds for semi-static cached responses.",
        validation_alias="CACHE_TTL_SECONDS",
    )
    cache_ttl_volatile_seconds: int = Field(
        default=60,
        description=(
            "TTL in seconds for volatile cached responses " "(activities, wellness, events, etc.)."
        ),
        validation_alias="CACHE_TTL_VOLATILE_SECONDS",
    )

    @model_validator(mode="before")
    @classmethod
    def _resolve_secret_files(cls, data: object) -> object:
        """Resolve *_FILE secret references before field validation.

        For each secret-bearing env var, if its ``_FILE`` variant is set
        (non-empty), the secret is read from that file and used as the
        effective value. Docker secrets mount at ``/run/secrets/<name>`` with
        mode 0400, so containers inject e.g.
        ``INTERVALS_API_KEY_FILE=/run/secrets/intervals_api_key`` and the key
        never appears in ``docker inspect``.

        Precedence: the ``_FILE`` variant is authoritative when set. Setting
        BOTH the direct env var and its ``_FILE`` variant is ambiguous and
        fails fast — silent precedence could mask a stale secret and surface
        only as confusing downstream 401s. ``_FILE`` variants are read from
        the process environment only (compose/K8s ``environment:``), not from
        the ``.env`` file.
        """
        if not isinstance(data, dict):
            return data
        for env_var, file_env_var in _SECRET_FILE_ENV_VARS.items():
            file_path = os.environ.get(file_env_var)
            if not file_path:
                continue
            if data.get(env_var) is not None:
                raise SecretResolutionError(
                    f"Ambiguous secret configuration: both {env_var} and "
                    f"{file_env_var} are set; set only one of them."
                )
            data[env_var] = _read_secret_file(file_env_var, file_path)
            logger.info("Loaded %s from secret file %s", env_var, file_path)
        return data


settings = Settings()
