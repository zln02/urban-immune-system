"""상관관계 탭 — 실측 JSON 로드 기반 (하드코딩 제거, 2026-04 P0)."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.components.image_card import render_image_card
from src.config import L1_PHARMACY, L2_SEARCH, L2_SEWAGE, L3_SEARCH  # noqa: F401

CORRELATION_JSON = Path(__file__).resolve().parents[2] / "ml" / "outputs" / "correlation.json"

_LAYER_META = {
    "L1_pharmacy": ("약국 OTC", L1_PHARMACY),
    "L2_sewage": ("하수 바이오마커", L2_SEWAGE),
    "L3_search": ("검색어 트렌드", L3_SEARCH),
}


def _load_correlation() -> dict | None:
    if not CORRELATION_JSON.exists():
        return None
    try:
        return json.loads(CORRELATION_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def render_correlation_tab() -> None:
    st.markdown("#### Cross-correlation + Granger 인과검정 결과")
    render_image_card("slide7_crosscorr.png", "📁 `slide7_crosscorr.png` 는 분석 노트북에서 생성 예정")

    data = _load_correlation()
    if data is None:
        st.warning(
            "📁 `ml/outputs/correlation.json` 이 없습니다. "
            "`python analysis/notebooks/performance_measurement.py` 로 생성하세요."
        )
        return

    st.caption(f"🕐 측정: {data.get('generated_at', 'N/A')}  ·  실측 statsmodels grangercausalitytests(maxlag=4) 결과")

    granger = data.get("granger_causality", {})
    crosscorr = data.get("cross_correlation", {})

    chips = []
    for key, (label, color) in _LAYER_META.items():
        g = granger.get(key, {})
        cc = crosscorr.get(key, {})
        lag = cc.get("lag_weeks_best", "-")
        p_val = g.get("p_value", 1.0)
        is_sig = g.get("significant_at_0_05", False)
        mark = "✅ 유의" if is_sig else "⚠️ 비유의"
        chips.append(
            f"""
            <div class="stat-chip">
                <div class="label">{label}</div>
                <div class="value" style="color:{color};">{lag if lag != '-' else '-'}주 lag</div>
                <div class="sub">p = {p_val:.4f} · {mark}</div>
            </div>
            """
        )

    all_sig = all(v.get("significant_at_0_05", False) for v in granger.values())
    conclusion = (
        "✅ 3개 Layer 모두 통계적으로 유의한 선행 지표 (All p < 0.05)"
        if all_sig
        else "⚠️ 일부 Layer 비유의 — 재측정·추가 데이터 필요"
    )

    st.markdown(
        f"""
        <div class="stat-row">{''.join(chips)}</div>
        <div class="highlight-row" style="text-align:center;">{conclusion}</div>
        """,
        unsafe_allow_html=True,
    )
