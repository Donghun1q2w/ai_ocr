from pathlib import Path
from unittest.mock import patch, MagicMock
import json

import pytest
import fitz
from PIL import Image

from ai_ocr.pipeline import OcrPipeline, PipelineResult
from ai_ocr.ocr_engine import OcrWord


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a 2-page PDF with text for testing."""
    doc = fitz.open()
    for i in range(2):
        page = doc.new_page(width=612, height=792)
        page.insert_text(fitz.Point(72, 72), f"Page {i+1} test text", fontsize=14)
    pdf_path = tmp_path / "test.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@patch("ai_ocr.pipeline.correct_ocr_text")
@patch("ai_ocr.pipeline.extract_words_with_boxes")
def test_process_pdf_creates_output(mock_ocr, mock_llm, sample_pdf, tmp_path):
    """Test that process_pdf creates an output PDF."""
    mock_words = [
        OcrWord(text="Hello", left=100, top=100, width=80, height=30,
                confidence=95.0, line_num=1, block_num=1, page_num=0),
    ]
    mock_ocr.return_value = mock_words
    mock_llm.side_effect = lambda words, **kw: words

    out_pdf = tmp_path / "output.pdf"
    pipeline = OcrPipeline(use_llm=True)
    result = pipeline.process_pdf(sample_pdf, out_pdf)

    assert out_pdf.exists()
    assert isinstance(result, PipelineResult)
    assert result.total_pages == 2
    assert result.total_words == 2  # 1 word per page × 2 pages


@patch("ai_ocr.pipeline.extract_words_with_boxes")
def test_process_pdf_no_llm(mock_ocr, sample_pdf, tmp_path):
    """Test pipeline without LLM correction."""
    mock_words = [
        OcrWord(text="Test", left=50, top=50, width=60, height=25,
                confidence=90.0, line_num=1, block_num=1, page_num=0),
    ]
    mock_ocr.return_value = mock_words

    out_pdf = tmp_path / "output.pdf"
    pipeline = OcrPipeline(use_llm=False)
    result = pipeline.process_pdf(sample_pdf, out_pdf)

    assert out_pdf.exists()
    assert result.corrected_words == 0


@patch("ai_ocr.pipeline.extract_words_with_boxes")
def test_process_folder(mock_ocr, tmp_path):
    """Test batch processing of a folder."""
    mock_ocr.return_value = []

    # Create 2 test PDFs
    in_dir = tmp_path / "input"
    in_dir.mkdir()
    for name in ["a.pdf", "b.pdf"]:
        doc = fitz.open()
        doc.new_page()
        doc.save(str(in_dir / name))
        doc.close()

    out_dir = tmp_path / "output"
    pipeline = OcrPipeline(use_llm=False)
    results = pipeline.process_folder(in_dir, out_dir)

    assert len(results) == 2
    assert all(r.output_path.exists() for r in results)


@patch("ai_ocr.pipeline.extract_words_with_boxes")
def test_process_folder_empty(mock_ocr, tmp_path):
    """Test folder processing with no PDFs."""
    in_dir = tmp_path / "empty_input"
    in_dir.mkdir()
    out_dir = tmp_path / "output"

    pipeline = OcrPipeline(use_llm=False)
    results = pipeline.process_folder(in_dir, out_dir)

    assert results == []
