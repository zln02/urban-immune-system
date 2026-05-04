"""교차검증 탭."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src.utils import asset_path


def render_validation_tab() -> None:
    st.markdown("#### 단일 Layer vs 3-Layer 교차검증")
    left, right = st.columns(2)
    with left:
        st.markdown("**경보 정확도 비교 (Test Set)**")
        img8 = asset_path("slide8_comparison.png")
        if os.path.exists(img8):
            st.image(img8, width="stretch")
        else:
            st.info("📁 `assets/slide8_comparison.png`")
    with right:
        st.markdown("**Deng 2-Layer vs 우리 3-Layer**")
        img9 = asset_path("slide9_deng_comparison.png")
        if os.path.exists(img9):
            st.image(img9, width="stretch")
        else:
            st.info("📁 `assets/slide9_deng_comparison.png`")

    st.markdown("<br>", unsafe_allow_html=True)
    # 17개 시·도 walk-forward 백테스트 (2025-2026 인플루엔자 시즌)
    # 출처: analysis/outputs/backtest_17regions.json
    result_data = {
        "지표": [
            "Precision",
            "Recall",
            "F1-Score",
            "False Alarm Rate",
            "Lead Time (주)",
        ],
        "3-Layer 통합 (17개 시·도 평균)": [
            "0.96",
            "0.77",
            "0.84",
            "0.16",
            "5.9",
        ],
    }
    st.dataframe(pd.DataFrame(result_data), width="stretch", hide_index=True)
    st.markdown(
        """
        <div class="highlight-row">
            <strong>핵심 결론:</strong> 17개 시·도 walk-forward 백테스트(n=1,020)에서
            F1=0.84 / Precision=0.96 / FAR=0.16 / 평균 lead time 5.9주.
            출처: <code>analysis/outputs/backtest_17regions.json</code>
        </div>
        """,
        unsafe_allow_html=True,
    )
