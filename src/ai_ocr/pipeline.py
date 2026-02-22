from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from PIL import Image

from ai_ocr.ocr_engine import OcrWord, extract_text, extract_words_with_boxes
from ai_ocr.llm_corrector import correct_ocr_text


@dataclass
class OcrResult:
    """Result of the OCR pipeline."""
    raw_text: str
    corrected_text: str
    words: list
    corrected_words: list = field(default_factory=list)


class OcrPipeline:
    """Two-stage OCR pipeline: Tesseract + optional LLM correction."""

    def __init__(
        self,
        use_llm: bool = True,
        lang: str = "eng",
        min_confidence: float = 0,
    ):
        self.use_llm = use_llm
        self.lang = lang
        self.min_confidence = min_confidence

    def run(self, image: Image.Image) -> OcrResult:
        """Run OCR pipeline on a PIL Image."""
        # Stage 1: Tesseract OCR
        raw_text = extract_text(image, lang=self.lang)
        words = extract_words_with_boxes(
            image, lang=self.lang, min_confidence=self.min_confidence
        )

        # Stage 2: LLM correction (optional)
        if self.use_llm and words:
            corrected_words = correct_ocr_text(words)
            corrected_text = _words_to_text(corrected_words)
        else:
            corrected_words = list(words)
            corrected_text = raw_text

        return OcrResult(
            raw_text=raw_text,
            corrected_text=corrected_text,
            words=words,
            corrected_words=corrected_words,
        )

    def run_from_file(self, image_path: Union[str, Path]) -> OcrResult:
        """Run OCR pipeline on an image file."""
        image = Image.open(image_path)
        return self.run(image)


def _words_to_text(words: list) -> str:
    """Reconstruct text from words, grouping by line."""
    if not words:
        return ""

    lines: dict = {}
    for w in words:
        key = (w.block_num, w.line_num)
        lines.setdefault(key, []).append(w)

    result_lines = []
    for key in sorted(lines.keys()):
        line_words = sorted(lines[key], key=lambda w: w.left)
        result_lines.append(" ".join(w.text for w in line_words))

    return "\n".join(result_lines)
