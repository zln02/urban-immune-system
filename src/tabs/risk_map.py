"""위험도 지도 탭."""
from __future__ import annotations

import streamlit as st
from streamlit_folium import st_folium

from src.api_client import get_current_alert
from src.map.builder import build_map


def render_map_tab(region: str) -> None:
    st.markdown("#### 서울시 구별 감염병 위험도 현황")

    # Try API for current alert
    alert = get_current_alert(region)
    if alert and alert.get("composite_score") is not None:
        level = alert["alert_level"]
        score = alert["composite_score"]
        color_map = {"GREEN": "🟢", "YELLOW": "🟡", "ORANGE": "🟠", "RED": "🔴"}
        st.markdown(f"**현재 경보**: {color_map.get(level, '⚪')} {level} (종합점수: {score})")
        if alert.get("l1_score") is not None:
            cols = st.columns(3)
            cols[0].metric("L1 약국 OTC", f"{alert['l1_score']:.1f}")
            cols[1].metric("L2 하수도", f"{alert['l2_score']:.1f}")
            cols[2].metric("L3 검색어", f"{alert['l3_score']:.1f}")

    st_folium(build_map(region), width=None, height=500, returned_objects=[])
    st.markdown(
        """
        <div class="legend-row">
            <div class="legend-item"><div class="swatch" style="background:#16a34a;"></div>Level 1 낮음</div>
            <div class="legend-item"><div class="swatch" style="background:#ca8a04;"></div>Level 2 주의</div>
            <div class="legend-item"><div class="swatch" style="background:#ea580c;"></div>Level 3 경계</div>
            <div class="legend-item"><div class="swatch" style="background:#dc2626;"></div>Level 4 심각</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
