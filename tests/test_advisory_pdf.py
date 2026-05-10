"""advisory_pdf.py 단위 테스트 (커버리지 0% → 목표 커버리지 상승)."""
from __future__ import annotations

import json
import matplotlib
matplotlib.use("Agg")

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.services.advisory_pdf import (
    _chart_attention,
    _chart_lead_time,
    _limitations,
    _load_json,
    _references,
    _styles,
    build_advisory_pdf,
)


# ---------------------------------------------------------------------------
# 1. _load_json
# ---------------------------------------------------------------------------

def test_load_json_exists(tmp_path: Path) -> None:
    """존재하는 JSON 파일 → dict 반환."""
    data = {"key": "value", "count": 42}
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    result = _load_json(json_file)
    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["count"] == 42


def test_load_json_missing(tmp_path: Path) -> None:
    """존재하지 않는 경로 → 빈 dict 반환."""
    missing_path = tmp_path / "nonexistent.json"
    result = _load_json(missing_path)
    assert result == {}


# ---------------------------------------------------------------------------
# 2. 차트 함수
# ---------------------------------------------------------------------------

def test_chart_attention_empty() -> None:
    """빈 metrics dict → bytes 타입 반환."""
    result = _chart_attention({})
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_chart_lead_time_empty() -> None:
    """빈 lead dict → bytes 타입 반환."""
    result = _chart_lead_time({})
    assert isinstance(result, bytes)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# 3. 스토리 빌더
# ---------------------------------------------------------------------------

def test_limitations_returns_list() -> None:
    """_limitations(styles) → list 반환, 비어있지 않음."""
    s = _styles()
    result = _limitations(s)
    assert isinstance(result, list)
    assert len(result) > 0


def test_references_returns_list() -> None:
    """_references(styles) → list 반환, 비어있지 않음."""
    s = _styles()
    result = _references(s)
    assert isinstance(result, list)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# 4. build_advisory_pdf 통합
# ---------------------------------------------------------------------------

def test_build_advisory_pdf_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_load_json 패치 + 경로 상수 monkeypatch → PDF 파일 생성 및 크기 검증."""
    # ART_DIR / ML_DIR 을 tmp_path 로 대체 (존재하지 않아도 _load_json 패치로 우회)
    import backend.app.services.advisory_pdf as advisory_mod
    monkeypatch.setattr(advisory_mod, "ART_DIR", tmp_path)
    monkeypatch.setattr(advisory_mod, "ML_DIR", tmp_path)

    # _load_json 을 항상 {} 반환하도록 패치
    with patch.object(advisory_mod, "_load_json", return_value={}):
        out_path = tmp_path / "out.pdf"
        result = build_advisory_pdf(out_path, week_label="2026-W18")

    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 1000
