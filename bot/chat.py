"""Coordinate routing, chat replies, meme generation, and fetching."""

from dataclasses import dataclass
from collections.abc import MutableMapping
from typing import Any

from config import API_KEY, MODEL_NAME, PROMPTS_DIR
from bot.fetch import fetch
from bot.generate import fallback_captions, generate
from bot.llm import LLMError, complete
from bot.memory import ChatMemory
from bot.render import render
from bot.router import explicit_meme_decision, route
from bot.utils import extract_json, logger


@dataclass
class ChatResult:
    """Contain the casual reply and optional local image path or image URL."""

    reply: str
    image_path: str | None = None


class ChatBot:
    """Handle messages independently of the terminal interface."""

    def __init__(self, memory_state: MutableMapping[str, Any] | None = None) -> None:
        """Initialize conversation memory with optional caller-owned session state."""
        self.memory = ChatMemory(memory_state)

    def _reply(self, message: str) -> str:
        """Ask Gemma for a short casual JSON chat reply."""
        personality = (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")
        messages = [
            {
                "role": "system",
                "content": (
                    f"{personality}\nEvery answer must be strict JSON with one string field named "
                    '"reply". Keep it casual, short, and without emojis.'
                ),
            },
            *self.memory.history,
            {"role": "user", "content": message},
        ]
        for attempt in range(3):
            try:
                result = extract_json(complete(messages, temperature=0.7))
                reply = result.get("reply")
                if isinstance(reply, str) and reply.strip():
                    return reply.strip()
                raise ValueError("Chat reply JSON must contain a non-empty reply string.")
            except LLMError as error:
                logger.warning("Chat model request failed: %s", error)
                return "I couldn't get a reply from Gemma just now. Check your .env settings and try again."
            except ValueError as error:
                logger.warning("Chat reply attempt %s failed: %s", attempt + 1, error)
                if attempt == 2:
                    return "I couldn't get a reply from Gemma just now. Check your .env settings and try again."
        return "I couldn't get a reply from Gemma just now. Check your .env settings and try again."

    def handle(
        self,
        message: str,
        mode: str = "auto",
        template_name: str | None = None,
    ) -> ChatResult:
        """Process one message in auto, generate, or fetch mode."""
        if mode not in {"auto", "generate", "fetch"}:
            raise ValueError("mode must be 'auto', 'generate', or 'fetch'.")
        if not MODEL_NAME:
            reply = "Add MODEL_NAME=your-Gemma-4-26B-A4B-IT-model-id to .env before chatting."
            self.memory.add_exchange(message, reply)
            return ChatResult(reply)
        if not API_KEY:
            reply = "Add API_KEY=your_provider_api_key to .env before chatting."
            self.memory.add_exchange(message, reply)
            return ChatResult(reply)
        try:
            decision = self.memory.follow_up(message)
            if decision is None:
                if mode == "generate":
                    decision = {"action": "generate", "context": message, "query": ""}
                elif mode == "fetch":
                    decision = {"action": "fetch", "context": "", "query": message}
                else:
                    decision = explicit_meme_decision(message) or route(
                        message, self.memory.history
                    )
        except Exception as error:
            logger.warning("Message routing failed: %s", error)
            reply = "I couldn't sort that out just now. Check your .env settings and try again."
            self.memory.add_exchange(message, reply)
            return ChatResult(reply)
        if decision["action"] == "chat":
            reply = self._reply(message)
            self.memory.add_exchange(message, reply)
            return ChatResult(reply)

        try:
            if decision["action"] == "fetch":
                meme = fetch(decision["query"])
                if meme:
                    self.memory.remember_meme(decision)
                    reply = "Found one for you."
                    self.memory.add_exchange(message, reply)
                    return ChatResult(reply, meme["url"])
                decision["action"] = "generate"
                decision["context"] = decision["context"] or decision["query"]
                notice = "I couldn't find a fresh one, so I made you one instead."
            else:
                notice = ""
            try:
                captions = generate(decision["context"], template_name=template_name)
            except LLMError as error:
                logger.warning("Using local meme captions after Gemma failure: %s", error)
                captions = fallback_captions(decision["context"], template_name)
                fallback_notice = "Gemma is taking a while, so I made a quick meme locally."
                notice = f"{notice} {fallback_notice}".strip()
            image_path = render(captions)
            self.memory.remember_meme(decision, captions["template"])
            reply = f"{notice} Made a meme for you." if notice else "Made a meme for you."
            self.memory.add_exchange(message, reply)
            return ChatResult(reply, str(image_path))
        except Exception as error:
            logger.warning("Meme request failed: %s", error)
            reply = "I couldn't make that meme right now. Check your .env settings or try again in a bit."
            self.memory.add_exchange(message, reply)
            return ChatResult(reply)
