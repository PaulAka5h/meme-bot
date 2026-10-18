"""Tests for shared JSON helpers."""

import pytest

from bot.utils import extract_json


def test_extract_json_with_surrounding_text() -> None:
    """Extract a JSON object surrounded by explanatory text."""
    assert extract_json('Here you go: {"action":"chat"} done') == {"action": "chat"}


def test_extract_json_ignores_malformed_object() -> None:
    """Find a valid object after malformed JSON text."""
    assert extract_json('bad {broken} then {"ok":true}') == {"ok": True}


def test_extract_json_rejects_missing_object() -> None:
    """Raise a clear error when no JSON object is present."""
    with pytest.raises(ValueError, match="No JSON object"):
        extract_json("nothing structured here")
