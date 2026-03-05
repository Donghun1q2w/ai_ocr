# OCR with LLM Correction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a two-stage OCR pipeline that uses Tesseract for initial text extraction (with bounding boxes) and Gemini 3 Flash to correct misrecognized text using contextual understanding.

**Architecture:** Stage 1 extracts text and positional data (bounding boxes) via Tesseract OCR. Stage 2 sends the raw OCR text to Gemini 3 Flash, which corrects misrecognized words using contextual understanding. The corrected text is then mapped back to the original bounding box positions, solving both accuracy and positioning problems.

**Tech Stack:** Python 3.9+, pytesseract, Pillow, google-genai (new SDK), Tesseract OCR, pytest

---

## Project Structure

```
ai_ocr/
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/
│   └── ai_ocr/
│       ├── __init__.py
│       ├── ocr_engine.py       # Tesseract OCR wrapper
│       ├── llm_corrector.py    # Gemini LLM text correction
│       └── pipeline.py         # Two-stage pipeline
├── tests/
│   ├── conftest.py
│   ├── test_ocr_engine.py
│   ├── test_llm_corrector.py
│   └── test_pipeline.py
└── samples/                    # Sample test images
```

---

### Task 1: Project Setup & Dependencies

**Files:**
- Create: `ai_ocr/pyproject.toml`
- Create: `ai_ocr/.gitignore`
- Create: `ai_ocr/.env.example`
- Create: `ai_ocr/src/ai_ocr/__init__.py`

**Step 1: Install Tesseract system dependency**

Run: `brew install tesseract`
Expected: Tesseract installed, `tesseract --version` works

**Step 2: Create pyproject.toml**

```toml
[project]
name = "ai-ocr"
version = "0.1.0"
description = "Two-stage OCR: Tesseract + Gemini LLM correction"
requires-python = ">=3.9"
dependencies = [
    "pytesseract>=0.3.10",
    "Pillow>=10.0.0",
    "google-genai>=1.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.12.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.venv/
.pytest_cache/
```

**Step 4: Create .env.example**

```
GEMINI_API_KEY=your-api-key-here
```

**Step 5: Create __init__.py**

```python
"""ai_ocr - Two-stage OCR with LLM correction."""
```

**Step 6: Install dependencies**

Run: `cd ai_ocr && pip install -e ".[dev]"`
Expected: All packages install successfully

**Step 7: Verify Tesseract is accessible from Python**

Run: `cd ai_ocr && python -c "import pytesseract; print(pytesseract.get_tesseract_version())"`
Expected: Prints tesseract version number

**Step 8: Commit**

```bash
cd ai_ocr
git add pyproject.toml .gitignore .env.example src/ai_ocr/__init__.py
git commit -m "chore: initial project setup with dependencies"
```

---

### Task 2: OCR Engine - Tesseract Wrapper

**Files:**
- Create: `ai_ocr/tests/conftest.py`
- Create: `ai_ocr/tests/test_ocr_engine.py`
- Create: `ai_ocr/src/ai_ocr/ocr_engine.py`

**Step 1: Create a simple test image for conftest**

```python
# tests/conftest.py
import pytest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


@pytest.fixture
def sample_image_path(tmp_path: Path) -> Path:
    """Create a simple image with known text for testing."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "Hello World", fill="black")
    path = tmp_path / "test_image.png"
    img.save(path)
    return path


@pytest.fixture
def sample_image(sample_image_path: Path) -> Image.Image:
    return Image.open(sample_image_path)
```

**Step 2: Write failing tests for OCR engine**

```python
# tests/test_ocr_engine.py
from pathlib import Path
from PIL import Image

from ai_ocr.ocr_engine import extract_text, extract_words_with_boxes, OcrWord


def test_extract_text_returns_string(sample_image: Image.Image):
    result = extract_text(sample_image)
    assert isinstance(result, str)
    assert len(result) > 0


def test_extract_words_with_boxes_returns_list(sample_image: Image.Image):
    words = extract_words_with_boxes(sample_image)
    assert isinstance(words, list)
    assert len(words) > 0


def test_ocr_word_has_required_fields(sample_image: Image.Image):
    words = extract_words_with_boxes(sample_image)
    word = words[0]
    assert isinstance(word, OcrWord)
    assert isinstance(word.text, str)
    assert isinstance(word.left, int)
    assert isinstance(word.top, int)
    assert isinstance(word.width, int)
    assert isinstance(word.height, int)
    assert isinstance(word.confidence, float)


def test_extract_words_with_boxes_filters_low_confidence(sample_image: Image.Image):
    words = extract_words_with_boxes(sample_image, min_confidence=0)
    all_words = extract_words_with_boxes(sample_image, min_confidence=-1)
    assert len(words) <= len(all_words)
```

