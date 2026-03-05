"""PDF text layer writer — adds invisible/debug text overlay to PDF pages."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import fitz  # PyMuPDF

from ai_ocr.ocr_engine import OcrWord


def _px_to_pt(px_value: float, dpi: int) -> float:
    """Convert pixels to PDF points."""
    return px_value * 72.0 / dpi


def _calculate_fontsize(bbox_height_px: int, dpi: int) -> float:
    """Calculate font size from bounding box height in pixels."""
    return bbox_height_px * 72.0 / dpi * 0.85


def _has_korean(text: str) -> bool:
    """Return True if text contains Korean characters."""
    return any('\uAC00' <= c <= '\uD7A3' or '\u3130' <= c <= '\u318F' for c in text)


def add_text_layer(
    src_pdf: Union[str, Path],
    out_pdf: Union[str, Path],
    pages_words: dict[int, list[OcrWord]],
    dpi: int = 300,
    debug_color: Optional[str] = None,
) -> None:
    """Add an invisible (or debug-visible) text layer to each PDF page.

    Args:
        src_pdf: Path to the source PDF file.
        out_pdf: Path for the output PDF file.
        pages_words: Mapping of 0-based page index to list of OcrWord objects.
        dpi: Resolution used when OCR was performed (pixels per inch).
        debug_color: If None, use render_mode=3 (invisible). If a color name
            such as "red", render the text visibly in that color.
    """
    doc = fitz.open(str(src_pdf))

    for page_index, words in pages_words.items():
        if page_index >= len(doc):
            continue

        page = doc[page_index]

        for word in words:
            x_pt = _px_to_pt(word.left, dpi)
            y_pt = _px_to_pt(word.top, dpi)
            fontsize = _calculate_fontsize(word.height, dpi)

            if fontsize <= 0:
                fontsize = 1.0

            fontname = "ko" if _has_korean(word.text) else "helv"

            if debug_color is None:
                page.insert_text(
                    fitz.Point(x_pt, y_pt),
                    word.text,
                    fontsize=fontsize,
                    fontname=fontname,
                    render_mode=3,
                )
            else:
                # Resolve color: try fitz.pdfcolor dict, fall back to red
                color = fitz.pdfcolor.get(debug_color, (1, 0, 0))
                page.insert_text(
                    fitz.Point(x_pt, y_pt),
                    word.text,
                    fontsize=fontsize,
                    fontname=fontname,
                    render_mode=0,
                    color=color,
                )

    doc.save(str(out_pdf))
    doc.close()
