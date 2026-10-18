"""Streamlit chat interface for the meme bot."""

import json
from io import BytesIO
import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
from PIL import Image

from bot.chat import ChatBot, ChatResult
from bot.memory import HISTORY_KEY, LAST_MEME_KEY
from config import TEMPLATES_FILE

logger = logging.getLogger("meme_bot")
UI_MESSAGES_KEY = "meme_bot_ui_messages"
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _template_names() -> list[str]:
    """Read template names for the sidebar picker."""
    templates = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    return [item["name"] for item in templates]


def _load_image(image_path: str) -> tuple[bytes, str, str]:
    """Load a local or fetched image for display and download."""
    parsed = urlparse(image_path)
    if parsed.scheme in {"http", "https"}:
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Only secure image URLs can be loaded.")
        with requests.get(image_path, timeout=(5, 15), stream=True) as response:
            response.raise_for_status()
            if urlparse(response.url).scheme != "https":
                raise ValueError("The meme image redirected to an insecure URL.")
            mime_type = response.headers.get("Content-Type", "").split(";", 1)[0]
            if not mime_type.startswith("image/"):
                raise ValueError("The meme source did not return an image.")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    raise ValueError("The meme image is too large to download.")
                chunks.append(chunk)
            extension = mimetypes.guess_extension(mime_type) or ".img"
            image_data = b"".join(chunks)
            with Image.open(BytesIO(image_data)) as image:
                image.verify()
            return image_data, f"meme{extension}", mime_type
    path = Path(image_path)
    image_data = path.read_bytes()
    with Image.open(BytesIO(image_data)) as image:
        image.verify()
    return image_data, path.name, mimetypes.guess_type(path.name)[0] or "image/png"


def _submit_message(
    message: str,
    bot: ChatBot,
    mode: str,
    template_name: str | None,
) -> None:
    """Run one message and persist its reply in this Streamlit session."""
    st.session_state[UI_MESSAGES_KEY].append({"role": "user", "content": message})
    with st.chat_message("user"):
        st.markdown(message)
    with st.spinner("Thinking up a reply..."):
        try:
            result = bot.handle(message, mode=mode, template_name=template_name)
        except Exception as error:
            logger.warning("Chat request failed: %s", error)
            result = ChatResult("I couldn't finish that just now. Please try again in a bit.")
        image_data = None
        filename = ""
        mime_type = ""
        if result.image_path:
            try:
                image_data, filename, mime_type = _load_image(result.image_path)
            except (OSError, requests.RequestException, ValueError) as error:
                logger.warning("Meme image could not be loaded: %s", error)
        entry = {"role": "assistant", "content": result.reply}
        if result.image_path:
            entry.update(
                {
                    "image_path": result.image_path,
                    "image_data": image_data,
                    "filename": filename,
                    "mime_type": mime_type,
                }
            )
        st.session_state[UI_MESSAGES_KEY].append(entry)
    st.rerun()


def main() -> None:
    """Render the interactive meme chat page."""
    st.set_page_config(page_title="Meme Bot", page_icon=None)
    st.title("Meme Bot")
    st.write("Tell me about your day or pick a topic, and we'll find a meme for it.")

    st.session_state.setdefault(UI_MESSAGES_KEY, [])
    st.session_state.setdefault(HISTORY_KEY, [])
    st.session_state.setdefault(LAST_MEME_KEY, None)
    bot = ChatBot(memory_state=st.session_state)
    with st.sidebar:
        st.header("Chat settings")
        selected_mode = st.selectbox(
            "Mode",
            ["Auto", "Always generate", "Always fetch"],
            help="Choose how each new message should be handled.",
        )
        template_names = _template_names()
        selected_template = st.selectbox("Meme template", ["Auto"] + template_names)
        if st.button("Clear chat", use_container_width=True):
            st.session_state[UI_MESSAGES_KEY] = []
            st.session_state[HISTORY_KEY] = []
            st.session_state[LAST_MEME_KEY] = None
            st.rerun()

    mode = {"Auto": "auto", "Always generate": "generate", "Always fetch": "fetch"}[
        selected_mode
    ]
    template_name = None if selected_template == "Auto" else selected_template
    for index, entry in enumerate(st.session_state[UI_MESSAGES_KEY]):
        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])
            if entry.get("image_path"):
                if entry.get("image_data"):
                    st.image(entry["image_data"], width="stretch")
                else:
                    st.caption("This meme image could not be loaded.")
                columns = st.columns(3)
                with columns[0]:
                    if st.button("Another one", key=f"another-{index}"):
                        _submit_message("another one", bot, mode, template_name)
                with columns[1]:
                    if st.button("Funnier", key=f"funnier-{index}"):
                        _submit_message("funnier", bot, mode, template_name)
                with columns[2]:
                    st.download_button(
                        "Download meme",
                        data=entry.get("image_data") or b"",
                        file_name=entry.get("filename") or "meme.png",
                        mime=entry.get("mime_type") or "image/png",
                        disabled=not entry.get("image_data"),
                        key=f"download-{index}",
                    )

    prompt = st.chat_input("Tell me what happened or name a meme topic")
    if prompt:
        _submit_message(prompt, bot, mode, template_name)


if __name__ == "__main__":
    main()
