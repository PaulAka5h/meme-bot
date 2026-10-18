"""Keep short conversation history and context for meme follow-ups."""

from collections.abc import MutableMapping
from typing import Any

from config import MAX_HISTORY

HISTORY_KEY = "meme_bot_history"
LAST_MEME_KEY = "meme_bot_last_meme"

FOLLOW_UPS = {
    "another one": "another",
    "one more": "another",
    "funnier": "funnier",
    "make it funnier": "funnier",
    "different template": "different template",
}


class ChatMemory:
    """Store recent messages and the last meme request."""

    def __init__(self, state: MutableMapping[str, Any] | None = None) -> None:
        """Initialize memory backed by a caller-provided session mapping."""
        self.state = state if state is not None else {}
        self.state.setdefault(HISTORY_KEY, [])
        self.state.setdefault(LAST_MEME_KEY, None)

    @property
    def history(self) -> list[dict[str, str]]:
        """Return recent chat messages from the session mapping."""
        return self.state[HISTORY_KEY]

    @property
    def last_meme(self) -> dict[str, str] | None:
        """Return the last meme request from the session mapping."""
        return self.state[LAST_MEME_KEY]

    def add_exchange(self, user: str, assistant: str) -> None:
        """Append an exchange and retain only the configured history window."""
        history = self.history
        history.extend([{"role": "user", "content": user}, {"role": "assistant", "content": assistant}])
        self.state[HISTORY_KEY] = history[-MAX_HISTORY * 2 :]

    def follow_up(self, message: str) -> dict[str, str] | None:
        """Return adjusted prior meme context when the message is a follow-up."""
        if not self.last_meme:
            return None
        normalized = message.lower().strip()
        kind = next((value for phrase, value in FOLLOW_UPS.items() if phrase in normalized), None)
        if kind is None and normalized.startswith(("make it about ", "about ")):
            kind = "topic"
        if kind is None:
            return None
        context = self.last_meme.get("context", "")
        query = self.last_meme.get("query", "")
        action = self.last_meme.get("action", "generate")
        if kind == "topic":
            topic = normalized.removeprefix("make it about ").removeprefix("about ").strip()
            context = f"{context}. Update the meme to be about {topic}."
            query = topic
        elif kind == "funnier":
            action = "generate"
            context = context or query
            context = f"{context}. Make this version funnier."
        elif kind == "different template":
            action = "generate"
            context = context or query
            context = f"{context}. Use a different template from the previous meme."
            if self.last_meme.get("template"):
                context += f" Do not use the {self.last_meme['template']} template."
        return {
            "action": action,
            "context": context,
            "query": query,
        }

    def remember_meme(self, decision: dict[str, str], template: str | None = None) -> None:
        """Save the context needed to create a related follow-up meme."""
        last_meme = {
            "action": decision["action"],
            "context": decision["context"],
            "query": decision["query"],
        }
        if template:
            last_meme["template"] = template
        self.state[LAST_MEME_KEY] = last_meme
