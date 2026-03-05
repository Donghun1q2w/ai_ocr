"""Searchable PDF pipeline: PDF → OCR → LLM correction → invisible text layer."""
from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from PIL import Image

from ai_ocr.ocr_engine import OcrWord, extract_words_with_boxes
from ai_ocr.llm_corrector import correct_ocr_text
from ai_ocr.pdf_reader import extract_page_images, PageInfo
from ai_ocr.pdf_writer import add_text_layer

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of processing a single PDF."""
    input_path: Path
    output_path: Path
    total_pages: int = 0
    total_words: int = 0
    corrected_words: int = 0
    elapsed_seconds: float = 0.0


class OcrPipeline:
    """Two-stage OCR pipeline: Tesseract + optional LLM correction → Searchable PDF."""

    def __init__(
        self,
        use_llm: bool = True,
        lang: str = "kor+eng",
        dpi: int = 300,
        min_confidence: float = 30,
        debug_color: Optional[str] = None,
    ):
        self.use_llm = use_llm
        self.lang = lang
        self.dpi = dpi
        self.min_confidence = min_confidence
        self.debug_color = debug_color

    def process_pdf(
        self,
        input_pdf: Union[str, Path],
        output_pdf: Union[str, Path],
    ) -> PipelineResult:
        """Process a single PDF: extract text via OCR and embed as invisible text layer."""
        input_pdf = Path(input_pdf)
        output_pdf = Path(output_pdf)
        start = time.time()

        # Extract page images
        page_data = extract_page_images(input_pdf, dpi=self.dpi)
        total_pages = len(page_data)

        # OCR each page
        pages_words: dict[int, list[OcrWord]] = {}
        total_words = 0
        corrected_count = 0

        for image, page_info in page_data:
            page_num = page_info.page_num
            _print_progress(page_num + 1, total_pages)

            # Stage 1: Tesseract OCR
            words = extract_words_with_boxes(
                image,
                lang=self.lang,
                min_confidence=self.min_confidence,
                page_num=page_num,
            )

            # Stage 2: LLM correction (optional)
            if self.use_llm and words:
                corrected = correct_ocr_text(words, lang=self.lang)
                for orig, corr in zip(words, corrected):
                    if orig.text != corr.text:
                        corrected_count += 1
                pages_words[page_num] = corrected
            else:
                pages_words[page_num] = words

            total_words += len(words)

            # Release image memory
            del image

        _print_progress_done(total_pages)

        # Write text layer to PDF
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        add_text_layer(
            src_pdf=input_pdf,
            out_pdf=output_pdf,
            pages_words=pages_words,
            dpi=self.dpi,
            debug_color=self.debug_color,
        )

        elapsed = time.time() - start
        return PipelineResult(
            input_path=input_pdf,
            output_path=output_pdf,
            total_pages=total_pages,
            total_words=total_words,
            corrected_words=corrected_count,
            elapsed_seconds=round(elapsed, 2),
        )

    def process_folder(
        self,
        input_dir: Union[str, Path],
        output_dir: Union[str, Path],
    ) -> list[PipelineResult]:
        """Process all PDF files in a folder."""
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        pdf_files = sorted(input_dir.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found in %s", input_dir)
            return []

        results = []
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] {pdf_file.name}")
            out_path = output_dir / pdf_file.name
            result = self.process_pdf(pdf_file, out_path)
            results.append(result)
            print(f"  Done: {result.total_pages} pages, {result.total_words} words, "
                  f"{result.elapsed_seconds}s")

        return results


def _print_progress(current: int, total: int) -> None:
    """Print page processing progress."""
    sys.stdout.write(f"\r  Page {current}/{total} ...")
    sys.stdout.flush()


def _print_progress_done(total: int) -> None:
    """Print completion message."""
    sys.stdout.write(f"\r  Page {total}/{total} ... done\n")
    sys.stdout.flush()
