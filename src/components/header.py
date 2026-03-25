"""헤더와 KPI 컴포넌트."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.config import GREEN_SAFE, L1_PHARMACY, L2_SEWAGE, L3_SEARCH, ORANGE, RED


def render_header(region: str) -> None:
    now_label = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"""
        <div class="gov-header">
            <div>
                <h1>Urban Immune System</h1>
                <div class="sub">AI 감염병 조기경보 시스템 · {region} · {now_label} 기준</div>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
                <span class="badge">PROTOTYPE</span>
                <span class="badge">v3.0</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_alert_banner(region: str, threshold: int) -> None:
    level = "4" if threshold <= 80 else "3"
    level_label = "Level 4 (심각)" if level == "4" else "Level 3 (경계)"
    alert_class = "level-4" if level == "4" else "level-3"
    urgency = "즉시 대응 필요" if level == "4" else "집중 모니터링 필요"
    st.markdown(
        f"""
        <div class="alert-banner {alert_class}">
            <span style="font-size:1.2rem;">⚠️</span>
            <span>감염병 경보 {level_label} — {region} · 인플루엔자 A 확산 초기 징후 감지 · {urgency}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis() -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{RED};"></div>
                <div class="kpi-label">현재 위험도</div>
                <div class="kpi-value danger">Level 4</div>
                <div class="kpi-delta up">▲ 2단계 상승</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{L1_PHARMACY};"></div>
                <div class="kpi-label">약국 OTC 구매지수</div>
                <div class="kpi-value pharmacy">72.5</div>
                <div class="kpi-delta up">+180% 전주 대비</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{L2_SEWAGE};"></div>
                <div class="kpi-label">하수 바이러스 농도</div>
                <div class="kpi-value sewage">4.2×10³</div>
                <div class="kpi-delta up">+150% 전주 대비</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{L3_SEARCH};"></div>
                <div class="kpi-label">검색 트렌드 지수</div>
                <div class="kpi-value search">89.3</div>
                <div class="kpi-delta up">+190% 전주 대비</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
