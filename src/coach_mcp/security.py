"""Security utilities for secret/PII redaction and input sanitization."""

import json
import re
from typing import Any

# Basic authentication header values: Basic <base64>
_BASIC_AUTH_RE = re.compile(r"Basic\s+[A-Za-z0-9+/=]+", re.IGNORECASE)

# Bearer tokens: Bearer <token>
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE)

# API keys in URL query parameters: key=value
_API_KEY_QUERY_RE = re.compile(r"(api_key|apikey|key)\s*=\s*[A-Za-z0-9_-]+", re.IGNORECASE)

# APIKEY prefix header style: APIKEY <value>
_API_KEY_HEADER_RE = re.compile(r"APIKEY\s+[A-Za-z0-9_-]+", re.IGNORECASE)

# General key/value patterns using colon separator: key: value
_API_KEY_COLON_RE = re.compile(r"(?:api_key|apikey|key):\s*[A-Za-z0-9_-]+", re.IGNORECASE)

# Email addresses
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Mapping key names whose values must never be logged (structured redaction).
# ``key`` matches bare "key" and "*_key" suffixes (private_key, access_key, ...)
# without swallowing ordinary words that merely contain "key" (monkey, hotkey).
_SENSITIVE_KEY_RE = re.compile(
    r"api[_-]?key|apikey|(?:^|_)key(?:$)|token|authorization|password|secret|credential|bearer",
    re.IGNORECASE,
)

_REDACTED_PLACEHOLDER = "[REDACTED]"


def redact_sensitive(text: str | None) -> str | None:
    """Redact sensitive tokens, credentials, API keys, and email PII.

    Handles ``None`` and empty strings cleanly. Applies the following
    redactions:

    * ``Basic <base64>`` -> ``Basic [REDACTED]``
    * ``Bearer <token>`` -> ``Bearer [REDACTED]``
    * ``api_key=<value>`` -> ``api_key=[REDACTED]``
    * ``APIKEY <value>`` -> ``APIKEY [REDACTED]``
    * ``api_key: <value>`` -> ``[REDACTED]``
    * ``user@example.com`` -> ``[REDACTED:EMAIL]``

    Args:
        text: Input string that may contain sensitive data.

    Returns:
        Sanitized string, or ``None`` if input was ``None``.
    """
    if text is None:
        return None
    if text == "":
        return ""

    text = _BASIC_AUTH_RE.sub("Basic [REDACTED]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _API_KEY_QUERY_RE.sub(r"\1=[REDACTED]", text)
    text = _API_KEY_HEADER_RE.sub("APIKEY [REDACTED]", text)
    text = _API_KEY_COLON_RE.sub("[REDACTED]", text)
    text = _EMAIL_RE.sub("[REDACTED:EMAIL]", text)
    return text


def _is_sensitive_key(key: str) -> bool:
    """Return True if a mapping key names a secret-bearing field."""
    return _SENSITIVE_KEY_RE.search(key) is not None


def _redact_string(value: str) -> str | None:
    """Redact a string value, recursing into embedded JSON when present.

    A string whose stripped form starts with ``{`` or ``[`` is treated as
    potential JSON: on a successful parse the parsed structure is redacted via
    :func:`redact_structure` and re-serialized, so quoted JSON key/value pairs
    (invisible to the legacy string regex) cannot leak secrets. Malformed
    strings fall through to the prose path unchanged.
    """
    stripped = value.strip()
    if stripped.startswith(("{", "[")):
        try:
            parsed = json.loads(stripped)
        except ValueError:
            return redact_sensitive(value)
        if isinstance(parsed, (dict, list)):
            return json.dumps(redact_structure(parsed))
    return redact_sensitive(value)


def redact_structure(value: Any) -> Any:
    """Recursively redact secrets and PII from structured data.

    Extends :func:`redact_sensitive` to structured payloads (dicts, lists) for
    the audit path (#64):

    * values stored under sensitive keys (``api_key``, ``token``, ...) are
      replaced wholesale with ``[REDACTED]`` — the legacy string redaction
      cannot catch JSON-style ``"api_key": "..."`` pairs on its own;
    * every string value passes through :func:`_redact_string`, which recurses
      into embedded JSON (``{"notes": "{\\"api_key\\": \\"...\\"}"``) before
      applying the string redaction;
    * non-string scalars (int, float, bool, None) are preserved.

    Args:
        value: Arbitrary structure (dict, list, str, or scalar).

    Returns:
        Structure of the same shape with sensitive content redacted.
    """
    if isinstance(value, dict):
        return {
            key: _REDACTED_PLACEHOLDER if _is_sensitive_key(str(key)) else redact_structure(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_structure(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value
