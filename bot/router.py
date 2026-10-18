"""Choose chat, custom meme generation, or meme fetching."""

import json
from typing import Any

from config import PROMPTS_DIR
from bot.llm import LLMError, complete
from bot.utils import extract_json, logger

VALID_ACTIONS = {"chat", "generate", "fetch"}
GENERATE_TERMS = ("make", "create", "generate", "draw", "custom")
FETCH_TERMS = ("give", "find", "show", "get", "send", "fetch")


def explicit_meme_decision(message: str) -> dict[str, str] | None:
    """Recognize clear meme requests without relying on model classification."""
    normalized = message.lower()
    if "meme" not in normalized:
        return None
    if any(term in normalized for term in GENERATE_TERMS):
        return {"action": "generate", "context": message, "query": ""}
    if any(term in normalized for term in FETCH_TERMS):
        return {"action": "fetch", "context": "", "query": message}
    return None


def route(message: str, history: list[dict[str, str]] | None = None) -> dict[str, str]:
    """Ask Gemma for a validated routing decision."""
    system_prompt = (PROMPTS_DIR / "router.txt").read_text(encoding="utf-8")
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": message})
    for attempt in range(3):
        try:
            raw = complete(messages, temperature=0.3)
            value: dict[str, Any] = extract_json(raw)
            action = value.get("action")
            context = value.get("context")
            query = value.get("query")
            if (
                not isinstance(action, str)
                or action not in VALID_ACTIONS
                or not isinstance(context, str)
                or not isinstance(query, str)
            ):
                raise ValueError("Routing response has invalid fields.")
            return {"action": action, "context": context.strip(), "query": query.strip()}
        except LLMError as error:
            logger.warning("Router model request failed: %s", error)
            return {"action": "chat", "context": "", "query": ""}
        except ValueError as error:
            logger.warning("Router attempt %s failed: %s", attempt + 1, error)
            if attempt == 2:
                return {"action": "chat", "context": "", "query": ""}
    return {"action": "chat", "context": "", "query": ""}
