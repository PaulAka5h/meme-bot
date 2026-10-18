"""Load environment settings and project paths."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

MODEL_NAME = os.getenv("MODEL_NAME", "").strip()
API_KEY = os.getenv("API_KEY", "").strip()
BASE_URL = os.getenv(
    "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
).strip().rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "8"))
TEMPLATES_FILE = ROOT / "templates" / "templates.json"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
SEEN_FILE = DATA_DIR / "seen.json"
PROMPTS_DIR = ROOT / "prompts"
