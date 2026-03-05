# Searchable PDF Pipeline Rebuild Plan

## Summary

기존 이미지 OCR 파이프라인을 스캔된 PDF 입력 → Searchable PDF 출력 파이프라인으로 전면 재구축한다. Tesseract OCR로 워드 레벨 바운딩 박스를 추출하고, PyMuPDF `render_mode=3`으로 원본 이미지 위에 투명 텍스트 레이어를 매핑한다. Gemini LLM으로 OCR 텍스트를 보정하며, Windows 독립 실행 .exe로 배포한다.

## Background

- 기존 코드: 단일 이미지 → 텍스트 추출/반환 목적 (Tesseract + Gemini 2단계)
- 신규 요구: 스캔 PDF(100+ 페이지, 한/영/수식) → 텍스트 검색 가능한 PDF 생성
- Adobe Acrobat Pro의 OCR 기능과 동등한 결과물 요구
- 95%+ 텍스트 위치/크기 정확도, 육안 검증 모드(붉은색 텍스트) 필요

## Tech Stack Decision

| 역할 | 선택 | 근거 |
|------|------|------|
| OCR 엔진 | Tesseract (pytesseract) | 유일한 네이티브 워드 레벨 바운딩 박스, 최소 번들 크기 |
| PDF 처리 | PyMuPDF (fitz) | `render_mode=3` 투명 텍스트 API, 페이지→이미지 변환 통합 |
| LLM 보정 | Gemini 3 Flash (google-genai) | 기존 코드 재활용, OCR 오인식 보정 |
| 배포 | PyInstaller | Windows .exe 독립 실행 파일 생성 |
| 설정 관리 | configparser (config.ini) | exe 옆 설정 파일로 API 키 관리 |

## Architecture

```
[Scanned PDF]
     │
     ▼
┌─────────────────┐
│ PDF Page Loader  │  PyMuPDF: PDF → page images (PIL)
│ (pdf_reader.py)  │  페이지별 DPI/크기 정보 보존
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OCR Engine       │  Tesseract: image → OcrWord[] (text + bbox)
│ (ocr_engine.py)  │  워드 레벨 위치/크기/신뢰도 추출
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Corrector    │  Gemini: OcrWord[] → 보정된 OcrWord[]
│ (llm_corrector.py)│  선택적, 신뢰도 낮은 단어만 보정
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PDF Writer       │  PyMuPDF: OcrWord[] → 투명 텍스트 레이어
│ (pdf_writer.py)  │  render_mode=3, 폰트 크기 매칭
└────────┬────────┘
         │
         ▼
[Searchable PDF]
```

### 데이터 흐름

1. **pdf_reader.py**: PDF 페이지를 PIL Image로 변환 (DPI 정보 유지)
2. **ocr_engine.py**: 이미지에서 OcrWord 리스트 추출 (기존 코드 개조)
3. **llm_corrector.py**: OcrWord 텍스트 보정 (기존 코드 재활용)
4. **pdf_writer.py**: 원본 PDF 페이지 위에 투명 텍스트 삽입
5. **pipeline.py**: 전체 흐름 조율, 페이지별 처리, 진행률 표시
6. **cli.py**: 단일 파일 + 폴더 일괄 처리 CLI

### 핵심 모듈 상세

#### pdf_reader.py
- `extract_page_images(pdf_path, dpi=300) -> list[(Image, page_info)]`
- 페이지별 원본 크기(pt), 렌더링 DPI 보존
- PyMuPDF `page.get_pixmap(dpi=300)` 사용

#### pdf_writer.py
- `add_text_layer(pdf_path, output_path, pages_words, debug_color=None)`
- 각 OcrWord의 bbox를 이미지 좌표 → PDF 좌표(pt)로 변환
- `page.insert_text(point, text, fontsize=calculated, render_mode=3)`
- `debug_color="red"` 옵션으로 육안 검증 모드

#### 좌표 변환 로직 (핵심)
```
PDF 좌표(pt) = 이미지 좌표(px) × (72 / render_dpi)
폰트 크기(pt) = bbox_height(px) × (72 / render_dpi) × scale_factor
```
- Tesseract bbox는 이미지 픽셀 단위 → PDF 포인트로 변환 필요
- scale_factor는 실제 글리프 높이와 bbox 높이의 비율 보정값

## Acceptance Criteria

| # | 기준 | 검증 방법 |
|---|------|----------|
| AC1 | 100+ 페이지 PDF 처리 완료 | 샘플 PDF로 전체 파이프라인 실행 |
| AC2 | 출력 PDF에서 텍스트 선택/복사 가능 | PDF 뷰어에서 텍스트 드래그 |
| AC3 | 원본 이미지 그대로 유지 | 출력 PDF 육안 비교 |
| AC4 | 붉은색 디버그 모드로 위치 확인 | `--debug-color red` 실행 후 육안 비교 |
| AC5 | 텍스트 위치/크기 95%+ 일치 | 디버그 모드에서 빨간 텍스트가 원본 글자와 겹침 확인 |
| AC6 | 한/영 혼합 텍스트 정상 인식 | 한영 혼합 문서로 테스트 |
| AC7 | 수식/특수문자 유니코드 인식 시도 | 수식 포함 문서로 테스트 |
| AC8 | `ocr_tool.exe input.pdf output.pdf` 동작 | Windows에서 실행 |
| AC9 | `ocr_tool.exe ./input_folder/ ./output_folder/` 동작 | 폴더 일괄 처리 |
| AC10 | exe 옆 config.ini로 API 키 로드 | config.ini 배치 후 실행 |
| AC11 | Python 미설치 Windows에서 실행 | 클린 Windows 환경 테스트 |

