"""Tests for end-to-end chat and follow-up behavior."""

from pathlib import Path

import pytest

from bot import chat


@pytest.fixture(autouse=True)
def configure_mock_model(monkeypatch) -> None:
    """Provide placeholder credentials while all chat dependencies are mocked."""
    monkeypatch.setattr(chat, "MODEL_NAME", "test-model")
    monkeypatch.setattr(chat, "API_KEY", "test-key")


def test_chat_and_generated_meme_follow_up(monkeypatch) -> None:
    """Handle chat-only, generation, and a context-aware meme follow-up."""
    decisions = iter(
        [
            {"action": "chat", "context": "", "query": ""},
            {"action": "generate", "context": "missed the bus", "query": ""},
        ]
    )
    contexts = []
    monkeypatch.setattr(chat, "route", lambda message, history: next(decisions))
    monkeypatch.setattr(chat.ChatBot, "_reply", lambda self, message: "That sounds like a day.")
    monkeypatch.setattr(
        chat,
        "generate",
        lambda context, template_name=None: contexts.append(context)
        or {"template": template_name or "Two Panel", "top": "Late", "bottom": "Again"},
    )
    monkeypatch.setattr(chat, "render", lambda captions: Path("output/meme.png"))
    bot = chat.ChatBot()
    assert bot.handle("rough commute").image_path is None
    generated = bot.handle("I missed the bus and spilled my coffee")
    follow_up = bot.handle("funnier")
    different_template = bot.handle("different template")
    assert generated.image_path == str(Path("output/meme.png"))
    assert follow_up.image_path == str(Path("output/meme.png"))
    assert different_template.image_path == str(Path("output/meme.png"))
    assert "missed the bus" in contexts[1]
    assert "funnier" in contexts[1]
    assert "Do not use the Two Panel template" in contexts[2]


def test_fetch_failure_falls_back_to_generated_meme(monkeypatch) -> None:
    """Create a custom meme and explain the fallback when fetching is empty."""
    monkeypatch.setattr(chat, "route", lambda message, history: {
        "action": "fetch", "context": "football", "query": "football"
    })
    monkeypatch.setattr(chat, "fetch", lambda query: None)
    monkeypatch.setattr(
        chat,
        "generate",
        lambda context, template_name=None: {
            "template": template_name or "Two Panel",
            "top": "A",
            "bottom": "B",
        },
    )
    monkeypatch.setattr(chat, "render", lambda captions: Path("output/fallback.png"))
    result = chat.ChatBot().handle("football meme")
    assert "couldn't find a fresh one" in result.reply
    assert result.image_path == str(Path("output/fallback.png"))


def test_fetch_result_returns_url(monkeypatch) -> None:
    """Return a fetched meme URL from the chat handler."""
    monkeypatch.setattr(chat, "route", lambda message, history: {
        "action": "fetch", "context": "", "query": "football"
    })
    monkeypatch.setattr(
        chat, "fetch", lambda query: {"id": "1", "url": "https://example.com/meme.png", "title": "Nice"}
    )
    result = chat.ChatBot().handle("football meme")
    assert result.image_path == "https://example.com/meme.png"


def test_scripted_chat_generate_fetch_and_follow_up(monkeypatch) -> None:
    """Run one scripted session covering chat, both meme paths, and a follow-up."""
    decisions = iter(
        [
            {"action": "chat", "context": "", "query": ""},
            {"action": "generate", "context": "forgot my lunch", "query": ""},
            {"action": "fetch", "context": "", "query": "football"},
        ]
    )
    generated_contexts = []
    fetch_queries = []
    monkeypatch.setattr(chat, "route", lambda message, history: next(decisions))
    monkeypatch.setattr(chat.ChatBot, "_reply", lambda self, message: "That is a rough one.")
    monkeypatch.setattr(
        chat,
        "generate",
        lambda context, template_name=None: generated_contexts.append(context)
        or {"template": "Big Mood", "top": "Oops", "bottom": "Lunch"},
    )
    monkeypatch.setattr(chat, "render", lambda captions: Path("output/generated.png"))
    monkeypatch.setattr(
        chat,
        "fetch",
        lambda query: fetch_queries.append(query)
        or {"id": "football-1", "url": "https://example.com/football.png", "title": "Score"},
    )
    bot = chat.ChatBot()
    chat_reply = bot.handle("I forgot lunch")
    generated = bot.handle("Now I am hungry")
    fetched = bot.handle("football topic")
    follow_up = bot.handle("another one")
    assert chat_reply.image_path is None
    assert generated.image_path == str(Path("output/generated.png"))
    assert fetched.image_path == "https://example.com/football.png"
    assert follow_up.image_path == fetched.image_path
    assert generated_contexts == ["forgot my lunch"]
    assert fetch_queries == ["football", "football"]


