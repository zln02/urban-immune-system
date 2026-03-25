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
    result_data = {
        "모델": [
            "약국 단독",
            "하수 단독",
            "검색 단독",
            "3-Layer 통합",
            "Deng 2-Layer (선행연구)",
            "Urban Immune System (Ours)",
        ],
        "Precision": ["0.00", "1.00", "0.67", "1.00", "1.00", "1.00"],
        "Recall": ["0.00", "0.44", "0.22", "0.56", "0.56", "0.56"],
        "F1-Score": ["0.00", "0.62", "0.33", "0.71", "0.71", "0.71"],
        "오경보": ["0건", "0건", "2건", "0건", "0건", "0건"],
    }
    st.dataframe(pd.DataFrame(result_data), width="stretch", hide_index=True)
    st.markdown(
        """
        <div class="highlight-row">
            <strong>핵심 결론:</strong> 3-Layer = Deng 2-Layer 동일 F1 (0.71) + 오경보 0건.
            약국 Layer가 노이즈 없는 안전망 역할 → 시즌·지역 변화에 대한 견고성 확보
        </div>
        """,
        unsafe_allow_html=True,
    )
