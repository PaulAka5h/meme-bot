"""Tests for the configured model API wrapper."""

import requests
import pytest

from bot import llm


def test_complete_uses_configured_model(monkeypatch) -> None:
    """Send the model ID configured in settings and return response text."""
    calls = []

    class Response:
        """Provide a minimal successful fake HTTP response."""

        status_code = 200

        def raise_for_status(self) -> None:
            """Accept the successful fake HTTP status."""

        def json(self) -> dict:
            """Return the expected chat completion payload."""
            return {"choices": [{"message": {"content": '{"reply":"hey"}'}}]}

    def post(url, **kwargs):
        """Capture the configured API request and return a successful response."""
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(llm, "MODEL_NAME", "test-gemma-model")
    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", post)
    assert llm.complete([{"role": "user", "content": "hello"}]) == '{"reply":"hey"}'
    assert calls[0][1]["json"]["model"] == "test-gemma-model"


def test_complete_retries_transient_errors(monkeypatch) -> None:
    """Retry connection failures and succeed on the third request."""
    attempts = []
    monkeypatch.setattr(llm, "MODEL_NAME", "test-model")
    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)

    def post(url, **kwargs):
        """Raise temporary connection failures before succeeding."""
        attempts.append(url)
        if len(attempts) < 3:
            raise requests.ConnectionError("temporary")

        class Response:
            """Provide a successful completion after the transient errors."""

            def raise_for_status(self) -> None:
                """Accept the successful fake HTTP status."""

            def json(self) -> dict:
                """Return a valid model response payload."""
                return {"choices": [{"message": {"content": "ok"}}]}

        return Response()

    monkeypatch.setattr(llm.requests, "post", post)
    assert llm.complete([]) == "ok"
    assert len(attempts) == 3


def test_complete_requires_model_id(monkeypatch) -> None:
    """Stop before making a request when MODEL_NAME is missing."""
    monkeypatch.setattr(llm, "MODEL_NAME", "")
    with pytest.raises(llm.LLMError, match="MODEL_NAME=your-Gemma"):
        llm.complete([])


def test_complete_does_not_retry_timeouts(monkeypatch) -> None:
    """Fail promptly on a read timeout so the caller can use local fallback."""
    calls = []

    def timeout(url, **kwargs):
        """Simulate an API response that times out."""
        calls.append(url)
        raise requests.Timeout("provider timed out")

    monkeypatch.setattr(llm, "MODEL_NAME", "test-model")
    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", timeout)
    with pytest.raises(llm.LLMError, match="timed out"):
        llm.complete([])
    assert len(calls) == 1