**Step 3: Run tests to verify they fail**

Run: `cd ai_ocr && python -m pytest tests/test_ocr_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_ocr.ocr_engine'`

**Step 4: Implement OCR engine**

```python
# src/ai_ocr/ocr_engine.py
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

        if not text or conf < min_confidence:
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
```

**Step 5: Run tests to verify they pass**

Run: `cd ai_ocr && python -m pytest tests/test_ocr_engine.py -v`
Expected: All 4 tests PASS

**Step 6: Commit**

```bash
cd ai_ocr
git add tests/conftest.py tests/test_ocr_engine.py src/ai_ocr/ocr_engine.py
git commit -m "feat: add Tesseract OCR engine with bounding box extraction"
```

---

### Task 3: LLM Corrector - Gemini Integration

**Files:**
- Create: `ai_ocr/tests/test_llm_corrector.py`
- Create: `ai_ocr/src/ai_ocr/llm_corrector.py`

**Step 1: Write failing tests for LLM corrector (mocked)**

```python
# tests/test_llm_corrector.py
import json
import pytest
from unittest.mock import MagicMock, patch

from ai_ocr.llm_corrector import correct_ocr_text, build_correction_prompt
from ai_ocr.ocr_engine import OcrWord


@pytest.fixture
def sample_ocr_words() -> list[OcrWord]:
    return [
        OcrWord(text="Helo", left=10, top=30, width=50, height=20, confidence=72.0, line_num=1, block_num=1),
        OcrWord(text="Wrld", left=70, top=30, width=50, height=20, confidence=65.0, line_num=1, block_num=1),
        OcrWord(text="Test", left=10, top=60, width=50, height=20, confidence=95.0, line_num=2, block_num=1),
    ]


def test_build_correction_prompt_contains_words(sample_ocr_words):
    prompt = build_correction_prompt(sample_ocr_words)
    assert "Helo" in prompt
    assert "Wrld" in prompt
    assert "Test" in prompt


def test_build_correction_prompt_contains_confidence(sample_ocr_words):
    prompt = build_correction_prompt(sample_ocr_words)
    assert "72.0" in prompt or "72" in prompt


@patch("ai_ocr.llm_corrector._call_gemini")
def test_correct_ocr_text_returns_corrected_words(mock_gemini, sample_ocr_words):
    mock_gemini.return_value = json.dumps([
        {"index": 0, "original": "Helo", "corrected": "Hello"},
        {"index": 1, "original": "Wrld", "corrected": "World"},
    ])
    result = correct_ocr_text(sample_ocr_words)
    assert result[0].text == "Hello"
    assert result[1].text == "World"
    assert result[2].text == "Test"  # unchanged


@patch("ai_ocr.llm_corrector._call_gemini")
def test_correct_ocr_text_preserves_positions(mock_gemini, sample_ocr_words):
    mock_gemini.return_value = json.dumps([
        {"index": 0, "original": "Helo", "corrected": "Hello"},
    ])
    result = correct_ocr_text(sample_ocr_words)
    assert result[0].left == 10
    assert result[0].top == 30
    assert result[0].width == 50
    assert result[0].height == 20


@patch("ai_ocr.llm_corrector._call_gemini")
def test_correct_ocr_text_handles_empty_response(mock_gemini, sample_ocr_words):
    mock_gemini.return_value = "[]"
    result = correct_ocr_text(sample_ocr_words)
    assert result[0].text == "Helo"  # unchanged
    assert result[1].text == "Wrld"  # unchanged


@patch("ai_ocr.llm_corrector._call_gemini")
def test_correct_ocr_text_handles_malformed_response(mock_gemini, sample_ocr_words):
    mock_gemini.return_value = "not valid json"
    result = correct_ocr_text(sample_ocr_words)
    # Should return original words unchanged on error
    assert result[0].text == "Helo"
    assert result[1].text == "Wrld"
```

**Step 2: Run tests to verify they fail**

