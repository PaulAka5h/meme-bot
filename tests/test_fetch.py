"""Tests for the public meme fetch source."""

import json

import requests

from bot import fetch as fetch_module


def test_fetch_records_and_skips_seen_items(tmp_path, monkeypatch) -> None:
    """Skip a previously recorded meme and persist the new ID."""
    seen_file = tmp_path / "data" / "seen.json"
    seen_file.parent.mkdir()
    seen_file.write_text(json.dumps(["old"]), encoding="utf-8")
    replies = iter(
        [
            {"id": "old", "url": "https://example.com/old.png", "title": "old"},
            {"id": "new", "url": "https://example.com/new.png", "title": "new"},
        ]
    )
    monkeypatch.setattr(fetch_module, "SEEN_FILE", seen_file)
    monkeypatch.setattr(fetch_module, "fetch_from_source", lambda query: next(replies))
    assert fetch_module.fetch("football")["id"] == "new"
    assert json.loads(seen_file.read_text(encoding="utf-8")) == ["new", "old"]


def test_fetch_returns_none_for_empty_source(tmp_path, monkeypatch) -> None:
    """Return no meme when the public source has no result."""
    monkeypatch.setattr(fetch_module, "SEEN_FILE", tmp_path / "seen.json")
    monkeypatch.setattr(fetch_module, "fetch_from_source", lambda query: None)
    assert fetch_module.fetch("football") is None


def test_fetch_returns_none_when_source_times_out(tmp_path, monkeypatch) -> None:
    """Treat source timeouts as an empty fetch so chat can generate a fallback."""
    monkeypatch.setattr(fetch_module, "SEEN_FILE", tmp_path / "seen.json")

    def timeout(query):
        """Simulate a public source timeout."""
        raise requests.Timeout("source unavailable")

    monkeypatch.setattr(fetch_module, "fetch_from_source", timeout)
    assert fetch_module.fetch("football") is None
