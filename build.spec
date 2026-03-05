# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ai-ocr Windows executable.

Usage:
    pyinstaller build.spec

Prerequisites (Windows):
    1. Install Tesseract OCR and note the install path (e.g. C:\\Program Files\\Tesseract-OCR)
    2. Set TESSERACT_PATH environment variable to the Tesseract install directory
    3. Ensure tessdata/ contains eng.traineddata and kor.traineddata

The spec bundles:
    - Tesseract binary + DLLs from TESSERACT_PATH
    - tessdata language files (eng, kor)
    - config.ini.example as config.ini template
"""
import os
import sys
from pathlib import Path

block_cipher = None

# Tesseract bundling (Windows only)
tesseract_binaries = []
tesseract_datas = []

tesseract_path = os.environ.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR")
if os.path.isdir(tesseract_path):
    # Bundle tesseract.exe and all DLLs
    tess_dir = Path(tesseract_path)
    for f in tess_dir.glob("*.exe"):
        tesseract_binaries.append((str(f), "."))
    for f in tess_dir.glob("*.dll"):
        tesseract_binaries.append((str(f), "."))

    # Bundle tessdata (eng + kor)
    tessdata_dir = tess_dir / "tessdata"
    if tessdata_dir.is_dir():
        for lang_file in ["eng.traineddata", "kor.traineddata", "osd.traineddata"]:
            lang_path = tessdata_dir / lang_file
            if lang_path.exists():
                tesseract_datas.append((str(lang_path), "tessdata"))


a = Analysis(
    ["src/ai_ocr/cli.py"],
    pathex=[],
    binaries=tesseract_binaries,
    datas=tesseract_datas + [
        ("config.ini.example", "."),
    ],
    hiddenimports=[
        "ai_ocr",
        "ai_ocr.ocr_engine",
        "ai_ocr.llm_corrector",
        "ai_ocr.pdf_reader",
        "ai_ocr.pdf_writer",
        "ai_ocr.pipeline",
        "ai_ocr.config",
        "pytesseract",
        "PIL",
        "fitz",
        "google.genai",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ai-ocr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
