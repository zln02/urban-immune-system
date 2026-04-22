"""앱 전역 상수 모음."""

from __future__ import annotations

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
# ─────────────────────────────────────────────
# 경보 색상 — Okabe-Ito CUD (색맹 안전, Nature 권장)
# 2026-04-21 교체: 기존 hex 는 YELLOW 2.94:1·ORANGE 3.56:1 로 WCAG AA 실패 + 적록색맹 동색
# ─────────────────────────────────────────────
RED = "#CC0000"          # Deep Red — 대비 5.1:1
ORANGE = "#D55E00"       # Vermillion (Okabe-Ito #6)
YELLOW = "#E69F00"       # Orange-Yellow (#2)
GREEN_SAFE = "#009E73"   # Bluish Green (#3) — 적록색맹에도 구분됨

# Layer 색상 (기존 유지, 경보 4색과 다른 영역)
L1_PHARMACY = "#be185d"
L2_SEWAGE = "#047857"
L3_SEARCH = "#1d4ed8"
# 별칭 (레거시 호환)
L2_SEARCH = L3_SEARCH

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
    1: {"color": GREEN_SAFE, "label": "Level 1 (낮음)",   "radius": 8,  "icon": "✅"},
    2: {"color": YELLOW,     "label": "Level 2 (주의)",   "radius": 12, "icon": "🔔"},
    3: {"color": ORANGE,     "label": "Level 3 (경계)",   "radius": 16, "icon": "⚠️"},
    4: {"color": RED,        "label": "Level 4 (심각)",   "radius": 22, "icon": "🚨"},
}
