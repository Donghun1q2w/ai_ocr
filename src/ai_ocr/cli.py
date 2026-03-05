"""CLI entry point for Searchable PDF generation."""
import argparse
import sys
from pathlib import Path

from ai_ocr.config import load_config
from ai_ocr.llm_corrector import set_api_key
from ai_ocr.pipeline import OcrPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate searchable PDF from scanned PDF using OCR + LLM correction"
    )
    parser.add_argument("input", type=Path, help="Input PDF file or folder")
    parser.add_argument("output", type=Path, help="Output PDF file or folder")
    parser.add_argument("--lang", help="Tesseract language (default: from config.ini or kor+eng)")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM correction")
    parser.add_argument("--dpi", type=int, help="Render DPI (default: from config.ini or 300)")
    parser.add_argument("--min-confidence", type=float, help="Min OCR confidence (default: from config.ini or 30)")
    parser.add_argument("--debug-color", help="Show text layer in this color (e.g. red) for visual verification")
    parser.add_argument("--config", type=Path, help="Path to config.ini file")
    args = parser.parse_args()

    # Load config
    cfg = load_config(args.config)

    # CLI args override config.ini
    lang = args.lang or cfg.lang
    dpi = args.dpi or cfg.dpi
    min_confidence = args.min_confidence if args.min_confidence is not None else cfg.min_confidence
    debug_color = args.debug_color or cfg.debug_color or None

    # Set API key from config
    if cfg.gemini_api_key and not args.no_llm:
        set_api_key(cfg.gemini_api_key)

    pipeline = OcrPipeline(
        use_llm=not args.no_llm,
        lang=lang,
        dpi=dpi,
        min_confidence=min_confidence,
        debug_color=debug_color,
    )

    # Single file or folder mode
    if args.input.is_dir():
        if not args.input.exists():
            print(f"Error: Folder not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        results = pipeline.process_folder(args.input, args.output)
        total_pages = sum(r.total_pages for r in results)
        total_words = sum(r.total_words for r in results)
        print(f"\nCompleted: {len(results)} files, {total_pages} pages, {total_words} words")
    else:
        if not args.input.exists():
            print(f"Error: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        if not args.input.suffix.lower() == ".pdf":
            print(f"Error: Input must be a PDF file: {args.input}", file=sys.stderr)
            sys.exit(1)
        try:
            result = pipeline.process_pdf(args.input, args.output)
            print(f"\nCompleted: {result.total_pages} pages, {result.total_words} words, "
                  f"{result.corrected_words} corrected, {result.elapsed_seconds}s")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
