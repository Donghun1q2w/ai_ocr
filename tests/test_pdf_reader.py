from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from PIL import Image

from ai_ocr.pdf_reader import PageInfo, extract_page_images


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def two_page_pdf(tmp_path: Path) -> Path:
    """Programmatically generate a 2-page PDF with text on each page."""
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()

    for i in range(2):
        page = doc.new_page(width=595, height=842)  # A4 in points
        page.insert_text((72, 72), f"Page {i + 1} content", fontsize=12)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def single_page_pdf(tmp_path: Path) -> Path:
    """Single-page PDF for basic smoke tests."""
    pdf_path = tmp_path / "single.pdf"
    doc = fitz.open()
    page = doc.new_page(width=200, height=100)
    page.insert_text((10, 50), "Hello", fontsize=10)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_returns_correct_page_count(two_page_pdf: Path):
    results = extract_page_images(two_page_pdf)
    assert len(results) == 2


def test_returns_tuples_of_image_and_page_info(two_page_pdf: Path):
    results = extract_page_images(two_page_pdf)
    for img, info in results:
        assert isinstance(img, Image.Image)
        assert isinstance(info, PageInfo)


def test_image_dimensions_scale_with_dpi(single_page_pdf: Path):
    """Rendering at 2× DPI should produce an image ~2× wider and taller."""
    results_150 = extract_page_images(single_page_pdf, dpi=150)
    results_300 = extract_page_images(single_page_pdf, dpi=300)

    w150, h150 = results_150[0][0].size
    w300, h300 = results_300[0][0].size

    assert w300 == pytest.approx(w150 * 2, abs=2)
    assert h300 == pytest.approx(h150 * 2, abs=2)


def test_page_info_stores_render_dpi(two_page_pdf: Path):
    dpi = 150
    results = extract_page_images(two_page_pdf, dpi=dpi)
    for _, info in results:
        assert info.dpi == dpi


def test_page_info_stores_page_num(two_page_pdf: Path):
    results = extract_page_images(two_page_pdf)
    for expected_index, (_, info) in enumerate(results):
        assert info.page_num == expected_index


def test_page_info_dimensions_are_in_points(single_page_pdf: Path):
    """PageInfo width/height should match the page rect in PDF points (72 dpi)."""
    results = extract_page_images(single_page_pdf, dpi=300)
    _, info = results[0]
    # The fixture created a 200×100 pt page
    assert info.width_pt == pytest.approx(200.0)
    assert info.height_pt == pytest.approx(100.0)


def test_page_info_dimensions_for_a4(two_page_pdf: Path):
    """Both pages in the fixture are A4 (595×842 pt)."""
    results = extract_page_images(two_page_pdf)
    for _, info in results:
        assert info.width_pt == pytest.approx(595.0)
        assert info.height_pt == pytest.approx(842.0)


def test_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        extract_page_images("/nonexistent/path/file.pdf")


def test_empty_pdf_returns_empty_list(tmp_path: Path):
    """A PDF with zero pages should return an empty list."""
    # PyMuPDF refuses to save a zero-page doc, so write a minimal valid
    # zero-page PDF by hand and rely on fitz.open() tolerating it.
    pdf_path = tmp_path / "empty.pdf"
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
        b"startxref\n116\n%%EOF\n"
    )
    pdf_path.write_bytes(minimal_pdf)

    results = extract_page_images(pdf_path)
    assert results == []
