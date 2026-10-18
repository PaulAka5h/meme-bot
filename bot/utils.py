"""Shared JSON extraction and logging helpers."""

import json
import logging
from typing import Any

logger = logging.getLogger("meme_bot")


def extract_json(text: str) -> dict[str, Any]:
    """Extract the first valid JSON object from model output."""
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("No JSON object found in model response.")


def configure_logging() -> None:
    """Set concise logging defaults for the application."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
