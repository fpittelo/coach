"""Tests for Docker secrets support (_FILE env var pattern) in coach_mcp.config.

Covers issue #63 acceptance criteria:
- AC1: INTERVALS_API_KEY_FILE reads the API key from a file when set.
- AC2: COACH_MCP_AUTH_TOKEN_FILE reads the token from a file when set.
- AC3: Falls back to the regular env var when the _FILE variant is unset.
- AC5: Secret files mounted with Docker's default mode 0400 are readable.
- AC7: Read-from-file, fallback-to-env, and missing-file error behaviour.

Precedence rule (documented contract): when both the direct env var and its
_FILE variant are set, startup fails fast — silent precedence could mask a
stale secret and produce confusing downstream 401s.
"""

import logging
import os
from typing import Any

import pytest

from coach_mcp.config import SecretResolutionError, Settings

SECRET_CASES = [
    ("INTERVALS_API_KEY", "INTERVALS_API_KEY_FILE", "intervals_api_key"),
    ("COACH_MCP_AUTH_TOKEN", "COACH_MCP_AUTH_TOKEN_FILE", "coach_mcp_auth_token"),
]


@pytest.fixture(autouse=True)
def _hermetic_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Run each test in an empty cwd so no local .env file leaks into Settings."""
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize(("env_var", "file_env_var", "field_name"), SECRET_CASES)
def test_secret_read_from_file_when_file_env_var_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    env_var: str,
    file_env_var: str,
    field_name: str,
) -> None:
    """AC1/AC2: the secret is read from the file when the _FILE variant is set."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("file-secret-value")
    monkeypatch.setenv(file_env_var, str(secret_file))
    monkeypatch.delenv(env_var, raising=False)

    settings = Settings()

    assert getattr(settings, field_name) == "file-secret-value"


@pytest.mark.parametrize(("env_var", "file_env_var", "field_name"), SECRET_CASES)
def test_falls_back_to_env_var_when_file_var_unset(
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
    file_env_var: str,
    field_name: str,
) -> None:
    """AC3: without the _FILE variant the regular env var is used (backward compat)."""
    monkeypatch.setenv(env_var, "env-secret-value")
    monkeypatch.delenv(file_env_var, raising=False)

    settings = Settings()

    assert getattr(settings, field_name) == "env-secret-value"


@pytest.mark.parametrize(("env_var", "file_env_var", "field_name"), SECRET_CASES)
def test_falls_back_to_default_when_neither_set(
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
    file_env_var: str,
    field_name: str,
) -> None:
    """AC3: with neither variant set the field keeps its empty default."""
    monkeypatch.delenv(env_var, raising=False)
    monkeypatch.delenv(file_env_var, raising=False)

    settings = Settings()

    assert getattr(settings, field_name) == ""


@pytest.mark.parametrize(("env_var", "file_env_var", "field_name"), SECRET_CASES)
def test_empty_file_env_var_treated_as_unset(
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
    file_env_var: str,
    field_name: str,
) -> None:
    """An empty _FILE value is treated as unset (falls back to the env var)."""
    monkeypatch.setenv(env_var, "env-secret-value")
    monkeypatch.setenv(file_env_var, "")

    settings = Settings()

    assert getattr(settings, field_name) == "env-secret-value"


@pytest.mark.parametrize(("env_var", "file_env_var", "_field_name"), SECRET_CASES)
def test_missing_secret_file_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    env_var: str,
    file_env_var: str,
    _field_name: str,
) -> None:
    """AC7: a _FILE variant pointing at a missing file fails fast at startup."""
    missing = tmp_path / "does-not-exist"
    monkeypatch.setenv(file_env_var, str(missing))
    monkeypatch.delenv(env_var, raising=False)

    with pytest.raises(SecretResolutionError) as exc_info:
        Settings()

    assert str(missing) in str(exc_info.value)
    assert file_env_var in str(exc_info.value)


