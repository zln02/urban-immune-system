"""전역 스타일 주입."""

from __future__ import annotations

from src.config import (
    GRAY_100,
    GRAY_200,
    GRAY_300,
    GRAY_50,
    GRAY_500,
    GRAY_700,
    GRAY_900,
    GREEN_SAFE,
    L1_PHARMACY,
    L2_SEWAGE,
    L3_SEARCH,
    NAVY,
    NAVY_LIGHT,
    ORANGE,
    RED,
    WHITE,
    YELLOW,
)


def inject_styles() -> str:
    return f"""
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

    .team-watermark {{
        margin-top: 16px;
        padding-top: 12px;
        border-top: 1px solid {GRAY_200};
        display: flex;
        justify-content: center;
        gap: 24px;
        flex-wrap: wrap;
    }}

    .team-member {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
    }}

    .team-member .member-name {{
        font-weight: 700;
        font-size: 0.78rem;
        color: {NAVY};
    }}

    .team-member .member-dept {{
        font-size: 0.68rem;
        color: {GRAY_500};
    }}

    .team-member .member-role {{
        font-size: 0.7rem;
        color: {NAVY_LIGHT};
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 4px;
        padding: 1px 6px;
        font-weight: 600;
    }}

    .sidebar-team {{
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid {GRAY_200};
    }}

    .sidebar-team .team-title {{
        font-size: 0.68rem;
        color: {GRAY_500};
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
        margin-bottom: 8px;
    }}

    .sidebar-member {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }}

    .sidebar-member .s-badge {{
        background: {NAVY};
        color: white;
        font-size: 0.62rem;
        padding: 1px 6px;
        border-radius: 3px;
        font-weight: 700;
        white-space: nowrap;
    }}

    .sidebar-member .s-info {{
        font-size: 0.75rem;
        color: {GRAY_700};
    }}

    .sidebar-member .s-name {{
        font-weight: 700;
        color: {GRAY_900};
    }}

    .sidebar-member .s-dept {{
        font-size: 0.68rem;
        color: {GRAY_500};
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
    """
