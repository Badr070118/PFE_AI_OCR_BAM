from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

LOGGER = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"
DEFAULT_TIMEOUT_SECONDS = 6.0


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value is not None else default


def generate_response(
    prompt: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float | None = None,
) -> str | None:
    if not prompt:
        return None

    url = base_url or _env("LLAMA_BASE_URL", DEFAULT_BASE_URL)
    model_name = model or _env("LLAMA_MODEL", DEFAULT_MODEL)
    timeout = timeout_seconds
    if timeout is None:
        try:
            timeout = float(_env("LLAMA_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)) or DEFAULT_TIMEOUT_SECONDS)
        except ValueError:
            timeout = DEFAULT_TIMEOUT_SECONDS

    payload: dict[str, Any] = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        LOGGER.warning("LLaMA HTTP error: %s", exc)
        return None
    except Exception as exc:
        LOGGER.warning("LLaMA request failed: %s", exc)
        return None

    try:
        decoded = json.loads(body)
    except json.JSONDecodeError:
        LOGGER.warning("LLaMA response is not valid JSON.")
        return None

    if isinstance(decoded, dict) and decoded.get("error"):
        LOGGER.warning("LLaMA error response: %s", decoded.get("error"))
        return None

    text = ""
    if isinstance(decoded, dict):
        text = decoded.get("response") or decoded.get("text") or ""
    if not text:
        return None
    return str(text).strip() or None


__all__ = ["generate_response"]
