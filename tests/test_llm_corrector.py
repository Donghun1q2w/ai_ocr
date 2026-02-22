import json
import pytest
from unittest.mock import MagicMock, patch

from ai_ocr.llm_corrector import correct_ocr_text, build_correction_prompt
from ai_ocr.ocr_engine import OcrWord


@pytest.fixture
def sample_ocr_words() -> list[OcrWord]:
    return [
        OcrWord(text="Helo", left=10, top=30, width=50, height=20, confidence=72.0, line_num=1, block_num=1),
        OcrWord(text="Wrld", left=70, top=30, width=50, height=20, confidence=65.0, line_num=1, block_num=1),
        OcrWord(text="Test", left=10, top=60, width=50, height=20, confidence=95.0, line_num=2, block_num=1),
    ]


def test_build_correction_prompt_contains_words(sample_ocr_words):
    prompt = build_correction_prompt(sample_ocr_words)
    assert "Helo" in prompt
    assert "Wrld" in prompt
    assert "Test" in prompt


def test_build_correction_prompt_contains_confidence(sample_ocr_words):
    prompt = build_correction_prompt(sample_ocr_words)
    assert "72.0" in prompt or "72" in prompt


@patch("ai_ocr.llm_corrector._call_gemini")
def test_correct_ocr_text_returns_corrected_words(mock_gemini, sample_ocr_words):
    mock_gemini.return_value = json.dumps([
        {"index": 0, "original": "Helo", "corrected": "Hello"},
        {"index": 1, "original": "Wrld", "corrected": "World"},
    ])
    result = correct_ocr_text(sample_ocr_words)
    assert result[0].text == "Hello"
    assert result[1].text == "World"
    assert result[2].text == "Test"  # unchanged


@patch("ai_ocr.llm_corrector._call_gemini")
def test_correct_ocr_text_preserves_positions(mock_gemini, sample_ocr_words):
    mock_gemini.return_value = json.dumps([
        {"index": 0, "original": "Helo", "corrected": "Hello"},
    ])
    result = correct_ocr_text(sample_ocr_words)
    assert result[0].left == 10
    assert result[0].top == 30
    assert result[0].width == 50
    assert result[0].height == 20


@patch("ai_ocr.llm_corrector._call_gemini")
def test_correct_ocr_text_handles_empty_response(mock_gemini, sample_ocr_words):
    mock_gemini.return_value = "[]"
    result = correct_ocr_text(sample_ocr_words)
    assert result[0].text == "Helo"  # unchanged
    assert result[1].text == "Wrld"  # unchanged


@patch("ai_ocr.llm_corrector._call_gemini")
def test_correct_ocr_text_handles_malformed_response(mock_gemini, sample_ocr_words):
    mock_gemini.return_value = "not valid json"
    result = correct_ocr_text(sample_ocr_words)
    assert result[0].text == "Helo"
    assert result[1].text == "Wrld"
