from __future__ import annotations

import streamlit as st

from src.components.footer import render_footer
from src.components.header import render_alert_banner, render_header, render_kpis
from src.components.sidebar import render_sidebar
from src.styles import inject_styles
from src.tabs.correlation import render_correlation_tab
from src.tabs.report import render_report_tab
from src.tabs.risk_map import render_map_tab
from src.tabs.timeseries import render_timeseries_tab
from src.tabs.validation import render_validation_tab


def main() -> None:
    st.set_page_config(page_title="Urban Immune System — AI 감염병 조기경보", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")
    st.markdown(inject_styles(), unsafe_allow_html=True)
    region, _, threshold, show_train = render_sidebar()
    render_header(region)
    render_alert_banner(region, threshold)
    render_kpis()
    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["위험도 지도", "시계열 분석", "상관관계 검정", "교차검증", "AI 경보 리포트"])
    with tab1: render_map_tab(region)
    with tab2: render_timeseries_tab(show_train)
    with tab3: render_correlation_tab()
    with tab4: render_validation_tab()
    with tab5: render_report_tab(region)
    render_footer()


if __name__ == "__main__":
    main()