## Implementation Steps

### Task 1: 프로젝트 구조 재편 및 의존성 갱신

**Files:**
- Modify: `ai_ocr/pyproject.toml`
- Create: `ai_ocr/src/ai_ocr/pdf_reader.py`
- Create: `ai_ocr/src/ai_ocr/pdf_writer.py`
- Create: `ai_ocr/src/ai_ocr/config.py`

**Steps:**
1. `pyproject.toml` 의존성 추가: `PyMuPDF>=1.24.0`
2. `pyproject.toml` 의존성 추가: `pyinstaller>=6.0` (dev)
3. 빈 모듈 파일 생성 (pdf_reader.py, pdf_writer.py, config.py)
4. `pip install -e ".[dev]"` 재설치

---

### Task 2: PDF Reader — 페이지 이미지 추출

**Files:**
- Create: `ai_ocr/tests/test_pdf_reader.py`
- Implement: `ai_ocr/src/ai_ocr/pdf_reader.py`

**Steps:**
1. 테스트용 샘플 PDF fixture 생성 (PyMuPDF로 테스트 PDF 프로그래매틱 생성)
2. 테스트 작성: `extract_page_images()`가 PIL Image 리스트 반환, 페이지 수 일치
3. 구현:
   - `PageInfo` dataclass: `width_pt`, `height_pt`, `dpi`, `page_num`
   - `extract_page_images(pdf_path, dpi=300) -> list[tuple[Image, PageInfo]]`
   - PyMuPDF `page.get_pixmap(dpi=dpi)` → PIL Image 변환
4. 테스트 통과 확인

---

### Task 3: OCR Engine 개조

**Files:**
- Modify: `ai_ocr/src/ai_ocr/ocr_engine.py`
- Modify: `ai_ocr/tests/test_ocr_engine.py`

**Steps:**
1. `OcrWord` dataclass에 `page_num: int` 필드 추가
2. `extract_words_with_boxes()`에 `page_num` 파라미터 추가
3. 기존 테스트 업데이트
4. 테스트 통과 확인

---

### Task 4: PDF Writer — 투명 텍스트 레이어 생성

**Files:**
- Create: `ai_ocr/tests/test_pdf_writer.py`
- Implement: `ai_ocr/src/ai_ocr/pdf_writer.py`

**Steps:**
1. 테스트 작성:
   - 출력 PDF에 텍스트 검색 가능 (`page.search_for("test word")` 결과 존재)
   - 원본 이미지 보존 (페이지 수, 크기 동일)
   - 디버그 모드에서 텍스트 색상이 빨간색
2. 좌표 변환 함수 구현:
   - `_px_to_pt(px_value, dpi) -> float`: 픽셀 → PDF 포인트
   - `_calculate_fontsize(bbox_height_px, dpi) -> float`: bbox 높이로 폰트 크기 계산
3. 텍스트 레이어 삽입 구현:
   - `add_text_layer(src_pdf, out_pdf, pages_words, dpi=300, debug_color=None)`
   - 각 페이지별로 OcrWord 리스트를 투명 텍스트로 삽입
   - `page.insert_text(fitz.Point(x_pt, y_pt), word.text, fontsize=fs, render_mode=3)`
   - debug_color 지정 시 `render_mode=0` + 해당 색상으로 표시
4. 한글 폰트 처리:
   - PyMuPDF 내장 CJK 폰트 사용 (`fontname="ko"` 또는 `"china-s"`)
   - 또는 시스템 폰트 경로 지정
5. 테스트 통과 확인

---

### Task 5: 파이프라인 재구축

**Files:**
- Rewrite: `ai_ocr/src/ai_ocr/pipeline.py`
- Rewrite: `ai_ocr/tests/test_pipeline.py`

**Steps:**
1. `OcrPipeline` 클래스 재설계:
   ```python
   class OcrPipeline:
       def __init__(self, use_llm=True, lang="eng", dpi=300,
                    min_confidence=0, debug_color=None)
       def process_pdf(self, input_pdf, output_pdf) -> PipelineResult
       def process_folder(self, input_dir, output_dir) -> list[PipelineResult]
   ```
2. `PipelineResult` dataclass:
   - `input_path`, `output_path`, `total_pages`, `total_words`, `corrected_words`, `elapsed_seconds`
3. 페이지별 처리 루프:
   - progress 출력 (`Page 1/120 ...`)
   - 메모리 관리: 페이지별로 이미지 생성→OCR→해제
