from __future__ import annotations

import copy
import json
import logging
import os
import re

from google import genai
from google.genai import types

from ai_ocr.ocr_engine import OcrWord

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-3-flash-preview"


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    return genai.Client(api_key=api_key)


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
    if response.text is None:
        raise ValueError("Gemini returned empty response")
    return response.text


def _parse_corrections(response_text: str) -> list[dict]:
    """Parse the JSON corrections from Gemini's response."""
    text = response_text.strip()
    # Handle markdown code blocks
    match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1)
    result = json.loads(text)
    if not isinstance(result, list):
        raise ValueError(f"Expected JSON array, got {type(result).__name__}")
    return result


def correct_ocr_text(words: list[OcrWord], lang: str = "eng") -> list[OcrWord]:
    """Send OCR words to Gemini for contextual correction.

    Returns a new list of OcrWord with corrected text.
    Bounding box positions are preserved from the original.
    """
    if not words:
        return []

    prompt = build_correction_prompt(words, lang=lang)

    try:
        response_text = _call_gemini(prompt)
        corrections = _parse_corrections(response_text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("LLM correction failed (parse): %s", e)
        return [copy.copy(w) for w in words]
    except Exception as e:
        logger.warning("LLM correction failed (API): %s", e)
        return [copy.copy(w) for w in words]

    result = [copy.copy(w) for w in words]

    for correction in corrections:
        idx = correction.get("index")
        corrected = correction.get("corrected")
        if idx is not None and corrected and 0 <= idx < len(result):
            result[idx].text = corrected

    return result