Run: `cd ai_ocr && python -m pytest tests/test_llm_corrector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_ocr.llm_corrector'`

**Step 3: Implement LLM corrector**

```python
# src/ai_ocr/llm_corrector.py
import copy
import json
import os

from google import genai
from google.genai import types

from ai_ocr.ocr_engine import OcrWord

_GEMINI_MODEL = "gemini-3-flash-preview"


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    return genai.Client(api_key=api_key)


def build_correction_prompt(words: list[OcrWord]) -> str:
    """Build a prompt asking the LLM to correct OCR errors."""
    word_list = ""
    for i, w in enumerate(words):
        word_list += f"  {i}: \"{w.text}\" (confidence: {w.confidence}, line: {w.line_num})\n"

    return f"""You are an OCR post-processing assistant.
Below is a list of words extracted by Tesseract OCR, with their index, confidence score, and line number.
Some words may be misrecognized. Use context from surrounding words (especially on the same line) to correct errors.

Words:
{word_list}
Respond ONLY with a JSON array of corrections. Each correction is an object with:
- "index": the word index
- "original": the original OCR text
- "corrected": the corrected text

Only include words that need correction. If all words are correct, respond with [].

Example response:
[{{"index": 0, "original": "Helo", "corrected": "Hello"}}]

JSON:"""


def _call_gemini(prompt: str) -> str:
    """Call Gemini API and return the response text."""
    client = _get_client()
    response = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
        ),
    )
    return response.text


def _parse_corrections(response_text: str) -> list[dict]:
    """Parse the JSON corrections from Gemini's response."""
    text = response_text.strip()
    # Handle markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return json.loads(text)


def correct_ocr_text(words: list[OcrWord]) -> list[OcrWord]:
    """Send OCR words to Gemini for contextual correction.

    Returns a new list of OcrWord with corrected text.
    Bounding box positions are preserved from the original.
    """
    if not words:
        return []

    prompt = build_correction_prompt(words)

    try:
        response_text = _call_gemini(prompt)
        corrections = _parse_corrections(response_text)
    except (json.JSONDecodeError, ValueError, Exception):
        # On any error, return words unchanged
        return [copy.copy(w) for w in words]

    result = [copy.copy(w) for w in words]

    for correction in corrections:
        idx = correction.get("index")
        corrected = correction.get("corrected")
        if idx is not None and corrected and 0 <= idx < len(result):
            result[idx].text = corrected

    return result
```

**Step 4: Run tests to verify they pass**

Run: `cd ai_ocr && python -m pytest tests/test_llm_corrector.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
cd ai_ocr
git add tests/test_llm_corrector.py src/ai_ocr/llm_corrector.py
git commit -m "feat: add Gemini LLM corrector for OCR text post-processing"
```

---

### Task 4: Pipeline - Combine OCR + LLM Correction

**Files:**
- Create: `ai_ocr/tests/test_pipeline.py`
- Create: `ai_ocr/src/ai_ocr/pipeline.py`

**Step 1: Write failing tests for pipeline**

```python
# tests/test_pipeline.py
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

from PIL import Image

from ai_ocr.pipeline import OcrPipeline, OcrResult


def test_pipeline_ocr_only(sample_image: Image.Image):
    """Test pipeline with only Tesseract (no LLM correction)."""
    pipeline = OcrPipeline(use_llm=False)
    result = pipeline.run(sample_image)
    assert isinstance(result, OcrResult)
    assert isinstance(result.raw_text, str)
    assert len(result.words) > 0


def test_pipeline_result_has_raw_and_corrected(sample_image: Image.Image):
    """Test that OcrResult contains both raw and corrected text."""
    pipeline = OcrPipeline(use_llm=False)
    result = pipeline.run(sample_image)
    assert result.raw_text == result.corrected_text  # no LLM = same


@patch("ai_ocr.pipeline.correct_ocr_text")
def test_pipeline_with_llm(mock_correct, sample_image: Image.Image):
    """Test pipeline calls LLM correction when enabled."""
    mock_correct.side_effect = lambda words: words  # pass through
    pipeline = OcrPipeline(use_llm=True)
    result = pipeline.run(sample_image)
    mock_correct.assert_called_once()
    assert isinstance(result, OcrResult)


def test_pipeline_from_file(sample_image_path: Path):
    """Test pipeline can load image from file path."""
    pipeline = OcrPipeline(use_llm=False)
    result = pipeline.run_from_file(sample_image_path)
    assert isinstance(result, OcrResult)
    assert len(result.words) > 0
```

