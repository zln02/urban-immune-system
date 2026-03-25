"""사이드바 렌더링."""

from __future__ import annotations

import streamlit as st

from src.config import REGIONS


def render_sidebar() -> tuple[str, str, int, bool]:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-header">
                <div class="org-name">질병관리청 연계 · AI 감시 시스템</div>
                <div class="sys-name">🏥 Urban Immune System</div>
                <div class="version">v3.0 — CDC-grade Surveillance Console</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        region = st.selectbox("감시 지역", REGIONS)
        season = st.selectbox(
            "분석 시즌",
            [
                "2024-25 절기 (2024.09~2025.03)",
                "2023-24 절기 (2023.09~2024.03)",
            ],
        )

        st.divider()
        st.markdown("**경보 설정**")
        threshold = st.slider(
            "임계값 (percentile)",
            50,
            95,
            80,
            help="이 백분위 이상이면 경보 발령",
        )
        show_train = st.checkbox("Train/Test 분할선 표시", value=True)

        st.divider()
        st.markdown("**데이터 소스 연동**")
        st.markdown(
            """
            <div class="source-tag"><span class="dot"></span>네이버 쇼핑인사이트 API</div>
            <div class="source-tag"><span class="dot"></span>KOWAS 하수감시소식지</div>
            <div class="source-tag"><span class="dot"></span>네이버 데이터랩 API</div>
            <div class="source-tag"><span class="dot"></span>KDCA 감염병포털</div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("© 2026 Urban Immune System · LG전자 DX School 13회차")

        st.markdown(
            """
            <div class="sidebar-team">
                <div class="team-title">팀 구성원</div>
                <div class="sidebar-member">
                    <span class="s-badge">총괄 · AI</span>
                    <div class="s-info">
                        <div class="s-name">박진영</div>
                        <div class="s-dept">컴퓨터공학과</div>
                    </div>
                </div>
                <div class="sidebar-member">
                    <span class="s-badge">분석</span>
                    <div class="s-info">
                        <div class="s-name">윤재영</div>
                        <div class="s-dept">정보통신공학과</div>
                    </div>
                </div>
                <div class="sidebar-member">
                    <span class="s-badge">개발</span>
                    <div class="s-info">
                        <div class="s-name">정욱현</div>
                        <div class="s-dept">정보통신공학과</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return region, season, threshold, show_train
