from PIL import Image, ImageDraw
from pathlib import Path
import pytest

from ai_ocr.ocr_engine import extract_text, extract_words_with_boxes


@pytest.fixture
def korean_image(tmp_path: Path) -> Image.Image:
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "테스트 문서", fill="black")
    path = tmp_path / "korean.png"
    img.save(path)
    return Image.open(path)


def test_extract_text_korean(korean_image: Image.Image):
    result = extract_text(korean_image, lang="kor")
    assert isinstance(result, str)


def test_extract_words_korean(korean_image: Image.Image):
    words = extract_words_with_boxes(korean_image, lang="kor")
    assert isinstance(words, list)
