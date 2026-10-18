"""Tests for model-backed routing."""

from bot import router


def test_route_valid_json(monkeypatch) -> None:
    """Return a valid action and strings from model JSON."""
    monkeypatch.setattr(router, "complete", lambda messages, temperature: '{"action":"fetch","context":"","query":"football"}')
    assert router.route("football meme") == {
        "action": "fetch",
        "context": "",
        "query": "football",
    }


def test_route_retries_invalid_json(monkeypatch) -> None:
    """Retry malformed model JSON before returning a valid decision."""
    replies = iter(["not json", '{"action":"generate","context":"bad day","query":""}'])
    monkeypatch.setattr(router, "complete", lambda messages, temperature: next(replies))
    result = router.route("make a meme")
    assert result["action"] == "generate"


def test_route_falls_back_after_invalid_fields(monkeypatch) -> None:
    """Fall back to ordinary chat after three invalid decisions."""
    monkeypatch.setattr(router, "complete", lambda messages, temperature: '{"action":"other","context":"","query":""}')
    assert router.route("hello")["action"] == "chat"


def test_route_does_not_repeat_failed_api_retry_cycle(monkeypatch) -> None:
    """Return a chat fallback after the LLM wrapper exhausts its retries."""
    calls = []

    def fail(messages, temperature):
        """Simulate the exhausted retries from the model wrapper."""
        calls.append(1)
        raise router.LLMError("request timed out")

    monkeypatch.setattr(router, "complete", fail)
    assert router.route("hello")["action"] == "chat"
    assert len(calls) == 1
