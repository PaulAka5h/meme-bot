# Meme Bot

A Python chat buddy with terminal and Streamlit front ends. It replies casually, makes captioned memes with Gemma and Pillow, or fetches public memes. The chat interfaces are separate from the bot logic, so either can call `ChatBot.handle()` without duplicating the core flow.

## Setup

Python 3.10 or newer is required. From this folder, install the pinned dependencies and copy the example environment file:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and provide the API key and exact model ID for Gemma 4 26B A4B IT. The model ID is intentionally not included in the source code:

```dotenv
API_KEY=your_provider_api_key
MODEL_NAME=your-exact-Gemma-4-26B-A4B-IT-model-id
BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

The configured provider must expose an OpenAI-compatible chat completions endpoint and support your exact model ID. Change `BASE_URL` if your provider uses another endpoint. Without `MODEL_NAME` or `API_KEY`, the bot stays friendly and explains what to configure, but model replies and custom meme captions cannot be generated.

## Run

```powershell
python main.py
```

Type `quit` or `exit` to leave. The bot keeps a short conversation history and uses recent meme context for requests such as “another one,” “funnier,” “different template,” or “make it about X.” Generated files go to `output/`; fetched memes are shown as URLs. The fetch source is the public, unauthenticated Meme API at `https://meme-api.com`, with IDs saved in `data/seen.json` to avoid repeats. The source was checked with a real unauthenticated request during setup. If it is unavailable or has no fresh result, the bot tries to make a custom meme instead.

For the interactive Streamlit chat, run:

```powershell
streamlit run app.py
```

The web UI keeps its chat and follow-up memory in the active Streamlit session. Its sidebar can choose automatic routing, always-generate, or always-fetch mode, select a meme template, and clear the session chat. Use the buttons beneath a meme for another version or a funnier one, or download the image.

## Test

```powershell
python -m pytest -q
```

Tests mock model and fetch calls; running them does not access the network.

## Templates

Five simple placeholder images are included so the bot works immediately. Replace the PNGs in `templates/` with your own meme images, keeping the filenames or updating `templates/templates.json`. Each entry has a unique `name`, image `file`, pixel-coordinate `text_boxes` for `top` and `bottom` (`[left, top, right, bottom]`), base `font_size`, and a `use_when` description used by the caption model. Pillow wraps and scales the white, black-outlined text to fit these regions. No AI image generation is used.

## Project layout

- `main.py` is the terminal loop; `bot/chat.py` provides the interface-independent message handler.
- `bot/llm.py` is the single configured Gemma API wrapper; routing and caption behavior are specified in `prompts/`.
- `bot/fetch.py` isolates the public meme source so it can be swapped independently.
- `data/seen.json` stores fetched meme IDs; `output/` holds generated images.
