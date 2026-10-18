"""Choose a template and captions with Gemma."""

import json
import random
from typing import Any

from config import PROMPTS_DIR, TEMPLATES_FILE
from bot.llm import LLMError, complete
from bot.utils import extract_json, logger


def fallback_captions(context: str, template_name: str | None = None) -> dict[str, str]:
    """Make short local captions when Gemma is unavailable."""
    templates = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    if not templates:
        raise ValueError("No meme templates are configured.")
    names = {item["name"] for item in templates}
    selected = template_name if template_name in names else random.choice(templates)["name"]
    headline = " ".join(context.split()).strip()
    if len(headline) > 64:
        headline = headline[:61].rsplit(" ", 1)[0].rstrip(".,;:") + "..."
    if not headline:
        headline = "ANOTHER LONG DAY"
    return {
        "template": selected,
        "top": headline.upper(),
        "bottom": "ME TRYING TO HOLD IT TOGETHER",
    }


def generate(context: str, template_name: str | None = None) -> dict[str, str]:
    """Generate validated meme captions, optionally requesting a chosen template."""
    templates = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    if not templates:
        raise ValueError("No meme templates are configured.")
    descriptions = [
        {"name": item["name"], "use_when": item["use_when"]} for item in templates
    ]
    prompt = (PROMPTS_DIR / "meme.txt").read_text(encoding="utf-8")
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"Situation: {context}\n"
                f"Preferred template: {template_name or 'choose the best fit'}\n"
                f"Templates: {json.dumps(descriptions, ensure_ascii=False)}"
            ),
        },
    ]
    for attempt in range(3):
        try:
            raw = complete(messages, temperature=0.9)
            value: dict[str, Any] = extract_json(raw)
            model_template = value.get("template")
            top = value.get("top")
            bottom = value.get("bottom")
            if not isinstance(top, str) or not isinstance(bottom, str):
                raise ValueError("Caption response has invalid text fields.")
            names = {item["name"] for item in templates}
            if template_name and template_name in names:
                selected_template = template_name
            elif not isinstance(model_template, str) or model_template not in names:
                selected_template = random.choice(templates)["name"]
            else:
                selected_template = model_template
            return {"template": selected_template, "top": top.strip(), "bottom": bottom.strip()}
        except LLMError as error:
            logger.warning("Caption model request failed: %s", error)
            raise
        except (ValueError, KeyError) as error:
            logger.warning("Caption attempt %s failed: %s", attempt + 1, error)
            if attempt == 2:
                raise LLMError("Gemma did not return usable meme captions.") from error
    raise ValueError("Gemma could not create valid meme captions.")