def test_missing_model_stops_message_processing(monkeypatch) -> None:
    """Show the exact required model setting without calling the router."""
    monkeypatch.setattr(chat, "MODEL_NAME", "")
    monkeypatch.setattr(chat, "route", lambda message, history: pytest.fail("router must not run"))
    result = chat.ChatBot().handle("hello")
    assert result.reply == "Add MODEL_NAME=your-Gemma-4-26B-A4B-IT-model-id to .env before chatting."


def test_session_state_and_forced_generation_mode(monkeypatch) -> None:
    """Keep memory in the supplied session mapping and honor generate mode."""
    state = {}
    bot = chat.ChatBot(memory_state=state)
    generated = []
    monkeypatch.setattr(chat, "route", lambda message, history: pytest.fail("auto router must not run"))
    monkeypatch.setattr(
        chat,
        "generate",
        lambda context, template_name=None: generated.append((context, template_name))
        or {"template": template_name, "top": "Today", "bottom": "Again"},
    )
    monkeypatch.setattr(chat, "render", lambda captions: Path("output/session.png"))
    result = bot.handle("my long day", mode="generate", template_name="Big Mood")
    same_session = chat.ChatBot(memory_state=state)
    other_session = chat.ChatBot(memory_state={})
    assert result.image_path == str(Path("output/session.png"))
    assert generated == [("my long day", "Big Mood")]
    assert len(same_session.memory.history) == 2
    assert same_session.memory.last_meme["template"] == "Big Mood"
    assert other_session.memory.history == []


def test_forced_fetch_fallback_uses_requested_topic(monkeypatch) -> None:
    """Generate a topic-specific meme when the forced fetch has no result."""
    contexts = []
    monkeypatch.setattr(chat, "fetch", lambda query: None)
    monkeypatch.setattr(
        chat,
        "generate",
        lambda context, template_name=None: contexts.append(context)
        or {"template": "Big Mood", "top": "Game", "bottom": "Day"},
    )
    monkeypatch.setattr(chat, "render", lambda captions: Path("output/fallback.png"))
    result = chat.ChatBot().handle("football", mode="fetch")
    assert "couldn't find a fresh one" in result.reply
    assert contexts == ["football"]


def test_explicit_meme_request_skips_router(monkeypatch) -> None:
    """Send an obvious request for a meme to the fetch flow directly."""
    fetched = []
    monkeypatch.setattr(
        chat, "route", lambda message, history: pytest.fail("explicit request should skip router")
    )
    monkeypatch.setattr(
        chat,
        "fetch",
        lambda query: fetched.append(query)
        or {"id": "marvel-1", "url": "https://example.com/marvel.png", "title": "Marvel"},
    )
    result = chat.ChatBot().handle("Give me a Marvel meme")
    assert result.image_path == "https://example.com/marvel.png"
    assert fetched == ["Give me a Marvel meme"]


def test_model_timeout_still_renders_and_reports_local_meme(monkeypatch) -> None:
    """Produce a usable meme image when Gemma times out during captioning."""
    monkeypatch.setattr(
        chat,
        "route",
        lambda message, history: {"action": "generate", "context": message, "query": ""},
    )
    monkeypatch.setattr(
        chat, "generate", lambda context, template_name=None: (_ for _ in ()).throw(chat.LLMError("timed out"))
    )
    monkeypatch.setattr(chat, "render", lambda captions: Path("output/fallback.png"))
    result = chat.ChatBot().handle("A tired day")
    assert result.image_path == str(Path("output/fallback.png"))
    assert "made a quick meme locally" in result.reply
