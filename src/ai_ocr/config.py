"""Configuration management — loads settings from config.ini."""
from __future__ import annotations

import configparser
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union


@dataclass
class AppConfig:
    gemini_api_key: str = ""
    lang: str = "kor+eng"
    dpi: int = 300
    min_confidence: int = 30
    debug_color: str = ""


def _find_config_file() -> Optional[Path]:
    """Search for config.ini in priority order."""
    candidates: list[Path] = []

    # 1. Next to the PyInstaller bundle or executable
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass).parent / "config.ini")
    candidates.append(Path(sys.executable).parent / "config.ini")

    # 2. Current working directory
    candidates.append(Path.cwd() / "config.ini")

    for path in candidates:
        if path.is_file():
            return path

    return None


def load_config(config_path: Optional[Union[str, Path]] = None) -> AppConfig:
    """Load AppConfig from config.ini, falling back to environment variables."""
    cfg = AppConfig()

    # Resolve the config file path
    if config_path is not None:
        resolved = Path(config_path)
        ini_path: Optional[Path] = resolved if resolved.is_file() else None
    else:
        ini_path = _find_config_file()

    if ini_path is not None:
        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8")

        if parser.has_option("api", "gemini_api_key"):
            cfg.gemini_api_key = parser.get("api", "gemini_api_key")

        if parser.has_option("ocr", "lang"):
            cfg.lang = parser.get("ocr", "lang")
        if parser.has_option("ocr", "dpi"):
            cfg.dpi = parser.getint("ocr", "dpi")
        if parser.has_option("ocr", "min_confidence"):
            cfg.min_confidence = parser.getint("ocr", "min_confidence")

        if parser.has_option("output", "debug_color"):
            cfg.debug_color = parser.get("output", "debug_color")

    # Environment variable always overrides config.ini
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key:
        cfg.gemini_api_key = env_key

    # Configure Tesseract path for PyInstaller bundle
    _setup_tesseract_path()

    return cfg


def _setup_tesseract_path() -> None:
    """Set pytesseract command path when running from a PyInstaller bundle."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is None:
        return

    import pytesseract
    bundle_dir = Path(meipass)
    tesseract_exe = bundle_dir / "tesseract.exe"
    if tesseract_exe.exists():
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)
        os.environ["TESSDATA_PREFIX"] = str(bundle_dir / "tessdata")
