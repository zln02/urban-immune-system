"""이미지 카드 렌더링."""

from __future__ import annotations

import os

import streamlit as st

from src.utils import asset_path


def render_image_card(filename: str, fallback_text: str) -> None:
    image_file = asset_path(filename)
    if os.path.exists(image_file):
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.image(image_file, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info(fallback_text)
