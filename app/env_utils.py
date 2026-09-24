"""Shared helper for reading environment variables defensively.

Found necessary the hard way: a trailing newline in a value pasted into
a hosting provider's dashboard (Render) produced an invalid HTTP header
when used as a Bearer token. `requests` rejects that with a clear
ValueError; httpx (which the openai SDK uses internally) instead
swallows the same validation failure and re-raises it as a generic,
unhelpful APIConnectionError. Stripping whitespace at the point of
reading avoids depending on every secret ever being pasted perfectly
clean into every environment this app runs in.
"""
from __future__ import annotations

import os


def clean_env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value or default
