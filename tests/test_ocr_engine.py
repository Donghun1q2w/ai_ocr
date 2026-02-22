from pathlib import Path
from PIL import Image

from ai_ocr.ocr_engine import extract_text, extract_words_with_boxes, OcrWord


def test_extract_text_returns_string(sample_image: Image.Image):
    result = extract_text(sample_image)
    assert isinstance(result, str)
    assert len(result) > 0


def test_extract_words_with_boxes_returns_list(sample_image: Image.Image):
    words = extract_words_with_boxes(sample_image)
    assert isinstance(words, list)
    assert len(words) > 0


def test_ocr_word_has_required_fields(sample_image: Image.Image):
    words = extract_words_with_boxes(sample_image)
    word = words[0]
    assert isinstance(word, OcrWord)
    assert isinstance(word.text, str)
    assert isinstance(word.left, int)
    assert isinstance(word.top, int)
    assert isinstance(word.width, int)
    assert isinstance(word.height, int)
    assert isinstance(word.confidence, float)


def test_extract_words_with_boxes_filters_low_confidence(sample_image: Image.Image):
    words = extract_words_with_boxes(sample_image, min_confidence=0)
    all_words = extract_words_with_boxes(sample_image, min_confidence=-1)
    assert len(words) <= len(all_words)
