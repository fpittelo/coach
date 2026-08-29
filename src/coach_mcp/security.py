"""Security utilities for secret/PII redaction and input sanitization."""

import re

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
