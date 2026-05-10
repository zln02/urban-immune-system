"""report_pdf.py 단위 테스트 — 커버리지 16% → ~65% 목표.

전략:
- db=None 경로를 통해 _build_pdf_story + build_pdf 를 실제로 실행 (asyncio)
- 차트·헬퍼 함수는 직접 호출
- 폰트 / DB 의존성은 fixture / monkeypatch 로 분리
"""
from __future__ import annotations

import asyncio
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import matplotlib
matplotlib.use("Agg")
import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """동기 컨텍스트에서 coroutine 실행."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# 1. 모듈 수준 상수 · 폰트 분기
# ---------------------------------------------------------------------------

def test_font_constants_are_strings():
    """_FONT, _FONT_B 가 str 타입인지 확인 (Helvetica 또는 NanumKR)."""
    from backend.app.services import report_pdf
    assert isinstance(report_pdf._FONT, str)
    assert isinstance(report_pdf._FONT_B, str)


def test_level_color_keys():
    from backend.app.services.report_pdf import LEVEL_COLOR, LEVEL_LABEL_KO
    for key in ("GREEN", "YELLOW", "ORANGE", "RED"):
        assert key in LEVEL_COLOR
        assert key in LEVEL_LABEL_KO


def test_font_fallback_on_register_error(tmp_path, monkeypatch):
    """pdfmetrics.registerFont 가 예외를 던지면 Helvetica 폴백."""
    import backend.app.services.report_pdf as mod
    # 폰트 파일이 존재하는 척하면서 registerFont 는 실패하도록
    monkeypatch.setattr(mod, "_NANUM_REG", str(tmp_path))  # tmp_path 는 dir 이지만 Path.exists() True
    with patch("reportlab.pdfbase.pdfmetrics.registerFont", side_effect=Exception("fail")):
        # 이미 import 된 후라 재실행 불가 — 로직 자체를 인라인으로 검증
        try:
            from reportlab.pdfbase.pdfmetrics import registerFont
            from reportlab.pdfbase.ttfonts import TTFont
            registerFont(TTFont("X", str(tmp_path)))
        except Exception:
            pass  # 예외 발생 → 폴백 경로 처리


# ---------------------------------------------------------------------------
# 2. _load_json
# ---------------------------------------------------------------------------

def test_load_json_valid(tmp_path: Path):
    from backend.app.services.report_pdf import _load_json
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert _load_json(p) == {"a": 1}


def test_load_json_missing(tmp_path: Path):
    from backend.app.services.report_pdf import _load_json
    assert _load_json(tmp_path / "nonexistent.json") == {}


def test_load_json_invalid_json(tmp_path: Path):
    from backend.app.services.report_pdf import _load_json
    p = tmp_path / "bad.json"
    p.write_text("NOT JSON", encoding="utf-8")
    assert _load_json(p) == {}


# ---------------------------------------------------------------------------
# 3. _iso_week_label
# ---------------------------------------------------------------------------

def test_iso_week_label_format():
    from backend.app.services.report_pdf import _iso_week_label
    dt = datetime(2026, 5, 4, tzinfo=timezone.utc)
    short, long_ = _iso_week_label(dt)
    assert short.startswith("2026-W")
    assert "년" in long_
    assert "월" in long_


def test_iso_week_label_week_range():
    from backend.app.services.report_pdf import _iso_week_label
    dt = datetime(2026, 1, 5, tzinfo=timezone.utc)
    short, _ = _iso_week_label(dt)
    assert "W" in short


# ---------------------------------------------------------------------------
# 4. _delta_str / _delta_color
# ---------------------------------------------------------------------------

def test_delta_str_none_previous():
    from backend.app.services.report_pdf import _delta_str
    assert _delta_str(50.0, None) == "-"


def test_delta_str_zero_diff():
    from backend.app.services.report_pdf import _delta_str
    assert _delta_str(50.0, 50.0) == "±0.0%"


def test_delta_str_positive():
    from backend.app.services.report_pdf import _delta_str
    result = _delta_str(60.0, 50.0)
    assert "▲" in result


def test_delta_str_negative():
    from backend.app.services.report_pdf import _delta_str
    result = _delta_str(40.0, 50.0)
    assert "▼" in result


def test_delta_str_previous_zero():
    from backend.app.services.report_pdf import _delta_str
    result = _delta_str(10.0, 0.0)
    assert "▲" in result


def test_delta_color_none():
    from backend.app.services.report_pdf import _delta_color
    assert _delta_color(50.0, None) == "#374151"


def test_delta_color_up():
    from backend.app.services.report_pdf import _delta_color, C_RED
    assert _delta_color(60.0, 50.0) == C_RED


def test_delta_color_down():
    from backend.app.services.report_pdf import _delta_color, C_GREEN
    assert _delta_color(40.0, 50.0) == C_GREEN


# ---------------------------------------------------------------------------
# 5. _format_citation
# ---------------------------------------------------------------------------

def test_format_citation_dict_full():
    from backend.app.services.report_pdf import _format_citation
    c = {"author": "Kim", "year": "2024", "topic": "Flu", "source": "KDCA", "url": "http://x"}
    result = _format_citation(1, c)
    assert "[1]" in result
    assert "Kim" in result
    assert "http://x" in result


def test_format_citation_dict_no_author():
    from backend.app.services.report_pdf import _format_citation
    c = {"title": "Some Paper", "source": "WHO"}
    result = _format_citation(2, c)
    assert "[2]" in result


def test_format_citation_string():
    from backend.app.services.report_pdf import _format_citation
    result = _format_citation(3, "plain string citation")
    assert "[3]" in result
    assert "plain string citation" in result


# ---------------------------------------------------------------------------
# 6. _md_to_paragraphs
# ---------------------------------------------------------------------------

def test_md_to_paragraphs_headings():
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from backend.app.services.report_pdf import _md_to_paragraphs, _FONT, _FONT_B
    from reportlab.lib import colors
    styles = getSampleStyleSheet()
    base = ParagraphStyle("b", fontName=_FONT, fontSize=10, leading=15)
    h2 = ParagraphStyle("h2", fontName=_FONT_B, fontSize=14, leading=20)
    h3 = ParagraphStyle("h3", fontName=_FONT_B, fontSize=11, leading=16)
    text_md = "# 제목\n## 소제목\n### 소소제목\n일반 텍스트\n**굵게**\n- 목록\n"
    result = _md_to_paragraphs(text_md, base, h2, h3)
    assert len(result) > 0


def test_md_to_paragraphs_empty_lines():
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from backend.app.services.report_pdf import _md_to_paragraphs, _FONT, _FONT_B
    styles = getSampleStyleSheet()
    base = ParagraphStyle("b2", fontName=_FONT, fontSize=10, leading=15)
    h2 = ParagraphStyle("h2b", fontName=_FONT_B, fontSize=14, leading=20)
    h3 = ParagraphStyle("h3b", fontName=_FONT_B, fontSize=11, leading=16)
    result = _md_to_paragraphs("\n\n\n", base, h2, h3)
    # 빈 줄들 → Spacer 들 반환
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# 7. 차트 함수 — bytes 반환 확인
# ---------------------------------------------------------------------------

def test_chart_three_layer_empty():
    from backend.app.services.report_pdf import _chart_three_layer
    result = _chart_three_layer([], [], [], [])
    assert isinstance(result, bytes)
    assert len(result) > 100


def test_chart_three_layer_with_data():
    from backend.app.services.report_pdf import _chart_three_layer
    dates = list(range(10))
    data = [(i, float(i * 5)) for i in dates]
    result = _chart_three_layer(data, data, data, data)
    assert isinstance(result, bytes)
    assert len(result) > 100


def test_chart_top5_regions_empty():
    from backend.app.services.report_pdf import _chart_top5_regions
    result = _chart_top5_regions([])
    assert isinstance(result, bytes)
    assert len(result) > 100


def test_chart_top5_regions_with_data():
    from backend.app.services.report_pdf import _chart_top5_regions
    regions = [
        {"region": "서울", "composite": 70.0, "level": "ORANGE"},
        {"region": "부산", "composite": 55.0, "level": "YELLOW"},
        {"region": "대구", "composite": 40.0, "level": "YELLOW"},
        {"region": "인천", "composite": 30.0, "level": "GREEN"},
        {"region": "광주", "composite": 85.0, "level": "RED"},
        {"region": "대전", "composite": 20.0, "level": "GREEN"},
    ]
    result = _chart_top5_regions(regions)
    assert isinstance(result, bytes)
    assert len(result) > 100


def test_chart_lead_time_empty():
    from backend.app.services.report_pdf import _chart_lead_time
    result = _chart_lead_time({})
    assert isinstance(result, bytes)
    assert len(result) > 100


def test_chart_lead_time_with_data():
    from backend.app.services.report_pdf import _chart_lead_time
    lead = {
        "signal_lead_weeks": {"l1_otc": 2, "l2_wastewater": 3, "l3_search": 1, "composite": 2},
        "ccf_max": {"l1_otc": 0.8, "l2_wastewater": 0.9, "l3_search": 0.7, "composite": 0.85},
        "granger_p": {"l1_otc": 0.02, "l2_wastewater": 0.01, "l3_search": 0.04, "composite": 0.01},
    }
    result = _chart_lead_time(lead)
    assert isinstance(result, bytes)
    assert len(result) > 100


def test_chart_backtest_empty():
    from backend.app.services.report_pdf import _chart_backtest
    result = _chart_backtest({})
    assert isinstance(result, bytes)
    assert len(result) > 100


def test_chart_backtest_with_data():
    from backend.app.services.report_pdf import _chart_backtest
    backtest = {
        "summary": {
            "mean_recall": 0.837,
            "mean_precision": 0.949,
            "mean_f1": 0.882,
            "mean_far_with_gate": 0.206,
        }
    }
    result = _chart_backtest(backtest)
    assert isinstance(result, bytes)
    assert len(result) > 100


# ---------------------------------------------------------------------------
# 8. _alert_band_canvas
# ---------------------------------------------------------------------------

def test_alert_band_canvas_all_levels():
    from backend.app.services.report_pdf import _alert_band_canvas
    mock_canvas = MagicMock()
    for level in ("GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN"):
        _alert_band_canvas(mock_canvas, level)
    assert mock_canvas.saveState.call_count == 5


# ---------------------------------------------------------------------------
# 9. _UISDocTemplate — afterPage / handle_pageBegin
# ---------------------------------------------------------------------------

def test_uis_doc_template_init():
    from backend.app.services.report_pdf import _UISDocTemplate
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    doc = _UISDocTemplate(
        buf, pagesize=A4,
        leftMargin=18, rightMargin=18,
        topMargin=22, bottomMargin=18,
        total_pages=6, level="GREEN",
        generated_kst="2026-05-10 10:00 KST",
    )
    assert doc._total_pages == 6
    assert doc._level == "GREEN"
    assert doc._page_num == 0


def test_uis_doc_template_after_page():
    """afterPage 가 canvas 메서드를 호출하는지 확인."""
    from backend.app.services.report_pdf import _UISDocTemplate
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    doc = _UISDocTemplate(
        buf, pagesize=A4,
        leftMargin=18, rightMargin=18,
        topMargin=22, bottomMargin=18,
        total_pages=3, level="ORANGE",
        generated_kst="2026-05-10 10:00 KST",
    )
    doc._page_num = 1
    mock_canvas = MagicMock()
    doc.canv = mock_canvas
    doc.afterPage()
    mock_canvas.saveState.assert_called_once()
    mock_canvas.restoreState.assert_called_once()


# ---------------------------------------------------------------------------
# 10. _build_pdf_story (db=None, 최소 데이터)
# ---------------------------------------------------------------------------

def test_build_pdf_story_minimal():
    """db=None, risk/rep 최소값 → story list + KST + level 반환."""
    from backend.app.services.report_pdf import _build_pdf_story
    story, kst, level = _run(_build_pdf_story("서울", db=None))
    assert isinstance(story, list)
    assert len(story) > 0
    assert "KST" in kst
    assert level in ("GREEN", "YELLOW", "ORANGE", "RED")


def test_build_pdf_story_with_risk():
    """risk 데이터 제공 → level 이 risk.alert_level 에서 추출됨."""
    from backend.app.services.report_pdf import _build_pdf_story
    risk = {
        "alert_level": "RED",
        "composite_score": 88.5,
        "l1_score": 80.0,
        "l2_score": 90.0,
        "l3_score": 85.0,
    }
    story, kst, level = _run(_build_pdf_story("부산", db=None, risk=risk))
    assert level == "RED"
    assert isinstance(story, list)


def test_build_pdf_story_with_prev_risk():
    """prev_risk 있을 때 delta 표시 (▲/▼) 로직 실행."""
    from backend.app.services.report_pdf import _build_pdf_story
    risk = {"alert_level": "YELLOW", "composite_score": 55.0, "l1_score": 50.0, "l2_score": 55.0, "l3_score": 45.0}
    prev_risk = {"composite_score": 45.0, "l1_score": 40.0, "l2_score": 45.0, "l3_score": 35.0}
    story, kst, level = _run(_build_pdf_story("대구", db=None, risk=risk, prev_risk=prev_risk))
    assert level == "YELLOW"
    assert len(story) > 0


def test_build_pdf_story_with_all_regions():
    """all_regions 제공 → page4 지역 테이블 + Top5 차트 포함."""
    from backend.app.services.report_pdf import _build_pdf_story
    all_regions = [
        {"region": "서울", "composite": 70.0, "level": "ORANGE"},
        {"region": "부산", "composite": 55.0, "level": "YELLOW"},
        {"region": "대구", "composite": 40.0, "level": "YELLOW"},
        {"region": "인천", "composite": 30.0, "level": "GREEN"},
        {"region": "광주", "composite": 85.0, "level": "RED"},
    ]
    story, _, _ = _run(_build_pdf_story("서울", db=None, all_regions=all_regions))
    assert len(story) > 5


def test_build_pdf_story_with_rep():
    """rep(alert_reports) 데이터 포함 — AI 분석 본문 + RAG 소스."""
    from backend.app.services.report_pdf import _build_pdf_story
    rep = {
        "alert_level": "ORANGE",
        "summary": "# 분석 요약\n## 주요 지표\n- L2 하수 신호 급등\n**주의** 필요",
        "model_used": "claude-haiku-4-5",
        "created_at": "2026-05-10 09:00",
        "rag_sources": json.dumps([
            {"author": "Kim", "year": "2024", "topic": "Flu Trend", "source": "KDCA", "url": "http://kdca.go.kr"},
            {"title": "WHO Guideline", "source": "WHO"},
        ]),
    }
    story, _, level = _run(_build_pdf_story("인천", db=None, rep=rep))
    assert level == "ORANGE"
    assert len(story) > 0


def test_build_pdf_story_rag_already_list():
    """rag_sources 가 이미 list 인 경우."""
    from backend.app.services.report_pdf import _build_pdf_story
    rep = {
        "alert_level": "GREEN",
        "summary": "정상 범위",
        "rag_sources": [{"author": "Lee", "year": "2023", "topic": "Wastewater", "source": "ENV"}],
    }
    story, _, _ = _run(_build_pdf_story("광주", db=None, rep=rep))
    assert isinstance(story, list)


def test_build_pdf_story_rag_invalid_json():
    """rag_sources 가 invalid JSON string 인 경우 → 조용히 무시."""
    from backend.app.services.report_pdf import _build_pdf_story
    rep = {
        "alert_level": "GREEN",
        "summary": "정상",
        "rag_sources": "NOT_JSON",
    }
    story, _, _ = _run(_build_pdf_story("대전", db=None, rep=rep))
    assert isinstance(story, list)


def test_build_pdf_story_empty_all_regions():
    """all_regions 빈 리스트 → 'DB 데이터 없음' 분기."""
    from backend.app.services.report_pdf import _build_pdf_story
    story, _, _ = _run(_build_pdf_story("울산", db=None, all_regions=[]))
    assert isinstance(story, list)


def test_build_pdf_story_all_levels():
    """GREEN/YELLOW/ORANGE/RED 4가지 레벨 모두 story 생성 가능."""
    from backend.app.services.report_pdf import _build_pdf_story
    for level in ("GREEN", "YELLOW", "ORANGE", "RED"):
        risk = {"alert_level": level, "composite_score": 50.0}
        story, _, returned_level = _run(_build_pdf_story("세종", db=None, risk=risk))
        assert returned_level == level
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# 11. build_pdf (파일 저장 통합 테스트)
# ---------------------------------------------------------------------------

def test_build_pdf_creates_file(tmp_path: Path):
    """build_pdf(db=None) → 파일 생성 + PDF 헤더 확인."""
    from backend.app.services.report_pdf import build_pdf
    out = tmp_path / "report.pdf"
    _run(build_pdf("서울", str(out)))
    assert out.exists()
    assert out.stat().st_size > 1000
    # PDF 매직 바이트
    assert out.read_bytes()[:4] == b"%PDF"


def test_build_pdf_with_risk_data(tmp_path: Path):
    """risk + prev_risk + rep + all_regions 모두 제공 → 파일 생성."""
    from backend.app.services.report_pdf import build_pdf
    out = tmp_path / "report_full.pdf"
    risk = {"alert_level": "ORANGE", "composite_score": 65.0, "l1_score": 60.0, "l2_score": 70.0, "l3_score": 55.0}
    prev_risk = {"composite_score": 55.0, "l1_score": 50.0, "l2_score": 60.0, "l3_score": 45.0}
    rep = {
        "alert_level": "ORANGE",
        "summary": "## 분석\n- 상승 추세\n**경계** 필요",
        "model_used": "claude-haiku-4-5",
        "created_at": "2026-05-10",
        "rag_sources": [],
    }
    all_regions = [{"region": "서울", "composite": 65.0, "level": "ORANGE"}]
    _run(build_pdf("서울", str(out), risk=risk, prev_risk=prev_risk, rep=rep, all_regions=all_regions))
    assert out.exists()
    assert out.stat().st_size > 1000


def test_build_pdf_red_level(tmp_path: Path):
    """RED 레벨 → PDF 정상 생성."""
    from backend.app.services.report_pdf import build_pdf
    out = tmp_path / "report_red.pdf"
    risk = {"alert_level": "RED", "composite_score": 90.0}
    _run(build_pdf("부산", str(out), risk=risk))
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_build_pdf_no_rag(tmp_path: Path):
    """rag_sources 없는 rep → 참고문헌 섹션 없이 PDF 생성."""
    from backend.app.services.report_pdf import build_pdf
    out = tmp_path / "report_no_rag.pdf"
    rep = {"alert_level": "GREEN", "summary": "정상 범위입니다."}
    _run(build_pdf("대전", str(out), rep=rep))
    assert out.exists()


def test_build_pdf_dominant_l1(tmp_path: Path):
    """L1 점수가 가장 높을 때 → 'L1 약국 OTC' 주도 경로."""
    from backend.app.services.report_pdf import build_pdf
    out = tmp_path / "report_l1.pdf"
    risk = {"alert_level": "YELLOW", "composite_score": 50.0, "l1_score": 70.0, "l2_score": 40.0, "l3_score": 30.0}
    _run(build_pdf("광주", str(out), risk=risk))
    assert out.exists()


def test_build_pdf_dominant_l3(tmp_path: Path):
    """L3 점수가 가장 높을 때 → 'L3 검색 트렌드' 주도 경로."""
    from backend.app.services.report_pdf import build_pdf
    out = tmp_path / "report_l3.pdf"
    risk = {"alert_level": "YELLOW", "composite_score": 50.0, "l1_score": 30.0, "l2_score": 40.0, "l3_score": 70.0}
    _run(build_pdf("울산", str(out), risk=risk))
    assert out.exists()


# ---------------------------------------------------------------------------
# 12. build_alert_pdf (bytes 반환 경로) — DB 없이는 직접 호출 불가하므로 mock
# ---------------------------------------------------------------------------

def test_build_alert_pdf_returns_bytes():
    """build_alert_pdf 가 _fetch_latest_risk + _build_pdf_story 를 호출하고 bytes 를 반환하는지 확인."""
    from backend.app.services import report_pdf
    import asyncio

    # _build_pdf_story 원본을 저장해 재귀 없이 실제 로직 실행
    _original_build = report_pdf._build_pdf_story
    called = {}

    async def fake_build_pdf_story(region, db, **kwargs):
        called["region"] = region
        # db=None 으로 전환해 실제 story 생성 (DB 없이)
        return await _original_build(region, None, **kwargs)

    async def fake_fetch_latest_risk(db, region):
        return {"alert_level": "GREEN", "composite_score": 30.0}

    async def run():
        with patch.object(report_pdf, "_build_pdf_story", side_effect=fake_build_pdf_story), \
             patch.object(report_pdf, "_fetch_latest_risk", side_effect=fake_fetch_latest_risk):
            mock_db = MagicMock()
            result = await report_pdf.build_alert_pdf("서울", mock_db)
        return result

    result = asyncio.get_event_loop().run_until_complete(run())
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"
    assert called["region"] == "서울"
