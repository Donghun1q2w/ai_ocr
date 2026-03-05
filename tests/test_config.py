"""Tests for config management module."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from ai_ocr.config import AppConfig, load_config


def _write_ini(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Default values when no config file exists and no env vars are set
# ---------------------------------------------------------------------------

def test_defaults_when_no_config(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Point to a non-existent file so no ini is loaded
    cfg = load_config(config_path=tmp_path / "nonexistent.ini")
    assert cfg.gemini_api_key == ""
    assert cfg.lang == "kor+eng"
    assert cfg.dpi == 300
    assert cfg.min_confidence == 30
    assert cfg.debug_color == ""


# ---------------------------------------------------------------------------
# Loading from an explicit config.ini path
# ---------------------------------------------------------------------------

def test_load_from_explicit_path(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ini = tmp_path / "config.ini"
    _write_ini(ini, """
[api]
gemini_api_key = test-key-123

[ocr]
lang = eng
dpi = 150
min_confidence = 50

[output]
debug_color = red
""")
    cfg = load_config(config_path=ini)
    assert cfg.gemini_api_key == "test-key-123"
    assert cfg.lang == "eng"
    assert cfg.dpi == 150
    assert cfg.min_confidence == 50
    assert cfg.debug_color == "red"


def test_partial_ini_uses_defaults_for_missing_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ini = tmp_path / "config.ini"
    _write_ini(ini, """
[ocr]
lang = jpn
""")
    cfg = load_config(config_path=ini)
    assert cfg.lang == "jpn"
    assert cfg.dpi == 300          # default
    assert cfg.min_confidence == 30  # default
    assert cfg.gemini_api_key == ""  # default


# ---------------------------------------------------------------------------
# Environment variable fallback
# ---------------------------------------------------------------------------

def test_env_var_sets_api_key_when_no_ini(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key-abc")
    cfg = load_config(config_path=tmp_path / "nonexistent.ini")
    assert cfg.gemini_api_key == "env-key-abc"


def test_env_var_overrides_ini_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "override-key")
    ini = tmp_path / "config.ini"
    _write_ini(ini, """
[api]
gemini_api_key = ini-key
""")
    cfg = load_config(config_path=ini)
    # env var takes priority over ini value
    assert cfg.gemini_api_key == "override-key"


def test_ini_api_key_used_when_env_var_absent(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ini = tmp_path / "config.ini"
    _write_ini(ini, """
[api]
gemini_api_key = ini-only-key
""")
    cfg = load_config(config_path=ini)
    assert cfg.gemini_api_key == "ini-only-key"
