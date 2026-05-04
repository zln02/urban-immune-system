"""시계열 탭."""
from __future__ import annotations

import logging

import streamlit as st

from src.api_client import get_latest_signals
from src.components.image_card import render_image_card
from src.config import L1_PHARMACY, L2_SEWAGE, L3_SEARCH, RED

logger = logging.getLogger(__name__)


def render_timeseries_tab(show_train: bool) -> None:
    st.markdown("#### 3-Layer 시계열 트렌드 vs 확진자 수")

    # Try API data first
    api_data = get_latest_signals()
    if api_data and api_data.get("count", 0) > 0:
        st.success(f"실데이터 연결됨 — {api_data['count']}건 조회")
        import pandas as pd
        df = pd.DataFrame(api_data["data"])
        if not df.empty and "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
            for layer, color, label in [
                ("L1", L1_PHARMACY, "약국 OTC"),
                ("L2", L2_SEWAGE, "하수 바이오마커"),
                ("L3", L3_SEARCH, "검색어 트렌드"),
            ]:
                layer_df = df[df["layer"] == layer]
                if not layer_df.empty:
                    st.line_chart(layer_df.set_index("time")["value"], color=color)
                    st.caption(f"{label} (최근 {len(layer_df)}건)")
    else:
        # Simulation fallback
        render_image_card("slide6_timeseries.png", "📁 `assets/slide6_timeseries.png` 파일을 넣어주세요")
        st.info("API 미연결 — 시뮬레이션 데이터 표시 중")

    if show_train:
        st.caption("Train/Test 분할선 표시 옵션이 활성화되어 있다고 가정한 리포트 뷰입니다.")
    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-chip">
                <div class="label">약국 OTC</div>
                <div class="value" style="color:{L1_PHARMACY};">~2주 선행</div>
                <div class="sub">피크 시즌 최강 신호</div>
            </div>
            <div class="stat-chip">
                <div class="label">하수 바이오마커</div>
                <div class="value" style="color:{L2_SEWAGE};">~3주 선행</div>
                <div class="sub">가장 이른 감지</div>
            </div>
            <div class="stat-chip">
                <div class="label">검색어 트렌드</div>
                <div class="value" style="color:{L3_SEARCH};">~1주 선행</div>
                <div class="sub">실시간 반응 최고</div>
            </div>
            <div class="stat-chip">
                <div class="label">확진자 수 (기준선)</div>
                <div class="value" style="color:{RED};">Ground Truth</div>
                <div class="sub">KDCA 감염병포털</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
