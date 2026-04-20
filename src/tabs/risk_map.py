"""위험도 지도 탭."""

from __future__ import annotations

import streamlit as st
from streamlit_folium import st_folium

from src.config import RISK_CFG
from src.map.builder import build_map


def render_map_tab(region: str) -> None:
    st.markdown("#### 서울시 구별 감염병 위험도 현황")
    st_folium(build_map(region), width=None, height=500, returned_objects=[])
    # 범례는 src.config.RISK_CFG 를 단일 소스로 사용 (하드코딩 제거)
    legend_items = "".join(
        f'<div class="legend-item">'
        f'<div class="swatch" style="background:{cfg["color"]};"></div>'
        f'{cfg["label"]}'
        f"</div>"
        for _, cfg in sorted(RISK_CFG.items())
    )
    st.markdown(
        f'<div class="legend-row">{legend_items}</div>',
        unsafe_allow_html=True,
    )
