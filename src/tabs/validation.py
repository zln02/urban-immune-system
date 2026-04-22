"""교차검증 탭 — 실측 JSON 로드 기반 (하드코딩 제거, 2026-04 P0)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.utils import asset_path

VALIDATION_JSON = Path(__file__).resolve().parents[2] / "ml" / "outputs" / "validation.json"

_MODEL_LABEL = {
    "pharmacy_only": "약국 단독",
    "sewage_only": "하수 단독",
    "search_only": "검색 단독",
    "three_layer_ensemble": "3-Layer 통합 (Ours)",
}


def _load_validation() -> dict | None:
    if not VALIDATION_JSON.exists():
        return None
    try:
        return json.loads(VALIDATION_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def render_validation_tab() -> None:
    st.markdown("#### 단일 Layer vs 3-Layer 교차검증")
    data = _load_validation()

    if data is None:
        st.warning(
            "📁 `ml/outputs/validation.json` 이 없습니다. "
            "`python analysis/notebooks/performance_measurement.py` 로 재현 가능한 수치를 생성하세요."
        )
        return

    # 데이터 원천·재현성 표시 (심사위원 질의 대응)
    st.caption(
        f"🕐 측정: {data.get('generated_at', 'N/A')}  ·  "
        f"데이터: {data.get('data_source', 'N/A')}  ·  "
        f"재현: `{data.get('script', 'N/A')}`"
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**경보 정확도 비교 (Test Set)**")
        img8 = asset_path("slide8_comparison.png")
        if os.path.exists(img8):
            st.image(img8, width="stretch")
        else:
            st.info("📁 `slide8_comparison.png` 는 분석 노트북에서 생성 예정")
    with right:
        st.markdown("**Deng 2-Layer vs 우리 3-Layer**")
        img9 = asset_path("slide9_deng_comparison.png")
        if os.path.exists(img9):
            st.image(img9, width="stretch")
        else:
            st.info("📁 `slide9_deng_comparison.png` 는 분석 노트북에서 생성 예정")

    st.markdown("<br>", unsafe_allow_html=True)

    rows = []
    for m in data.get("models", []):
        rows.append(
            {
                "모델": _MODEL_LABEL.get(m["model"], m["model"]),
                "Precision": f"{m['precision']:.3f}",
                "Recall": f"{m['recall']:.3f}",
                "F1": f"{m['f1']:.3f}",
                "MCC": f"{m['mcc']:.3f}",
                "AUPRC": f"{m['auprc']:.3f}",
                "오경보 (FP)": f"{m['false_alarms']}건",
                "임계값": f"{m['threshold']:.1f}",
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    # 3-Layer 앙상블 결과
    main = next((m for m in data["models"] if m["model"] == "three_layer_ensemble"), None)
    if main:
        st.markdown(
            f"""
            <div class="highlight-row">
                <strong>📊 3-Layer 통합 성능 (N={main['n_test']}주, 경보 이벤트 {main['n_positive_truth']}건):</strong><br>
                F1={main['f1']:.3f}  ·  MCC={main['mcc']:.3f}  ·  AUPRC={main['auprc']:.3f}  ·  오경보 {main['false_alarms']}건<br>
                <em>⚠️ 현재 합성 데이터 기반. KDCA ILINet 실데이터 확보 후 재실행 예정 (P1 멀티시즌).</em>
            </div>
            """,
            unsafe_allow_html=True,
        )
