import os
from datetime import datetime

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Urban Immune System — AI 감염병 조기경보",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


NAVY = "#1e3a5f"
NAVY_LIGHT = "#2c5282"
SLATE = "#334155"
GRAY_50 = "#f8fafc"
GRAY_100 = "#f1f5f9"
GRAY_200 = "#e2e8f0"
GRAY_300 = "#cbd5e1"
GRAY_500 = "#64748b"
GRAY_700 = "#334155"
GRAY_900 = "#0f172a"
WHITE = "#ffffff"
RED = "#dc2626"
ORANGE = "#ea580c"
YELLOW = "#ca8a04"
GREEN_SAFE = "#16a34a"
L1_PHARMACY = "#be185d"
L2_SEWAGE = "#047857"
L3_SEARCH = "#1d4ed8"

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
REGIONS = [
    "서울 강남구",
    "서울 송파구",
    "서울 강서구",
    "서울 마포구",
    "서울 영등포구",
    "서울 서초구",
    "서울 중랑구",
    "서울 관악구",
    "서울 구로구",
]
DISTRICTS = [
    {"name": "강남구", "lat": 37.5172, "lon": 127.0473, "risk": 4},
    {"name": "송파구", "lat": 37.5145, "lon": 127.1059, "risk": 3},
    {"name": "강서구", "lat": 37.5509, "lon": 126.8495, "risk": 2},
    {"name": "마포구", "lat": 37.5663, "lon": 126.9014, "risk": 3},
    {"name": "영등포구", "lat": 37.5264, "lon": 126.8963, "risk": 2},
    {"name": "서초구", "lat": 37.4837, "lon": 127.0324, "risk": 4},
    {"name": "용산구", "lat": 37.5326, "lon": 126.9909, "risk": 1},
    {"name": "종로구", "lat": 37.5735, "lon": 126.9790, "risk": 2},
    {"name": "중구", "lat": 37.5641, "lon": 126.9979, "risk": 1},
    {"name": "성동구", "lat": 37.5634, "lon": 127.0369, "risk": 3},
    {"name": "광진구", "lat": 37.5385, "lon": 127.0824, "risk": 2},
    {"name": "동대문구", "lat": 37.5744, "lon": 127.0397, "risk": 2},
    {"name": "중랑구", "lat": 37.6063, "lon": 127.0928, "risk": 3},
    {"name": "성북구", "lat": 37.5894, "lon": 127.0167, "risk": 2},
    {"name": "강북구", "lat": 37.6397, "lon": 127.0255, "risk": 1},
    {"name": "도봉구", "lat": 37.6688, "lon": 127.0472, "risk": 1},
    {"name": "노원구", "lat": 37.6542, "lon": 127.0568, "risk": 2},
    {"name": "은평구", "lat": 37.6027, "lon": 126.9291, "risk": 1},
    {"name": "서대문구", "lat": 37.5791, "lon": 126.9368, "risk": 2},
    {"name": "양천구", "lat": 37.5170, "lon": 126.8666, "risk": 2},
    {"name": "구로구", "lat": 37.4954, "lon": 126.8878, "risk": 3},
    {"name": "금천구", "lat": 37.4519, "lon": 126.8955, "risk": 2},
    {"name": "동작구", "lat": 37.5124, "lon": 126.9393, "risk": 2},
    {"name": "관악구", "lat": 37.4784, "lon": 126.9516, "risk": 3},
    {"name": "강동구", "lat": 37.5301, "lon": 127.1238, "risk": 2},
]
RISK_CFG = {
    1: {"color": GREEN_SAFE, "label": "Level 1 (낮음)", "radius": 8},
    2: {"color": YELLOW, "label": "Level 2 (주의)", "radius": 12},
    3: {"color": ORANGE, "label": "Level 3 (경계)", "radius": 16},
    4: {"color": RED, "label": "Level 4 (심각)", "radius": 22},
}


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

        .stApp {{
            background-color: {GRAY_50};
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        html, body, [class*="css"] {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1440px;
        }}

        [data-testid="stSidebar"] {{
            background-color: {WHITE};
            border-right: 1px solid {GRAY_200};
        }}

        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
            color: {GRAY_900} !important;
            font-family: 'Pretendard', sans-serif;
        }}

        .stApp p, .stApp li {{
            color: {GRAY_700};
        }}

        .gov-header {{
            background: {NAVY};
            color: {WHITE};
            padding: 16px 24px;
            border-radius: 0;
            margin: -1rem -1rem 24px -1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }}

        .gov-header h1 {{
            color: {WHITE} !important;
            font-size: 1.4rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.3px;
        }}

        .gov-header h1 span,
        .gov-header .sub,
        .gov-header .badge {{
            color: {WHITE} !important;
        }}

        .gov-header .sub {{
            color: rgba(255,255,255,0.74);
            font-size: 0.8rem;
            margin-top: 4px;
        }}

        .gov-header .badge {{
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.25);
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.75rem;
            color: {WHITE};
            font-weight: 600;
        }}

        .gov-header [data-testid="stHeaderActionElements"] {{
            display: none;
        }}

        .alert-banner {{
            padding: 12px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 600;
            font-size: 0.9rem;
        }}

        .alert-banner.level-4 {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-left: 4px solid {RED};
            color: {RED};
        }}

        .alert-banner.level-3 {{
            background: #fff7ed;
            border: 1px solid #fed7aa;
            border-left: 4px solid {ORANGE};
            color: {ORANGE};
        }}

        .alert-banner.level-2 {{
            background: #fefce8;
            border: 1px solid #fef08a;
            border-left: 4px solid {YELLOW};
            color: {YELLOW};
        }}

        .alert-banner.level-1 {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-left: 4px solid {GREEN_SAFE};
            color: {GREEN_SAFE};
        }}

        .kpi-flat {{
            background: {WHITE};
            border: 1px solid {GRAY_200};
            border-radius: 8px;
            padding: 20px;
            text-align: left;
            position: relative;
            min-height: 142px;
        }}

        .kpi-flat .kpi-label {{
            font-size: 0.75rem;
            color: {GRAY_500};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            font-weight: 600;
        }}

        .kpi-flat .kpi-value {{
            font-size: 1.8rem;
            font-weight: 800;
            color: {GRAY_900};
            line-height: 1.2;
            letter-spacing: -0.5px;
        }}

        .kpi-flat .kpi-value.danger {{ color: {RED}; }}
        .kpi-flat .kpi-value.pharmacy {{ color: {L1_PHARMACY}; }}
        .kpi-flat .kpi-value.sewage {{ color: {L2_SEWAGE}; }}
        .kpi-flat .kpi-value.search {{ color: {L3_SEARCH}; }}

        .kpi-flat .kpi-delta {{
            font-size: 0.8rem;
            margin-top: 4px;
            font-weight: 600;
        }}

        .kpi-flat .kpi-delta.up {{ color: {RED}; }}
        .kpi-flat .kpi-delta.down {{ color: {GREEN_SAFE}; }}

        .kpi-flat .kpi-bar {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            border-radius: 8px 8px 0 0;
        }}

        .section-card {{
            background: {WHITE};
            border: 1px solid {GRAY_200};
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 16px;
        }}

        .section-card h4 {{
            font-size: 0.9rem;
            font-weight: 700;
            color: {NAVY} !important;
            margin: 0 0 16px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid {NAVY};
            display: inline-block;
        }}

        .layer-indicator {{
            background: {WHITE};
            border: 1px solid {GRAY_200};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .layer-indicator .dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .layer-indicator .dot.pharmacy {{ background: {L1_PHARMACY}; }}
        .layer-indicator .dot.sewage {{ background: {L2_SEWAGE}; }}
        .layer-indicator .dot.search {{ background: {L3_SEARCH}; }}

        .layer-indicator .info {{
            flex: 1;
        }}

        .layer-indicator .info .name {{
            font-weight: 700;
            font-size: 0.85rem;
            color: {GRAY_900};
        }}

        .layer-indicator .info .desc {{
            font-size: 0.8rem;
            color: {GRAY_500};
            margin-top: 2px;
        }}

        .layer-indicator .metric {{
            text-align: right;
        }}

        .layer-indicator .metric .val {{
            font-size: 1.3rem;
            font-weight: 800;
            color: {GRAY_900};
        }}

        .layer-indicator .metric .unit {{
            font-size: 0.7rem;
            color: {GRAY_500};
        }}

        .report-card {{
            background: {WHITE};
            border: 1px solid {GRAY_200};
            border-radius: 8px;
            padding: 24px;
            line-height: 1.8;
            color: {GRAY_700};
        }}

        .report-card .report-header {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 6px;
            padding: 16px 20px;
            margin-bottom: 20px;
        }}

        .report-card .report-header h3 {{
            color: {RED} !important;
            margin: 0 0 4px 0;
            font-size: 1rem;
        }}

        .report-card .report-header p {{
            color: {GRAY_500};
            margin: 0;
            font-size: 0.85rem;
        }}

        .report-card .recommend-box {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-left: 3px solid {GREEN_SAFE};
            border-radius: 0 6px 6px 0;
            padding: 16px 20px;
            margin: 16px 0;
        }}

        .report-card .recommend-box strong {{
            color: {GREEN_SAFE};
        }}

        .highlight-row {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 6px;
            padding: 12px 16px;
            margin: 8px 0;
            font-weight: 600;
            color: {NAVY};
            font-size: 0.9rem;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 0;
            border-bottom: 2px solid {GRAY_200};
            background: transparent;
            padding: 0;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 0;
            color: {GRAY_500};
            font-weight: 600;
            padding: 10px 20px;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
        }}

        .stTabs [data-baseweb="tab"] p {{
            color: inherit;
            font-weight: inherit;
        }}

        .stTabs [aria-selected="true"] {{
            background: transparent !important;
            color: {NAVY} !important;
            border-bottom: 2px solid {NAVY} !important;
        }}

        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stSlider label,
        [data-testid="stSidebar"] .stCheckbox label {{
            color: {GRAY_700} !important;
            font-weight: 600;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-baseweb="base-input"] > div,
        [data-testid="stSidebar"] [data-baseweb="slider"] > div > div {{
            background: {WHITE};
            border-color: {GRAY_300};
            color: {GRAY_900};
        }}

        [data-testid="stSidebar"] [role="slider"] {{
            background: {NAVY};
        }}

        .sidebar-header {{
            padding: 16px 0;
            border-bottom: 1px solid {GRAY_200};
            margin-bottom: 20px;
        }}

        .sidebar-header .org-name {{
            font-size: 0.7rem;
            color: {GRAY_500};
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 700;
        }}

        .sidebar-header .sys-name {{
            font-size: 1.1rem;
            font-weight: 800;
            color: {NAVY};
            margin: 4px 0;
        }}

        .sidebar-header .version {{
            font-size: 0.7rem;
            color: {GRAY_500};
        }}

        .source-tag {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 0.78rem;
            color: {GRAY_700};
            background: {GRAY_100};
            border: 1px solid {GRAY_200};
            margin: 3px 0;
            width: 100%;
        }}

        .source-tag .dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: {GREEN_SAFE};
        }}

        .legend-row {{
            display: flex;
            gap: 16px;
            justify-content: center;
            margin-top: 12px;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.8rem;
            color: {GRAY_700};
            font-weight: 500;
        }}

        .legend-item .swatch {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }}

        .gov-footer {{
            text-align: center;
            color: {GRAY_500};
            font-size: 0.75rem;
            padding: 24px 0 16px;
            border-top: 1px solid {GRAY_200};
            margin-top: 40px;
            line-height: 1.8;
        }}

        .stat-row {{
            display: flex;
            gap: 12px;
            margin: 16px 0;
            flex-wrap: wrap;
        }}

        .stat-chip {{
            flex: 1 1 180px;
            background: {WHITE};
            border: 1px solid {GRAY_200};
            border-radius: 6px;
            padding: 14px 16px;
            text-align: center;
        }}

        .stat-chip .label {{
            color: {GRAY_500};
            font-size: 0.72rem;
            margin-bottom: 6px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .stat-chip .value {{
            color: {GRAY_900};
            font-size: 1.05rem;
            font-weight: 800;
        }}

        .stat-chip .sub {{
            color: {GRAY_500};
            font-size: 0.78rem;
            margin-top: 4px;
        }}

        div[data-testid="stDataFrame"] {{
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid {GRAY_200};
        }}

        .stApp [data-testid="stHeader"] {{
            background: transparent;
        }}

        @media (max-width: 900px) {{
            .gov-header {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .kpi-flat {{
                min-height: unset;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def asset_path(filename: str) -> str:
    return os.path.join(ASSETS_DIR, filename)


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

    return region, season, threshold, show_train


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


def build_map(region: str) -> folium.Map:
    selected_name = region.replace("서울 ", "")
    fmap = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="CartoDB positron")

    for district in DISTRICTS:
        cfg = RISK_CFG[district["risk"]]
        otc_status = "▲ 급증" if district["risk"] >= 3 else "— 정상"
        sewage_status = "▲ 양성" if district["risk"] >= 3 else "— 정상"
        search_status = "▲ 급증" if district["risk"] >= 2 else "— 정상"
        weight = 3 if district["name"] == selected_name else 2
        fill_opacity = 0.55 if district["name"] == selected_name else 0.4

        popup_html = (
            "<div style='font-family:Pretendard,sans-serif;'>"
            f"<b style='font-size:14px;'>{district['name']}</b><br>"
            f"<span style='color:{cfg['color']};font-weight:bold;'>{cfg['label']}</span><br>"
            "<hr style='margin:4px 0;border-color:#e2e8f0;'>"
            f"약국 OTC: {otc_status}<br>"
            f"하수 검출: {sewage_status}<br>"
            f"검색 트렌드: {search_status}"
            "</div>"
        )

        folium.CircleMarker(
            location=[district["lat"], district["lon"]],
            radius=cfg["radius"],
            color=cfg["color"],
            fill=True,
            fill_color=cfg["color"],
            fill_opacity=fill_opacity,
            weight=weight,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{district['name']} — {cfg['label']}",
        ).add_to(fmap)

    return fmap


def render_map_tab(region: str) -> None:
    st.markdown("#### 서울시 구별 감염병 위험도 현황")
    st_folium(build_map(region), width=None, height=500, returned_objects=[])
    st.markdown(
        """
        <div class="legend-row">
            <div class="legend-item"><div class="swatch" style="background:#16a34a;"></div>Level 1 낮음</div>
            <div class="legend-item"><div class="swatch" style="background:#ca8a04;"></div>Level 2 주의</div>
            <div class="legend-item"><div class="swatch" style="background:#ea580c;"></div>Level 3 경계</div>
            <div class="legend-item"><div class="swatch" style="background:#dc2626;"></div>Level 4 심각</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_image_card(filename: str, fallback_text: str) -> None:
    image_file = asset_path(filename)
    if os.path.exists(image_file):
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.image(image_file, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info(fallback_text)


def render_timeseries_tab(show_train: bool) -> None:
    st.markdown("#### 3-Layer 시계열 트렌드 vs 확진자 수")
    render_image_card("slide6_timeseries.png", "📁 `assets/slide6_timeseries.png` 파일을 넣어주세요")
    if show_train:
        st.caption("Train/Test 분할선 표시 옵션이 활성화되어 있다고 가정한 리포트 뷰입니다.")
    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-chip">
                <div class="label">약국 OTC</div>
                <div class="value" style="color:{L1_PHARMACY};">~2주 선행</div>
                <div class="sub">피크 시즌 최강 신호</div>
            </div>
            <div class="stat-chip">
                <div class="label">하수 바이오마커</div>
                <div class="value" style="color:{L2_SEWAGE};">~3주 선행</div>
                <div class="sub">가장 이른 감지</div>
            </div>
            <div class="stat-chip">
                <div class="label">검색어 트렌드</div>
                <div class="value" style="color:{L3_SEARCH};">~1주 선행</div>
                <div class="sub">실시간 반응 최고</div>
            </div>
            <div class="stat-chip">
                <div class="label">확진자 수 (기준선)</div>
                <div class="value" style="color:{RED};">Ground Truth</div>
                <div class="sub">KDCA 감염병포털</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_correlation_tab() -> None:
    st.markdown("#### Cross-correlation + Granger 인과검정 결과")
    render_image_card("slide7_crosscorr.png", "📁 `assets/slide7_crosscorr.png` 파일을 넣어주세요")
    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-chip">
                <div class="label">약국 OTC</div>
                <div class="value" style="color:{L1_PHARMACY};">~2주 선행</div>
                <div class="sub">p &lt; 0.05 · Granger 유의</div>
            </div>
            <div class="stat-chip">
                <div class="label">하수 바이오마커</div>
                <div class="value" style="color:{L2_SEWAGE};">~3주 선행</div>
                <div class="sub">p &lt; 0.05 · Granger 유의</div>
            </div>
            <div class="stat-chip">
                <div class="label">검색어 트렌드</div>
                <div class="value" style="color:{L3_SEARCH};">~1주 선행</div>
                <div class="sub">p &lt; 0.05 · Granger 유의</div>
            </div>
        </div>
        <div class="highlight-row" style="text-align:center;">
            ✅ 3개 Layer 모두 통계적으로 유의한 선행 지표 — 우연이 아닌 데이터 근거 (All p-values &lt; 0.05)
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def render_footer() -> None:
    st.markdown(
        f"""
        <div class="gov-footer">
            <strong style="color:{NAVY};">Urban Immune System</strong> v3.0 — CDC-grade Surveillance Console<br>
            제1회 2026 데이터로 미래를 그리는 AI 아이디어 공모전 · LG전자 DX School 13회차<br>
            데이터: KDCA 감염병포털 · KOWAS 하수감시소식지 · 네이버 쇼핑인사이트/데이터랩<br>
            선행연구: Deng et al. (2026) Engineering — 2-Layer 하수+검색어 통합 조기경보
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    inject_styles()
    region, _, threshold, show_train = render_sidebar()
    render_header(region)
    render_alert_banner(region, threshold)
    render_kpis()
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["위험도 지도", "시계열 분석", "상관관계 검정", "교차검증", "AI 경보 리포트"]
    )

    with tab1:
        render_map_tab(region)
    with tab2:
        render_timeseries_tab(show_train)
    with tab3:
        render_correlation_tab()
    with tab4:
        render_validation_tab()
    with tab5:
        render_report_tab(region)

    render_footer()


if __name__ == "__main__":
    main()
