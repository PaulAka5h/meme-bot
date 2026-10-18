"""Tests for the Streamlit image UI helpers."""

from PIL import Image

from app import _load_image


def test_load_local_meme_image_for_display_and_download(tmp_path) -> None:
    """Return verified image bytes and download metadata for a local meme."""
    image_path = tmp_path / "meme.png"
    Image.new("RGB", (32, 24), "navy").save(image_path)
    image_data, filename, mime_type = _load_image(str(image_path))
    assert image_data.startswith(b"\x89PNG")
    assert filename == "meme.png"
    assert mime_type == "image/png"
