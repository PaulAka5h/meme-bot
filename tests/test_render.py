"""Tests for meme image rendering."""

import json

from PIL import Image

from bot import render as render_module


def test_render_creates_valid_image(tmp_path, monkeypatch) -> None:
    """Render both captions and create a readable PNG."""
    source = tmp_path / "template.png"
    Image.new("RGB", (400, 300), "navy").save(source)
    config = [
        {
            "name": "test",
            "file": source.name,
            "text_boxes": {"top": [0, 0, 400, 140], "bottom": [0, 160, 400, 300]},
            "font_size": 36,
            "use_when": "test",
        }
    ]
    template_config = tmp_path / "templates.json"
    template_config.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "output"
    monkeypatch.setattr(render_module, "TEMPLATES_FILE", template_config)
    monkeypatch.setattr(render_module, "TEMPLATES_DIR", tmp_path)
    monkeypatch.setattr(render_module, "OUTPUT_DIR", output)
    path = render_module.render(
        {"template": "missing name", "top": "A very long caption " * 30, "bottom": "tiny win"}
    )
    assert path.is_file()
    with Image.open(path) as image:
        assert image.size == (400, 300)
        assert image.format == "PNG"
