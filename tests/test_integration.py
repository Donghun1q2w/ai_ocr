import os
import pytest
from pathlib import Path
from PIL import Image, ImageDraw

from ai_ocr.pipeline import OcrPipeline

requires_api_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set"
)


@pytest.fixture
def noisy_text_image(tmp_path: Path) -> Image.Image:
    """Create an image that Tesseract might misread."""
    img = Image.new("RGB", (600, 150), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "The quick brown fox jumps", fill="black")
    draw.text((10, 70), "over the lazy dog", fill="black")
    path = tmp_path / "noisy.png"
    img.save(path)
    return Image.open(path)


@requires_api_key
def test_full_pipeline_with_gemini(noisy_text_image: Image.Image):
    """End-to-end test: Tesseract -> Gemini correction."""
    pipeline = OcrPipeline(use_llm=True)
    result = pipeline.run(noisy_text_image)

    assert result.raw_text  # Tesseract produced something
    assert result.corrected_text  # LLM produced something
    assert len(result.corrected_words) > 0
    # Positions should be preserved
    for orig, corrected in zip(result.words, result.corrected_words):
        assert orig.left == corrected.left
        assert orig.top == corrected.top