4. 테스트: mock으로 전체 흐름 검증

---

### Task 6: Config 관리 (config.ini)

**Files:**
- Implement: `ai_ocr/src/ai_ocr/config.py`
- Create: `ai_ocr/config.ini.example`

**Steps:**
1. `config.ini` 포맷:
   ```ini
   [api]
   gemini_api_key = your-key-here

   [ocr]
   lang = kor+eng
   dpi = 300
   min_confidence = 30

   [output]
   debug_color =
   ```
2. `load_config()`: exe 옆 → 현재 디렉토리 → 환경변수 순서로 탐색
3. 테스트 작성 및 통과

---

### Task 7: CLI 재구축

**Files:**
- Rewrite: `ai_ocr/src/ai_ocr/cli.py`

**Steps:**
1. 사용법:
   ```
   ai-ocr input.pdf output.pdf [options]
   ai-ocr ./input_folder/ ./output_folder/ [options]
   ```
2. 옵션:
   - `--lang` (기본: kor+eng)
   - `--no-llm` (LLM 보정 건너뛰기)
   - `--dpi` (기본: 300)
   - `--min-confidence` (기본: 30)
   - `--debug-color red` (디버그 모드)
3. 단일 파일 vs 폴더 자동 감지 (`Path.is_dir()`)
4. 진행률 표시, 에러 핸들링

---

### Task 8: LLM Corrector 개선

**Files:**
- Modify: `ai_ocr/src/ai_ocr/llm_corrector.py`

**Steps:**
1. 코드 리뷰에서 발견된 HIGH 이슈 수정: LLM 응답 타입 검증 추가
2. `except Exception` → 구체적 예외로 좁히기
3. Gemini 클라이언트 캐싱 (모듈 레벨)
4. config.ini에서 API 키 로드 지원
5. 기존 테스트 + 새 엣지케이스 테스트 추가

---

### Task 9: Windows .exe 빌드

**Files:**
- Create: `ai_ocr/build.spec` (PyInstaller spec)
- Create: `ai_ocr/scripts/build_exe.py`

**Steps:**
1. PyInstaller spec 작성:
   - Tesseract 바이너리 + tessdata 번들 (`--add-binary`)
   - PyMuPDF DLL 포함
   - `--onefile` 모드
2. Tesseract 번들링:
   - Windows용 Tesseract portable 다운로드
   - `tessdata/eng.traineddata` + `kor.traineddata` 포함
   - 런타임에 임시 추출 경로에서 Tesseract 실행하도록 `pytesseract.pytesseract.tesseract_cmd` 설정
3. 빌드 스크립트 작성
4. 클린 Windows 환경에서 테스트

---

### Task 10: 통합 테스트 및 정확도 검증

**Files:**
- Create: `ai_ocr/tests/test_integration_pdf.py`

**Steps:**
1. 프로그래매틱으로 테스트 PDF 생성 (PyMuPDF로 텍스트 렌더링 → 이미지화)
2. 파이프라인 실행 → 출력 PDF에서 텍스트 검색 검증
3. 디버그 모드 출력 생성하여 좌표 정확도 시각 확인
4. 폴더 일괄 처리 테스트

## Risks and Mitigations

| 위험 | 영향 | 완화 방안 |
|------|------|----------|
| Tesseract 한글 인식 정확도 부족 | 텍스트 품질 저하 | Gemini LLM 보정 적극 활용, DPI 300+ |
| 폰트 크기 매칭 오차 | 95% 목표 미달 | scale_factor 튜닝, 디버그 모드로 반복 보정 |
| PyInstaller + Tesseract 번들 복잡성 | 빌드 실패 | 별도 Task로 분리, 단계적 검증 |
| 100+ 페이지 처리 시 메모리 | OOM 크래시 | 페이지별 처리 + 즉시 해제 |
| 수식/특수문자 인식 한계 | 인식 실패 | Gemini로 보정 시도, 인식 불가 시 빈 텍스트 |
| CJK 폰트 투명 텍스트 렌더링 이슈 | 한글 검색 불가 | PyMuPDF 내장 CJK 폰트 우선 사용 |

## Verification Steps

1. `python -m pytest tests/ -v` — 전체 테스트 통과
2. 한영 혼합 샘플 PDF로 파이프라인 실행 → 텍스트 선택/복사 확인
3. `--debug-color red`로 실행 → 빨간 텍스트와 원본 글자 겹침 육안 확인
4. `pyinstaller build.spec` → Windows exe 생성 → 클린 환경 실행 확인
5. 폴더 일괄 처리 (`./input/ → ./output/`) 정상 동작 확인

## Open Questions

1. Tesseract 한글 인식률이 실제 대상 문서에서 충분한지 — 10-20 페이지 샘플로 사전 검증 필요
2. PyMuPDF CJK 내장 폰트로 한글 투명 텍스트가 정상 작동하는지 — Task 4에서 조기 검증
3. `--onefile` exe 크기가 수용 가능한 수준인지 (~200-300MB 예상) — Task 9에서 확인
