"""푸터 렌더링."""

from __future__ import annotations

import streamlit as st

from src.config import NAVY


def render_footer() -> None:
    st.markdown(
        f"""
        <div class="gov-footer">
            <strong style="color:{NAVY};">Urban Immune System</strong> v3.0 — CDC-grade Surveillance Console<br>
            AI 기반 감염병 조기경보 서비스 · 3-Layer 교차검증 (약국 OTC · 하수 바이오마커 · 검색 트렌드)<br>
            데이터 제공: 질병관리청(KDCA) · 환경부(KOWAS) · 네이버 데이터랩/쇼핑인사이트<br>
            AI 모델: LightGBM · TFT · Autoencoder · RAG-LLM (GPT-4o / Claude Sonnet 4.6)<br>
            <span style="opacity:0.7;font-size:0.82rem;">Powered by 2026 AI 아이디어 공모전 대상 수상 연구 · © 2026 Urban Immune System</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
