# Plan History

| Date | Title | Status | Detail |
|------|-------|--------|--------|
| 2026-03-05 22:55 | Searchable PDF Pipeline Rebuild | **Proposed** | [detail](plans/2026-03-05_225500_searchable-pdf-rebuild.md) |
| 2026-02-22 | OCR with LLM Correction | **Completed** | [detail](plans/2026-02-22-ocr-with-llm-correction.md) |

## Entries

### 2026-03-05 — Searchable PDF Pipeline Rebuild
기존 이미지 OCR 파이프라인을 스캔된 PDF → Searchable PDF 파이프라인으로 전면 재구축. Tesseract + PyMuPDF `render_mode=3` 투명 텍스트 레이어 + Gemini LLM 보정 + Windows .exe 배포. 10개 Task로 구성.

### 2026-02-22 — OCR with LLM Correction
Tesseract → Gemini 3 Flash 2단계 OCR 파이프라인 초기 구현. 8개 Task, 17개 자동 테스트. 현재 완료 상태.
