"""Integration tests for the full PDF pipeline (no API key needed — uses mocks)."""
import pytest
from pathlib import Path
from unittest.mock import patch

import fitz

from ai_ocr.pipeline import OcrPipeline, PipelineResult
from ai_ocr.ocr_engine import OcrWord


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """Create a 3-page PDF with known text rendered as images (rasterized)."""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=612, height=792)
        page.insert_text(fitz.Point(72, 100), f"Page {i+1} sample text for OCR", fontsize=16)
        page.insert_text(fitz.Point(72, 130), "The quick brown fox jumps over the lazy dog", fontsize=12)
    pdf_path = tmp_path / "test_doc.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@patch("ai_ocr.pipeline.extract_words_with_boxes")
def test_full_pipeline_no_llm(mock_ocr, text_pdf, tmp_path):
    """End-to-end: PDF → OCR (mocked) → output PDF with text layer."""
    mock_ocr.return_value = [
        OcrWord(text="Sample", left=100, top=130, width=120, height=35,
                confidence=92.0, line_num=1, block_num=1, page_num=0),
        OcrWord(text="text", left=250, top=130, width=80, height=35,
                confidence=88.0, line_num=1, block_num=1, page_num=0),
    ]

    out_pdf = tmp_path / "output.pdf"
    pipeline = OcrPipeline(use_llm=False)
    result = pipeline.process_pdf(text_pdf, out_pdf)

    assert result.total_pages == 3
    assert result.total_words == 6  # 2 words × 3 pages
    assert out_pdf.exists()

    # Verify text is searchable in output
    doc = fitz.open(str(out_pdf))
    found = doc[0].search_for("Sample")
    assert len(found) > 0
    doc.close()


@patch("ai_ocr.pipeline.extract_words_with_boxes")
def test_debug_color_mode(mock_ocr, text_pdf, tmp_path):
    """Test debug color mode produces visible text."""
    mock_ocr.return_value = [
        OcrWord(text="Debug", left=100, top=100, width=100, height=30,
                confidence=95.0, line_num=1, block_num=1, page_num=0),
    ]

    out_pdf = tmp_path / "debug_output.pdf"
    pipeline = OcrPipeline(use_llm=False, debug_color="red")
    result = pipeline.process_pdf(text_pdf, out_pdf)

    assert out_pdf.exists()
    doc = fitz.open(str(out_pdf))
    found = doc[0].search_for("Debug")
    assert len(found) > 0
    doc.close()


@patch("ai_ocr.pipeline.extract_words_with_boxes")
def test_folder_batch_processing(mock_ocr, tmp_path):
    """Test batch processing of multiple PDFs."""
    mock_ocr.return_value = [
        OcrWord(text="Batch", left=50, top=50, width=80, height=25,
                confidence=90.0, line_num=1, block_num=1, page_num=0),
    ]

    in_dir = tmp_path / "batch_in"
    in_dir.mkdir()
    for name in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
        doc = fitz.open()
        doc.new_page()
        doc.save(str(in_dir / name))
        doc.close()

    out_dir = tmp_path / "batch_out"
    pipeline = OcrPipeline(use_llm=False)
    results = pipeline.process_folder(in_dir, out_dir)

    assert len(results) == 3
    assert all(r.output_path.exists() for r in results)
    assert all(isinstance(r, PipelineResult) for r in results)


@patch("ai_ocr.pipeline.extract_words_with_boxes")
def test_output_preserves_page_count(mock_ocr, text_pdf, tmp_path):
    """Output PDF must have same number of pages as input."""
    mock_ocr.return_value = []

    out_pdf = tmp_path / "same_pages.pdf"
    pipeline = OcrPipeline(use_llm=False)
    pipeline.process_pdf(text_pdf, out_pdf)

    in_doc = fitz.open(str(text_pdf))
    out_doc = fitz.open(str(out_pdf))
    assert len(out_doc) == len(in_doc)
    in_doc.close()
    out_doc.close()
