"""Tests for the pdf_writer module."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from ai_ocr.ocr_engine import OcrWord
from ai_ocr.pdf_writer import (
    _calculate_fontsize,
    _has_korean,
    _px_to_pt,
    add_text_layer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def blank_pdf(tmp_path: Path) -> Path:
    """Generate a 1-page blank white PDF (612x792 pt, US Letter)."""
    pdf_path = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_words() -> list[OcrWord]:
    """OcrWords at known pixel positions (dpi=72 so 1 px == 1 pt for easy math)."""
    return [
        OcrWord(
            text="hello",
            left=72,    # 72 px @ 72 dpi  => 72 pt
            top=144,    # 144 px @ 72 dpi => 144 pt
            width=50,
            height=14,
            confidence=90.0,
            line_num=1,
            block_num=1,
            page_num=0,
        ),
        OcrWord(
            text="world",
            left=130,
            top=144,
            width=55,
            height=14,
            confidence=88.0,
            line_num=1,
            block_num=1,
            page_num=0,
        ),
    ]


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

def test_px_to_pt_identity_at_72_dpi():
    assert _px_to_pt(100.0, 72) == pytest.approx(100.0)


def test_px_to_pt_halves_at_144_dpi():
    assert _px_to_pt(144.0, 144) == pytest.approx(72.0)


def test_px_to_pt_standard_300_dpi():
    assert _px_to_pt(300.0, 300) == pytest.approx(72.0)


def test_calculate_fontsize_scale():
    # 72 px height @ 72 dpi => 72 pt * 0.85 = 61.2
    assert _calculate_fontsize(72, 72) == pytest.approx(61.2)


def test_calculate_fontsize_300dpi():
    # 100 px @ 300 dpi => (100 * 72/300) * 0.85 = 24 * 0.85 = 20.4
    assert _calculate_fontsize(100, 300) == pytest.approx(20.4)


def test_has_korean_detects_hangul():
    assert _has_korean("안녕") is True


def test_has_korean_detects_jamo():
    assert _has_korean("\u3131") is True  # ㄱ (Hangul compatibility jamo)


def test_has_korean_false_for_ascii():
    assert _has_korean("hello") is False


def test_has_korean_mixed():
    assert _has_korean("hello 안녕") is True


# ---------------------------------------------------------------------------
# Integration tests for add_text_layer
# ---------------------------------------------------------------------------

def test_output_is_valid_pdf(blank_pdf: Path, sample_words: list[OcrWord], tmp_path: Path):
    out = tmp_path / "out.pdf"
    add_text_layer(blank_pdf, out, {0: sample_words}, dpi=72)

    assert out.exists()
    doc = fitz.open(str(out))
    assert len(doc) == 1
    doc.close()


def test_invisible_mode_text_is_searchable(blank_pdf: Path, sample_words: list[OcrWord], tmp_path: Path):
    """render_mode=3 text is invisible but still indexed and searchable."""
    out = tmp_path / "out_invisible.pdf"
    add_text_layer(blank_pdf, out, {0: sample_words}, dpi=72)

    doc = fitz.open(str(out))
    page = doc[0]
    results = page.search_for("hello")
    assert len(results) > 0, "Expected 'hello' to be searchable in invisible text layer"
    doc.close()


def test_debug_color_text_is_searchable(blank_pdf: Path, sample_words: list[OcrWord], tmp_path: Path):
    """debug_color mode should also produce searchable text."""
    out = tmp_path / "out_debug.pdf"
    add_text_layer(blank_pdf, out, {0: sample_words}, dpi=72, debug_color="red")

    doc = fitz.open(str(out))
    page = doc[0]
    results = page.search_for("world")
    assert len(results) > 0, "Expected 'world' to be searchable in debug text layer"
    doc.close()


def test_page_count_unchanged(blank_pdf: Path, sample_words: list[OcrWord], tmp_path: Path):
    """Source PDF page count must be preserved."""
    out = tmp_path / "out.pdf"
    add_text_layer(blank_pdf, out, {0: sample_words}, dpi=72)

    src_doc = fitz.open(str(blank_pdf))
    out_doc = fitz.open(str(out))
    assert len(out_doc) == len(src_doc)
    src_doc.close()
    out_doc.close()


def test_out_of_range_page_index_is_ignored(blank_pdf: Path, sample_words: list[OcrWord], tmp_path: Path):
    """Page index beyond doc length should not raise an exception."""
    out = tmp_path / "out.pdf"
    add_text_layer(blank_pdf, out, {99: sample_words}, dpi=72)
    assert out.exists()


def test_empty_words_list_produces_valid_pdf(blank_pdf: Path, tmp_path: Path):
    """Passing an empty word list should still write a valid PDF."""
    out = tmp_path / "out_empty.pdf"
    add_text_layer(blank_pdf, out, {0: []}, dpi=72)

    doc = fitz.open(str(out))
    assert len(doc) == 1
    doc.close()


def test_accepts_path_objects(blank_pdf: Path, sample_words: list[OcrWord], tmp_path: Path):
    """src_pdf and out_pdf may be Path objects."""
    out = tmp_path / "out_path.pdf"
    add_text_layer(Path(blank_pdf), Path(out), {0: sample_words}, dpi=72)
    assert out.exists()