def test_unreadable_secret_file_fails_fast(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """AC7: an unreadable secret file fails fast with the path in the error."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("unreadable-secret-value")
    secret_file.chmod(0o000)
    monkeypatch.setenv("INTERVALS_API_KEY_FILE", str(secret_file))
    monkeypatch.delenv("INTERVALS_API_KEY", raising=False)

    with pytest.raises(SecretResolutionError) as exc_info:
        Settings()

    assert str(secret_file) in str(exc_info.value)


@pytest.mark.skipif(os.geteuid() == 0, reason="file permissions are not enforced for root")
def test_unreadable_secret_file_error_never_contains_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """Secret hygiene: error messages carry the file path, never the content."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("top-secret-content")
    secret_file.chmod(0o000)
    monkeypatch.setenv("INTERVALS_API_KEY_FILE", str(secret_file))

    with pytest.raises(SecretResolutionError) as exc_info:
        Settings()

    assert "top-secret-content" not in str(exc_info.value)


def test_empty_secret_file_fails_fast(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """AC7: an empty secret file fails fast (a silently-empty key means 401s later)."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("")
    monkeypatch.setenv("INTERVALS_API_KEY_FILE", str(secret_file))
    monkeypatch.delenv("INTERVALS_API_KEY", raising=False)

    with pytest.raises(SecretResolutionError, match="empty"):
        Settings()


def test_whitespace_only_secret_file_fails_fast(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """A whitespace-only secret file is empty after stripping and fails fast."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("   \n\t\n")
    monkeypatch.setenv("INTERVALS_API_KEY_FILE", str(secret_file))
    monkeypatch.delenv("INTERVALS_API_KEY", raising=False)

    with pytest.raises(SecretResolutionError, match="empty"):
        Settings()


@pytest.mark.parametrize(("env_var", "file_env_var", "_field_name"), SECRET_CASES)
def test_both_env_var_and_file_var_set_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    env_var: str,
    file_env_var: str,
    _field_name: str,
) -> None:
    """Precedence rule: both variants set is ambiguous configuration — fail fast."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("file-secret-value")
    monkeypatch.setenv(env_var, "env-secret-value")
    monkeypatch.setenv(file_env_var, str(secret_file))

    with pytest.raises(SecretResolutionError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert env_var in message
    assert file_env_var in message


def test_secret_file_content_is_stripped(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Trailing newlines (common in mounted secret files) are stripped."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("stripped-secret-value\n")
    monkeypatch.setenv("INTERVALS_API_KEY_FILE", str(secret_file))
    monkeypatch.delenv("INTERVALS_API_KEY", raising=False)

    settings = Settings()

    assert settings.intervals_api_key == "stripped-secret-value"


def test_secret_file_with_docker_default_mode_0400_is_readable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """AC5: secret files mounted with Docker's default mode 0400 are readable."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("mode-0400-secret-value")
    secret_file.chmod(0o400)
    monkeypatch.setenv("INTERVALS_API_KEY_FILE", str(secret_file))
    monkeypatch.delenv("INTERVALS_API_KEY", raising=False)

    settings = Settings()

    assert settings.intervals_api_key == "mode-0400-secret-value"


def test_secret_content_never_logged_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Secret hygiene: the file path may be logged, the secret content never is."""
    secret_file = tmp_path / "secret"
    secret_file.write_text("logged-secret-value\n")
    monkeypatch.setenv("INTERVALS_API_KEY_FILE", str(secret_file))
    monkeypatch.delenv("INTERVALS_API_KEY", raising=False)

    with caplog.at_level(logging.DEBUG, logger="coach_mcp.config"):
        settings = Settings()

    assert settings.intervals_api_key == "logged-secret-value"
    assert "logged-secret-value" not in caplog.text
    assert str(secret_file) in caplog.text


def test_init_kwargs_still_work_without_file_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backward compat: programmatic construction by field name is unaffected."""
    monkeypatch.delenv("INTERVALS_API_KEY", raising=False)
    monkeypatch.delenv("INTERVALS_API_KEY_FILE", raising=False)
    monkeypatch.delenv("COACH_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("COACH_MCP_AUTH_TOKEN_FILE", raising=False)

    settings = Settings(
        intervals_api_key="kwarg-secret-value",
        coach_mcp_auth_token="kwarg-token-value",
    )

    assert settings.intervals_api_key == "kwarg-secret-value"
    assert settings.coach_mcp_auth_token == "kwarg-token-value"
