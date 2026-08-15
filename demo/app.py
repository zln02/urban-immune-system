"""Urban Immune System — 합성 데이터 데모.

이 앱은 저장소의 운영 코드(`pipeline/`, `ml/`, `backend/`, `src/`)를 전혀
import 하지 않는다. 같은 디렉터리의 `synthetic.py` 하나에만 의존하며,
데이터베이스·외부 API·실데이터 파일에도 접근하지 않는다.

목적은 "이 시스템이 무엇을 보여주는가"를 설치 없이 3분 안에 이해시키는 것이다.
성능 수치를 주장하지 않는다.

실행: streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from synthetic import (
    GATE_LAYER_THRESHOLD,
    GATE_MIN_LAYERS,
    LAYER_COLORS,
    LAYER_LABELS,
    LAYER_LEAD_WEEKS,
    RED_THRESHOLD,
    REGIONS,
    DemoConfig,
    build_region_frame,
    build_region_summary,
    gate_effect,
)

REPO_URL = "https://github.com/zln02/urban-immune-system"


def _banner() -> None:
    """화면 최상단 합성 데이터 고지. 어느 탭에서든 먼저 보이게 한다."""
    st.warning(
        "**⚠️ 이 화면의 모든 수치는 합성(synthetic) 데이터입니다.** "
        "실제 약국 판매·하수 검사·검색량 데이터가 아니며, 실제 감염병 위험도를 "
        "나타내지 않습니다. 방역·의료 판단에 사용할 수 없습니다. "
        f"실제 데이터로 돌리려면 [저장소]({REPO_URL})를 clone 하세요.",
        icon="⚠️",
    )


def _layer_chart(frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["week"],
            y=frame["clinical"],
            name="임상 신고 (기준선)",
            line=dict(color="#64748b", width=2, dash="dot"),
        )
    )
    for layer in ("L1", "L2", "L3"):
        fig.add_trace(
            go.Scatter(
                x=frame["week"],
                y=frame[layer],
                name=f"{LAYER_LABELS[layer]} (−{LAYER_LEAD_WEEKS[layer]}주)",
                line=dict(color=LAYER_COLORS[layer], width=2),
            )
        )
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="신호 강도 (0-100)",
        xaxis_title=None,
        hovermode="x unified",
    )
    return fig


def _composite_chart(frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["week"],
            y=frame["composite"],
            name="3계층 융합 위험도",
            line=dict(color="#1e3a5f", width=3),
            fill="tozeroy",
            fillcolor="rgba(30,58,95,0.10)",
        )
    )
    fig.add_hline(
        y=RED_THRESHOLD,
        line=dict(color="#dc2626", width=1, dash="dash"),
        annotation_text=f"경보 임계 {RED_THRESHOLD:g}",
        annotation_position="top left",
    )
    fired = frame[frame["alert"]]
    if not fired.empty:
        fig.add_trace(
            go.Scatter(
                x=fired["week"],
                y=fired["composite"],
                mode="markers",
                name="경보 발령 (게이트 통과)",
                marker=dict(color="#dc2626", size=9, symbol="triangle-up"),
            )
        )
    suppressed = frame[frame["alert_raw"] & ~frame["alert"]]
    if not suppressed.empty:
        fig.add_trace(
            go.Scatter(
                x=suppressed["week"],
                y=suppressed["composite"],
                mode="markers",
                name="게이트가 차단한 경보",
                marker=dict(
                    color="#ffffff",
                    size=9,
                    symbol="x",
                    line=dict(color="#dc2626", width=1.5),
                ),
            )
        )
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="융합 위험도",
        hovermode="x unified",
    )
    return fig


def main() -> None:
    st.set_page_config(
        page_title="Urban Immune System — 합성 데이터 데모",
        page_icon="🦠",
        layout="wide",
    )

    st.title("🦠 Urban Immune System — 데모")
    st.caption(
        "약국 OTC · 하수 바이오마커 · 검색 트렌드 3계층을 교차검증해 "
        "감염병을 선행 탐지하는 조기경보 시스템의 동작 방식 데모"
    )
    _banner()

    with st.sidebar:
        st.header("설정")
        region = st.selectbox("지역", REGIONS, index=0)
        weeks = st.slider("기간 (주)", 52, 156, 104, step=4)
        st.divider()
        st.markdown(
            f"**게이트 설정** (실제 값과 동일)\n\n"
            f"- 최소 통과 계층: `{GATE_MIN_LAYERS}`\n"
            f"- 계층 임계: `{GATE_LAYER_THRESHOLD:g}`\n"
            f"- 경보 임계: `{RED_THRESHOLD:g}`"
        )
        st.divider()
        st.link_button("전체 코드 보기 (GitHub)", REPO_URL, use_container_width=True)

    cfg = DemoConfig(weeks=weeks)
    frame = build_region_frame(region, cfg)
    latest = frame.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("종합 위험도", f"{latest['composite']:.1f}")
    c2.metric("게이트 통과 계층", f"{int(latest['gate_layers'])} / 3")
    c3.metric("경보 상태", "🔴 발령" if latest["alert"] else "🟢 정상")
    c4.metric("표시 기간", f"{weeks}주")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["3계층 신호", "융합 위험도 · 경보", "지역 현황", "이 데모의 한계"]
    )

    with tab1:
        st.subheader(f"{region} — 계층별 신호")
        st.markdown(
            "회색 점선이 임상 신고 곡선이고, 색깔 선 3개가 그보다 먼저 움직이는 "
            "비의료 신호다. 각 계층이 앞서는 정도는 저장소 README의 단독 선행 "
            "표(L1 8주 · L2 2주 · L3 3주)를 그대로 반영했다."
        )
        st.plotly_chart(_layer_chart(frame), use_container_width=True)

    with tab2:
        st.subheader(f"{region} — 3계층 융합과 게이트 로직")
        st.markdown(
            "빨간 삼각형은 실제로 발령된 경보이고, **X 표시는 임계는 넘었지만 "
            "게이트가 막은 경보**다. 단일 계층만 튀어서 생기는 오경보를 여기서 "
            "걸러낸다 — Google Flu Trends가 과대예측으로 실패한 지점이다."
        )
        st.plotly_chart(_composite_chart(frame), use_container_width=True)

        eff = gate_effect(cfg)
        g1, g2, g3 = st.columns(3)
        g1.metric("게이트 OFF 경보 수", f"{eff['gate_off']}건")
        g2.metric("게이트가 차단", f"{eff['blocked']}건")
        g3.metric("게이트 ON 경보 수", f"{eff['gate_on']}건")
        st.caption(
            "위 3개 수치는 17개 지역 합성 시계열을 합산한 것이다. "
            "**실제 성능 지표가 아니다.** 게이트가 무엇을 하는지 보여주는 용도다."
        )

    with tab3:
        st.subheader("17개 시·도 현황 (합성)")
        summary = build_region_summary(cfg)
        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "종합 위험도": st.column_config.ProgressColumn(
                    "종합 위험도", min_value=0, max_value=100, format="%.1f"
                )
            },
        )
        st.caption(
            "지역명은 실제 백테스트 대상 17개 시·도와 같지만, 값은 전부 합성이다."
        )

    with tab4:
        st.subheader("이 데모가 하지 않는 것")
        st.markdown(
            """
