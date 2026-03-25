"""위험도 지도 탭."""

from __future__ import annotations

import streamlit as st
from streamlit_folium import st_folium

from src.map.builder import build_map


def render_map_tab(region: str) -> None:
    st.markdown("#### 서울시 구별 감염병 위험도 현황")
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
