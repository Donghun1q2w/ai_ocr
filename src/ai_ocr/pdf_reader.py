"""PDF page extraction module — converts PDF pages to PIL Images."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

import fitz  # PyMuPDF
from PIL import Image


@dataclass
class PageInfo:
    """Metadata for a single rendered PDF page."""
    width_pt: float
    height_pt: float
    dpi: int
    page_num: int


def extract_page_images(
    pdf_path: Union[str, Path],
    dpi: int = 300,
) -> list[tuple[Image.Image, PageInfo]]:
    """Render each page of a PDF as a PIL Image.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Resolution to render at (default 300).

    Returns:
        List of (PIL Image, PageInfo) tuples, one per page.

    Raises:
        FileNotFoundError: If pdf_path does not exist.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    results: list[tuple[Image.Image, PageInfo]] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        info = PageInfo(
            width_pt=page.rect.width,
            height_pt=page.rect.height,
            dpi=dpi,
            page_num=page_index,
        )
        results.append((image, info))

    doc.close()
    return results
