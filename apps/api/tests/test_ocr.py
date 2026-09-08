"""OCR pipeline (§18): scanned/photographed documents should still be searchable."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from meza.services.documents import extract_text, ocr_available, ocr_image


def _render_text_image(text: str, suffix: str = ".png") -> Path:
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    img = Image.new("RGB", (900, 100), color="white")
    ImageDraw.Draw(img).text((10, 20), text, fill="black", font=font)
    path = Path(tempfile.mktemp(suffix=suffix))
    img.save(path)
    return path


@pytest.mark.skipif(not ocr_available(), reason="tesseract not installed on this host")
def test_ocr_extracts_text_from_synthetic_image():
    path = _render_text_image("ORDER AT-1001 CONTRACT")
    text = ocr_image(path)
    assert "AT-1001" in text.upper()


@pytest.mark.skipif(not ocr_available(), reason="tesseract not installed on this host")
def test_extract_text_dispatches_images_to_ocr():
    path = _render_text_image("INVOICE", suffix=".jpg")
    text = extract_text(path, ".jpg")
    assert "INVOICE" in text.upper()


def test_extract_text_returns_empty_string_for_unreadable_file():
    path = Path(tempfile.mktemp(suffix=".png"))
    path.write_bytes(b"not a real image")
    assert extract_text(path, ".png") == ""
