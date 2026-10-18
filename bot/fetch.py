"""Fetch a public meme and avoid previously sent items."""

import json
from typing import Any

import requests

from config import REQUEST_TIMEOUT, SEEN_FILE
from bot.utils import logger

SOURCE_URL = "https://meme-api.com/gimme/{subreddit}"


def _subreddit_for(query: str) -> str:
    """Map common topics to public meme communities supported by the source."""
    normalized = query.lower()
    if any(term in normalized for term in ("football", "soccer", "sports", "basketball")):
        return "sportsmemes"
    if any(term in normalized for term in ("cat", "kitten", "dog", "pet")):
        return "wholesomememes"
    return "memes"


def fetch_from_source(query: str) -> dict[str, str] | None:
    """Request one public meme from the configured source without authentication."""
    response = requests.get(
        SOURCE_URL.format(subreddit=_subreddit_for(query)),
        headers={"User-Agent": "casual-meme-bot/1.0"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    if not isinstance(payload, dict):
        return None
    url, post_id = payload.get("url"), payload.get("postLink")
    if not isinstance(url, str) or not url.startswith("https://") or not isinstance(post_id, str):
        return None
    return {"id": post_id, "url": url, "title": str(payload.get("title", "A meme"))}


def fetch(query: str) -> dict[str, str] | None:
    """Return a not-yet-seen meme and record its ID after successful retrieval."""
    try:
        SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        seen_data = json.loads(SEEN_FILE.read_text(encoding="utf-8")) if SEEN_FILE.exists() else []
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("Could not read meme history: %s", error)
        return None
    if not isinstance(seen_data, list) or any(not isinstance(item, str) for item in seen_data):
        logger.warning("Meme history has an invalid format.")
        return None
    seen = set(seen_data)
    for _ in range(5):
        try:
            meme = fetch_from_source(query)
        except (requests.RequestException, ValueError, TypeError) as error:
            logger.warning("Public meme source failed: %s", error)
            return None
        if not meme:
            return None
        if meme["id"] in seen:
            continue
        seen.add(meme["id"])
        try:
            SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")
        except OSError as error:
            logger.warning("Could not save meme history: %s", error)
        return meme
    return None
