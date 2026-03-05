# Revision: Searchable PDF 파이프라인 전면 재구축

**Date:** 2026-03-05 23:15
**Commit:** 1e4d457

## Summary

스캔된 PDF → Searchable PDF 생성 파이프라인으로 전면 재구축. Tesseract OCR + Gemini LLM 보정 + PyMuPDF 투명 텍스트 레이어.

## Rationale / Plan

- 기존: 단일 이미지 → 텍스트 반환 목적
- 신규: 스캔 PDF(100+ 페이지, 한/영/수식) → Adobe Acrobat OCR과 동등한 Searchable PDF 생성
- 계획: `docs/plans/2026-03-05_225500_searchable-pdf-rebuild.md` 참조

## Changed Files

| File | Status | Description |
|------|--------|-------------|
| `pyproject.toml` | Modified | PyMuPDF 의존성 추가, 버전 0.2.0, python-dotenv 제거 |
| `src/ai_ocr/__init__.py` | Modified | 프로젝트 설명 업데이트 |
| `src/ai_ocr/pdf_reader.py` | Added | PDF → PIL Image 변환 모듈 (PageInfo dataclass) |
| `src/ai_ocr/pdf_writer.py` | Added | 투명 텍스트 레이어 생성 모듈 (render_mode=3) |
| `src/ai_ocr/config.py` | Added | config.ini 기반 설정 관리 (AppConfig dataclass) |
| `src/ai_ocr/ocr_engine.py` | Modified | OcrWord에 page_num 필드 추가 |
| `src/ai_ocr/llm_corrector.py` | Modified | 타입 검증 강화, 클라이언트 캐싱, 예외 범위 축소 |
| `src/ai_ocr/pipeline.py` | Rewritten | process_pdf/process_folder 메서드, 페이지별 처리 |
| `src/ai_ocr/cli.py` | Rewritten | 단일 파일 + 폴더 일괄 처리, config.ini 연동 |
| `build.spec` | Added | PyInstaller Windows exe 빌드 설정 |
| `config.ini.example` | Added | 설정 파일 템플릿 |
| `tests/test_pdf_reader.py` | Added | PDF Reader 테스트 (8 tests) |
| `tests/test_pdf_writer.py` | Added | PDF Writer 테스트 (16 tests) |
| `tests/test_config.py` | Added | Config 관리 테스트 (6 tests) |
| `tests/test_integration_pdf.py` | Added | PDF 통합 테스트 (4 tests) |
| `tests/test_pipeline.py` | Rewritten | Pipeline 테스트 (4 tests) |
| `tests/test_llm_corrector.py` | Modified | 비정상 인덱스 엣지케이스 테스트 추가 |

## Details

### pdf_reader.py (New)
- `PageInfo` dataclass: width_pt, height_pt, dpi, page_num
- `extract_page_images()`: PyMuPDF로 PDF 페이지를 PIL Image로 변환, DPI 보존

### pdf_writer.py (New)
- `add_text_layer()`: 원본 PDF 위에 투명 텍스트 레이어 삽입
- `_px_to_pt()`: 픽셀 → PDF 포인트 변환 (px * 72 / dpi)
- `_calculate_fontsize()`: bbox 높이로 폰트 크기 계산 (× 0.85 scale factor)
- `_has_korean()`: 한글 감지 → CJK 폰트 선택
- debug_color 옵션으로 육안 검증 모드 지원

### config.py (New)
- `AppConfig` dataclass: gemini_api_key, lang, dpi, min_confidence, debug_color
- `load_config()`: config.ini 탐색 (exe 옆 → cwd → 환경변수)
- `_setup_tesseract_path()`: PyInstaller 번들 내 Tesseract 경로 자동 설정

### pipeline.py (Rewritten)
- `PipelineResult` dataclass: 처리 결과 메타데이터
- `process_pdf()`: PDF → OCR → LLM → 텍스트 레이어 → Searchable PDF
- `process_folder()`: 폴더 내 PDF 일괄 처리
- 페이지별 이미지 즉시 해제로 메모리 관리

### llm_corrector.py (Modified)
- LLM 응답 타입 검증 추가 (isinstance 체크)
- except Exception → ConnectionError/TimeoutError/RuntimeError/OSError
- Gemini 클라이언트 모듈 레벨 캐싱
- `set_api_key()` 함수 추가

### ocr_engine.py (Modified)
- `OcrWord.page_num: int = 0` 필드 추가

### build.spec (New)
- PyInstaller 빌드 설정: Tesseract 바이너리/tessdata 번들, --onefile 모드
