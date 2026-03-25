"""푸터 렌더링."""

from __future__ import annotations

import streamlit as st

from src.config import GRAY_500, GREEN_SAFE, NAVY, NAVY_LIGHT, ORANGE, RED


def render_footer() -> None:
    st.markdown(
        f"""
        <div class="gov-footer">
            <strong style="color:{NAVY};">Urban Immune System</strong> v3.0 — CDC-grade Surveillance Console<br>
            제1회 2026 데이터로 미래를 그리는 AI 아이디어 공모전 · LG전자 DX School 13회차<br>
            데이터: KDCA 감염병포털 · KOWAS 하수감시소식지 · 네이버 쇼핑인사이트/데이터랩<br>
            선행연구: Deng et al. (2026) Engineering — 2-Layer 하수+검색어 통합 조기경보
            <div class="team-watermark">
                <div class="team-member">
                    <div class="member-role">총괄 PM · AI 모델링</div>
                    <div class="member-name">박진영</div>
                    <div class="member-dept">컴퓨터공학과</div>
                </div>
                <div class="team-member">
                    <div class="member-role">데이터 분석</div>
                    <div class="member-name">윤재영</div>
                    <div class="member-dept">정보통신공학과</div>
                </div>
                <div class="team-member">
                    <div class="member-role">시스템 개발</div>
                    <div class="member-name">정욱현</div>
                    <div class="member-dept">정보통신공학과</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
