"""Draw readable captions on a configured meme template."""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from config import OUTPUT_DIR, TEMPLATES_DIR, TEMPLATES_FILE


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load Pillow's bundled scalable font at the requested size."""
    return ImageFont.load_default(size=size)


def _wrap(text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, width: int) -> list[str]:
    """Wrap text by measured pixel width, including unbroken long words."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ""
            while draw.textbbox((0, 0), word, font=font)[2] > width and len(word) > 1:
                split_at = max(1, len(word) // 2)
                while split_at > 1 and draw.textbbox((0, 0), word[:split_at], font=font)[2] > width:
                    split_at -= 1
                lines.append(word[:split_at])
                word = word[split_at:]
            line = word
        lines.append(line)
    return lines or [""]


def _draw_caption(image: Image.Image, text: str, box: list[int], base_size: int) -> None:
    """Wrap, shrink, and center outlined white text inside its box."""
    x1, y1, x2, y2 = box
    draw = ImageDraw.Draw(image)
    width, height = max(1, x2 - x1), max(1, y2 - y1)
    for size in range(base_size, 7, -1):
        font = _font(size)
        lines = _wrap(text.strip(), font, draw, max(1, width - 12))
        spacing = max(2, size // 5)
        line_heights = [draw.textbbox((0, 0), line or " ", font=font)[3] for line in lines]
        total_height = sum(line_heights) + spacing * max(0, len(lines) - 1)
        if total_height <= height - 4:
            break
    else:
        size = 8
        font = _font(size)
        lines = _wrap(text.strip(), font, draw, max(1, width - 12))
        spacing = 2
        max_lines = max(1, (height - 4) // (size + spacing))
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = (lines[-1][: max(0, len(lines[-1]) - 3)] + "...") if lines[-1] else "..."
    line_heights = [draw.textbbox((0, 0), line or " ", font=font)[3] for line in lines]
    total_height = sum(line_heights) + spacing * max(0, len(lines) - 1)
    y = y1 + max(0, (height - total_height) // 2)
    for line, line_height in zip(lines, line_heights):
        line_width = draw.textbbox((0, 0), line, font=font)[2]
        x = x1 + max(0, (width - line_width) // 2)
        draw.text(
            (x, y), line, font=font, fill="white", stroke_width=max(1, size // 12), stroke_fill="black"
        )
        y += line_height + spacing


def render(captions: dict[str, str]) -> Path:
    """Render captions on the selected or a random valid template and save it."""
    templates: list[dict[str, Any]] = json.loads(
        TEMPLATES_FILE.read_text(encoding="utf-8")
    )
    if not templates:
        raise ValueError("No meme templates are configured.")
    selected = next(
        (item for item in templates if item["name"] == captions.get("template")),
        random.choice(templates),
    )
    source = TEMPLATES_DIR / selected["file"]
    if not source.is_file():
        raise FileNotFoundError(f"Template image does not exist: {source}")
    with Image.open(source) as original:
        image = original.convert("RGB")
    boxes = selected["text_boxes"]
    size = int(selected["font_size"])
    _draw_caption(image, captions.get("top", ""), boxes["top"], size)
    _draw_caption(image, captions.get("bottom", ""), boxes["bottom"], size)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"meme_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    target = OUTPUT_DIR / filename
    image.save(target, format="PNG")
    return target
