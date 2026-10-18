"""Tests for meme caption generation."""

import pytest

from bot import generate as generate_module


def test_generate_uses_random_template_for_unknown_name(monkeypatch) -> None:
    """Choose a known template when the model returns an unknown one."""
    monkeypatch.setattr(generate_module, "complete", lambda messages, temperature: '{"template":"unknown","top":"setup","bottom":"punchline"}')
    result = generate_module.generate("a long Monday")
    assert result["template"] in {"Two Panel", "Four Panel", "Big Mood", "Expectation Reality", "Tiny Victory"}
    assert result["bottom"] == "punchline"


def test_generate_retries_bad_json(monkeypatch) -> None:
    """Retry malformed caption output before returning valid captions."""
    replies = iter(["bad output", '{"template":"Big Mood","top":"rough","bottom":"coffee"}'])
    monkeypatch.setattr(generate_module, "complete", lambda messages, temperature: next(replies))
    assert generate_module.generate("rough morning")["template"] == "Big Mood"


def test_generate_does_not_repeat_failed_api_retry_cycle(monkeypatch) -> None:
    """Raise after the model wrapper exhausts its own request retries."""
    calls = []

    def fail(messages, temperature):
        """Simulate the exhausted retries from the model wrapper."""
        calls.append(1)
        raise generate_module.LLMError("request timed out")

    monkeypatch.setattr(generate_module, "complete", fail)
    with pytest.raises(generate_module.LLMError, match="timed out"):
        generate_module.generate("rough morning")
    assert len(calls) == 1


def test_generate_honors_template_picker(monkeypatch) -> None:
    """Use a valid user-selected template instead of the model's choice."""
    monkeypatch.setattr(
        generate_module,
        "complete",
        lambda messages, temperature: '{"template":"Big Mood","top":"setup","bottom":"punchline"}',
    )
    assert generate_module.generate("long day", "Tiny Victory")["template"] == "Tiny Victory"


def test_fallback_captions_are_short_and_honor_template() -> None:
    """Keep offline caption fallback compact and use a valid selected template."""
    captions = generate_module.fallback_captions("a very long situation " * 20, "Big Mood")
    assert captions["template"] == "Big Mood"
    assert len(captions["top"]) <= 64
    assert captions["bottom"]
