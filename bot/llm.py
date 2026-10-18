"""Single retrying wrapper for Gemma chat completion calls."""

import time
from typing import Any

import requests

from config import API_KEY, BASE_URL, MODEL_NAME, REQUEST_TIMEOUT


class LLMError(RuntimeError):
    """Represent an actionable model request failure."""


def complete(messages: list[dict[str, str]], temperature: float = 0.3) -> str:
    """Call the configured model and retry transient failures twice."""
    if not MODEL_NAME:
        raise LLMError(
            "Gemma model is not configured. Put MODEL_NAME=your-Gemma-4-26B-A4B-IT-model-id in .env."
        )
    if not API_KEY:
        raise LLMError("API key is not configured. Put API_KEY=your_api_key_here in .env.")
    url = f"{BASE_URL}/chat/completions"
    payload: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
    }
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {API_KEY}"},
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise LLMError("Gemma returned an empty response.")
            return content.strip()
        except requests.Timeout as error:
            raise LLMError(
                "Gemma request timed out. Check your provider endpoint, model ID, and network."
            ) from error
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(0.25 * (attempt + 1))
    raise LLMError(f"Gemma request failed after 3 attempts: {last_error}") from last_error