**Step 2: Run tests to verify they fail**

Run: `cd ai_ocr && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_ocr.pipeline'`

**Step 3: Implement pipeline**

```python
# src/ai_ocr/pipeline.py
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from ai_ocr.ocr_engine import OcrWord, extract_text, extract_words_with_boxes
from ai_ocr.llm_corrector import correct_ocr_text


@dataclass
class OcrResult:
    """Result of the OCR pipeline."""
    raw_text: str
    corrected_text: str
    words: list[OcrWord]
    corrected_words: list[OcrWord] = field(default_factory=list)


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

    def run_from_file(self, image_path: str | Path) -> OcrResult:
        """Run OCR pipeline on an image file."""
        image = Image.open(image_path)
        return self.run(image)


def _words_to_text(words: list[OcrWord]) -> str:
    """Reconstruct text from words, grouping by line."""
    if not words:
        return ""

    lines: dict[tuple[int, int], list[OcrWord]] = {}
    for w in words:
        key = (w.block_num, w.line_num)
        lines.setdefault(key, []).append(w)

    result_lines = []
    for key in sorted(lines.keys()):
        line_words = sorted(lines[key], key=lambda w: w.left)
        result_lines.append(" ".join(w.text for w in line_words))

    return "\n".join(result_lines)
```

**Step 4: Run tests to verify they pass**

Run: `cd ai_ocr && python -m pytest tests/test_pipeline.py -v`
Expected: All 4 tests PASS

**Step 5: Run all tests together**

Run: `cd ai_ocr && python -m pytest tests/ -v`
Expected: All 14 tests PASS

**Step 6: Commit**

```bash
cd ai_ocr
git add tests/test_pipeline.py src/ai_ocr/pipeline.py
git commit -m "feat: add two-stage OCR pipeline combining Tesseract and LLM"
```

---

### Task 5: CLI Entry Point

**Files:**
- Create: `ai_ocr/src/ai_ocr/cli.py`

**Step 1: Implement CLI**

```python
# src/ai_ocr/cli.py
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from ai_ocr.pipeline import OcrPipeline


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="OCR with LLM correction")
    parser.add_argument("image", type=Path, help="Path to image file")
    parser.add_argument("--lang", default="eng", help="Tesseract language (default: eng)")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM correction")
    parser.add_argument("--min-confidence", type=float, default=0, help="Min OCR confidence (0-100)")
    parser.add_argument("--show-boxes", action="store_true", help="Show word bounding boxes")
    args = parser.parse_args()

    if not args.image.exists():
        print(f"Error: File not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    pipeline = OcrPipeline(
        use_llm=not args.no_llm,
        lang=args.lang,
        min_confidence=args.min_confidence,
    )

    result = pipeline.run_from_file(args.image)

    if args.no_llm:
        print(result.raw_text)
    else:
        print(result.corrected_text)

    if args.show_boxes:
        print("\n--- Word Bounding Boxes ---")
        words = result.corrected_words if not args.no_llm else result.words
        for w in words:
            print(f"  [{w.text}] at ({w.left}, {w.top}) size {w.width}x{w.height} conf={w.confidence:.1f}")


if __name__ == "__main__":
    main()
```

**Step 2: Add CLI entry point to pyproject.toml**

Add the following `[project.scripts]` section to `pyproject.toml`:

```toml
[project.scripts]
ai-ocr = "ai_ocr.cli:main"
```

**Step 3: Re-install to register CLI**

Run: `cd ai_ocr && pip install -e ".[dev]"`
Expected: Successfully installed

**Step 4: Test CLI with --no-llm**

Run: `cd ai_ocr && python -m ai_ocr.cli --no-llm --show-boxes tests/fixtures/test.png` (or use any test image)
Expected: Prints extracted text and bounding boxes

**Step 5: Commit**

```bash
cd ai_ocr
git add src/ai_ocr/cli.py pyproject.toml
git commit -m "feat: add CLI entry point for OCR pipeline"
```

---

### Task 6: Korean Language Support

**Files:**
- Modify: `ai_ocr/src/ai_ocr/llm_corrector.py`
- Create: `ai_ocr/tests/test_korean.py`

**Step 1: Install Korean language data for Tesseract**

