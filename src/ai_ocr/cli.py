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