이 데모는 **동작 방식을 보여줄 뿐, 성능을 주장하지 않는다.**

- **실데이터를 쓰지 않는다.** 약국 판매·하수 검사·검색량 어느 것도 실제 값이
  아니다. 고정 시드로 생성한 난수 곡선이다.
- **모델이 없다.** 실제 시스템은 XGBoost 주모델과 TFT 해석성 보조를 쓰지만,
  이 데모에는 학습된 모델이 들어 있지 않다. 가중 합산만 한다.
- **여기 뜨는 경보 건수는 성능 지표가 아니다.** 합성 곡선 위에서 게이트가
  어떻게 동작하는지 보여주는 예시다.

실제 검증 결과(17개 시·도 walk-forward 백테스트)와 그 한계 — F1이 OTC
z-score self-proxy 라벨 기준이며 임상 ground truth 대비로는 일치도가 낮다는
점까지 — 는 저장소 README의 "검증 결과"와 "한계와 정직성" 절에 정리돼 있다.
숫자를 인용하려면 그쪽을 봐야 한다.
            """
        )
        st.link_button("README에서 실제 검증 결과 보기", REPO_URL, type="primary")

    st.divider()
    st.caption(
        "Urban Immune System · 합성 데이터 데모 · "
        f"전체 재현은 [저장소 clone]({REPO_URL})"
    )


if __name__ == "__main__":
    main()