Run: `brew install tesseract-lang`
Expected: Korean (`kor`) language pack installed

**Step 2: Write test for Korean support**

```python
# tests/test_korean.py
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import pytest

from ai_ocr.ocr_engine import extract_text, extract_words_with_boxes


@pytest.fixture
def korean_image(tmp_path: Path) -> Image.Image:
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    # Use default font - may not render Korean perfectly, but tests the flow
    draw.text((10, 30), "테스트 문서", fill="black")
    path = tmp_path / "korean.png"
    img.save(path)
    return Image.open(path)


def test_extract_text_korean(korean_image: Image.Image):
    result = extract_text(korean_image, lang="kor")
    assert isinstance(result, str)


def test_extract_words_korean(korean_image: Image.Image):
    words = extract_words_with_boxes(korean_image, lang="kor")
    assert isinstance(words, list)
```

**Step 3: Run tests**

Run: `cd ai_ocr && python -m pytest tests/test_korean.py -v`
Expected: PASS

**Step 4: Update correction prompt to handle Korean**

In `llm_corrector.py`, update `build_correction_prompt` to add language awareness:

```python
def build_correction_prompt(words: list[OcrWord], lang: str = "eng") -> str:
    """Build a prompt asking the LLM to correct OCR errors."""
    word_list = ""
    for i, w in enumerate(words):
        word_list += f"  {i}: \"{w.text}\" (confidence: {w.confidence}, line: {w.line_num})\n"

    lang_instruction = ""
    if lang == "kor":
        lang_instruction = "The text is in Korean. Apply Korean grammar and context for corrections.\n"
    elif lang == "kor+eng":
        lang_instruction = "The text contains both Korean and English. Apply appropriate grammar for each language.\n"

    return f"""You are an OCR post-processing assistant.
Below is a list of words extracted by Tesseract OCR, with their index, confidence score, and line number.
Some words may be misrecognized. Use context from surrounding words (especially on the same line) to correct errors.
{lang_instruction}
Words:
{word_list}
Respond ONLY with a JSON array of corrections. Each correction is an object with:
- "index": the word index
- "original": the original OCR text
- "corrected": the corrected text

Only include words that need correction. If all words are correct, respond with [].

JSON:"""
```

Also update `correct_ocr_text` to accept `lang`:

```python
def correct_ocr_text(words: list[OcrWord], lang: str = "eng") -> list[OcrWord]:
    """Send OCR words to Gemini for contextual correction."""
    if not words:
        return []

    prompt = build_correction_prompt(words, lang=lang)
    # ... rest unchanged
```

**Step 5: Update pipeline to pass lang to corrector**

In `pipeline.py`, update the `run` method:

```python
corrected_words = correct_ocr_text(words, lang=self.lang)
```

**Step 6: Run all tests**

Run: `cd ai_ocr && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
cd ai_ocr
git add tests/test_korean.py src/ai_ocr/llm_corrector.py src/ai_ocr/pipeline.py
git commit -m "feat: add Korean language support for OCR and LLM correction"
```

---

### Task 7: Integration Test with Real Gemini API

**Files:**
- Create: `ai_ocr/tests/test_integration.py`

**Step 1: Write integration test (skipped without API key)**

```python
# tests/test_integration.py
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
```

**Step 2: Run integration test**

Run: `cd ai_ocr && GEMINI_API_KEY=your-key python -m pytest tests/test_integration.py -v`
Expected: PASS (or SKIPPED if no API key)

**Step 3: Run full test suite**

Run: `cd ai_ocr && python -m pytest tests/ -v`
Expected: All tests PASS (integration test skipped if no key)

**Step 4: Commit**

```bash
cd ai_ocr
git add tests/test_integration.py
git commit -m "test: add integration test for full pipeline with Gemini API"
```

---

### Task 8: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md with project details**

Replace the CLAUDE.md content with accurate build/test/run commands and architecture info now that the project is built.

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with project architecture and commands"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | Project setup & dependencies | - |
| 2 | OCR Engine (Tesseract wrapper) | 4 |
| 3 | LLM Corrector (Gemini integration) | 6 |
| 4 | Pipeline (combine both stages) | 4 |
| 5 | CLI entry point | manual |
| 6 | Korean language support | 2 |
| 7 | Integration test | 1 |
| 8 | Update CLAUDE.md | - |

**Total: 17 automated tests + manual CLI verification**
