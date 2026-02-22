from dataclasses import dataclass

import pytesseract
from PIL import Image


@dataclass
class OcrWord:
    """A single word extracted by OCR with its bounding box."""
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float
    line_num: int
    block_num: int


def extract_text(image: Image.Image, lang: str = "eng") -> str:
    """Extract plain text from an image using Tesseract."""
    return pytesseract.image_to_string(image, lang=lang).strip()


def extract_words_with_boxes(
    image: Image.Image,
    lang: str = "eng",
    min_confidence: float = 0,
) -> list[OcrWord]:
    """Extract words with bounding box positions from an image.

    Returns a list of OcrWord with text, position, and confidence.
    Words with confidence below min_confidence are filtered out.
    """
    data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)

    words = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])

        if not text or conf == -1 or conf < min_confidence:
            continue

        words.append(OcrWord(
            text=text,
            left=data["left"][i],
            top=data["top"][i],
            width=data["width"][i],
            height=data["height"][i],
            confidence=conf,
            line_num=data["line_num"][i],
            block_num=data["block_num"][i],
        ))

    return words
