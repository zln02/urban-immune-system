"""상관관계 탭."""

from __future__ import annotations

import streamlit as st

from src.components.image_card import render_image_card
from src.config import L1_PHARMACY, L2_SEWAGE, L3_SEARCH


def render_correlation_tab() -> None:
    st.markdown("#### Cross-correlation + Granger 인과검정 결과")
    render_image_card("slide7_crosscorr.png", "📁 `assets/slide7_crosscorr.png` 파일을 넣어주세요")
    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-chip">
                <div class="label">약국 OTC</div>
                <div class="value" style="color:{L1_PHARMACY};">~2주 선행</div>
                <div class="sub">p &lt; 0.05 · Granger 유의</div>
            </div>
            <div class="stat-chip">
                <div class="label">하수 바이오마커</div>
                <div class="value" style="color:{L2_SEWAGE};">~3주 선행</div>
                <div class="sub">p &lt; 0.05 · Granger 유의</div>
            </div>
            <div class="stat-chip">
                <div class="label">검색어 트렌드</div>
                <div class="value" style="color:{L3_SEARCH};">~1주 선행</div>
                <div class="sub">p &lt; 0.05 · Granger 유의</div>
            </div>
        </div>
        <div class="highlight-row" style="text-align:center;">
            ✅ 3개 Layer 모두 통계적으로 유의한 선행 지표 — 우연이 아닌 데이터 근거 (All p-values &lt; 0.05)
        </div>
        """,
        unsafe_allow_html=True,
    )
