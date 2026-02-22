from pathlib import Path
from unittest.mock import patch, MagicMock
import json

from PIL import Image

from ai_ocr.pipeline import OcrPipeline, OcrResult, _words_to_text


def test_pipeline_ocr_only(sample_image: Image.Image):
    """Test pipeline with only Tesseract (no LLM correction)."""
    pipeline = OcrPipeline(use_llm=False)
    result = pipeline.run(sample_image)
    assert isinstance(result, OcrResult)
    assert isinstance(result.raw_text, str)
    assert len(result.words) > 0


def test_pipeline_result_has_raw_and_corrected(sample_image: Image.Image):
    """Test that corrected_text is derived from corrected_words."""
    pipeline = OcrPipeline(use_llm=False)
    result = pipeline.run(sample_image)
    assert result.corrected_text == _words_to_text(result.corrected_words)


@patch("ai_ocr.pipeline.correct_ocr_text")
def test_pipeline_with_llm(mock_correct, sample_image: Image.Image):
    """Test pipeline calls LLM correction when enabled."""
    mock_correct.side_effect = lambda words: words  # pass through
    pipeline = OcrPipeline(use_llm=True)
    result = pipeline.run(sample_image)
    mock_correct.assert_called_once()
    assert isinstance(result, OcrResult)


def test_pipeline_from_file(sample_image_path: Path):
    """Test pipeline can load image from file path."""
    pipeline = OcrPipeline(use_llm=False)
    result = pipeline.run_from_file(sample_image_path)
    assert isinstance(result, OcrResult)
    assert len(result.words) > 0
