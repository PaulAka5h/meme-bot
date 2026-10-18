# Decisions

- Keep all application logic in Python and isolate terminal input in `main.py` from `ChatBot.handle()`.
- Use the Google Generative Language OpenAI-compatible endpoint by default and let `.env` select the exact model ID and API key.
- Require strict JSON in every model prompt, validate returned fields, and retry malformed output at most twice.
- Use Meme API subreddit feeds as the replaceable, unauthenticated fetch source; fall back to generated memes when it fails or repeats.
- Store only fetched post IDs locally to avoid repeats without downloading or retaining third-party images.
- Draw captions with Pillow using five included, replaceable 800-by-600 placeholder templates.
- Keep a bounded in-memory conversation history and the last meme context for follow-up requests.
- Pin Pillow, python-dotenv, requests, and pytest in `requirements.txt`.
- Pin a Streamlit-compatible Pillow release because Streamlit requires Pillow below version 13.
- Mock model and fetch calls in all unit tests so tests never make network requests.
- Add Streamlit as a separate UI that reuses `ChatBot.handle()` and leaves terminal `main.py` unchanged.
- Back Streamlit chat history and last-meme context with each browser session's `st.session_state` mapping.
- Let the UI select auto, forced generation, forced fetching, and an optional preferred meme template.
- Store displayed meme bytes in session history so images and downloads remain available across Streamlit reruns.
- Route explicit "give me a meme" and "make a meme" requests deterministically so a chat classification cannot hide the requested image.
- Stop repeating timed-out model requests and render a clearly identified local-caption meme as a graceful fallback.
- Stretch rendered meme images to the available chat width to keep them visible in the interface.
