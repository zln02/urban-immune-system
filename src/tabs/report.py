"""리포트 탭."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.config import GRAY_500, GREEN_SAFE, L1_PHARMACY, L2_SEWAGE, L3_SEARCH, ORANGE, RED


def render_report_tab(region: str) -> None:
    issued_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown("#### RAG-LLM 자동 경보 리포트")
    st.markdown(
        f"""
        <div class="report-card">
            <div class="report-header">
                <h3>⚠️ 감염병 조기경보 — {region}</h3>
                <p>발령: {issued_at} · 위험도: Level 4 (심각) · 예상 감염병: 인플루엔자 A</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Layer별 TFT Attention 기여도**")
    st.markdown(
        f"""
        <div class="layer-indicator">
            <div class="dot pharmacy"></div>
            <div class="info">
                <div class="name">Layer 1 — 약국 OTC 구매지수</div>
                <div class="desc">해열제 구매 +180% · 피크 시즌 최강 신호</div>
            </div>
            <div class="metric">
                <div class="val" style="color:{L1_PHARMACY};">68%</div>
                <div class="unit">Attention</div>
            </div>
        </div>
        <div class="layer-indicator">
            <div class="dot sewage"></div>
            <div class="info">
                <div class="name">Layer 2 — 하수 바이오마커</div>
                <div class="desc">인플루엔자A 4.2×10³ copies/mL · 무증상자 포함 감지</div>
            </div>
            <div class="metric">
                <div class="val" style="color:{L2_SEWAGE};">24%</div>
                <div class="unit">Attention</div>
            </div>
        </div>
        <div class="layer-indicator">
            <div class="dot search"></div>
            <div class="info">
                <div class="name">Layer 3 — 검색 트렌드</div>
                <div class="desc">"고열 병원" 검색 89.3 · 실시간 반응</div>
            </div>
            <div class="metric">
                <div class="val" style="color:{L3_SEARCH};">8%</div>
                <div class="unit">Attention</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**AI 생성 상황 분석**")
    st.markdown(
        f"""
        <div class="report-card">
            <strong>{region}에서 인플루엔자 A 확산 초기 징후가 감지되었습니다.</strong>
            <br><br>
            2024년 동절기 유사 패턴(KOWAS 2024-W48) 대비 확산 속도가 <strong style="color:{RED};">1.3배</strong> 빠르며,
            현재 기온(2°C)·습도(35%) 조건이 비말 전파에 유리합니다.
            <br><br>
            <div class="recommend-box">
                <strong>대응 권고안</strong><br><br>
                ① 고위험군(65세 이상) 대상 <strong>선제 백신 접종</strong> 권고<br>
                ② 관내 의료기관 <strong>항바이러스제 재고</strong> 확인 (오셀타미비르 3주분)<br>
                ③ 학교·어린이집 <strong>방역 강화</strong> 및 발열 모니터링 가동
            </div>
            <br>
            <span style="color:{GRAY_500}; font-size:0.8rem;">
                참조: CDC 가이드라인 · KOWAS 주간 보고 · Deng et al. (2026, Engineering)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**TFT 확산 예측 (Multi-Horizon)**")
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{ORANGE};"></div>
                <div class="kpi-label">7일 후 예측</div>
                <div class="kpi-value" style="color:{ORANGE};">+45%</div>
                <div class="kpi-delta up">급증 예상</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pc2:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{RED};"></div>
                <div class="kpi-label">14일 후 (피크)</div>
                <div class="kpi-value danger">+120%</div>
                <div class="kpi-delta up">피크 도달 예상</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pc3:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{GREEN_SAFE};"></div>
                <div class="kpi-label">21일 후</div>
                <div class="kpi-value" style="color:{GREEN_SAFE};">+80%</div>
                <div class="kpi-delta down">감소 전환 예상</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
