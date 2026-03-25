"""지도 빌더."""

from __future__ import annotations

import folium
from branca.element import Element

from src.config import DISTRICTS, RISK_CFG
from src.map.styles import map_styles
from src.utils import hex_to_rgba


def inject_map_styles(fmap: folium.Map) -> None:
    fmap.get_root().header.add_child(Element(map_styles()))


def build_pulse_marker(level: int, cfg: dict[str, str], is_selected: bool) -> folium.DivIcon:
    size = cfg["radius"] * 2 + 18
    core_size = max(12, cfg["radius"] + 2)
    pulse_speed = {8: "3.2s", 12: "2.7s", 16: "2.2s", 22: "1.7s"}.get(cfg["radius"], "2.5s")
    pulse_fill = hex_to_rgba(cfg["color"], 0.14 if is_selected else 0.10)
    pulse_shadow = hex_to_rgba(cfg["color"], 0.45 if is_selected else 0.30)
    selected_class = "selected" if is_selected else ""
    level_class = f"level-{level}"

    html = f"""
    <div class="risk-pulse-marker {level_class} {selected_class}"
         style="
            --pulse-size:{size}px;
            --core-size:{core_size}px;
            --pulse-speed:{pulse_speed};
            --pulse-color:{cfg['color']};
            --pulse-fill:{pulse_fill};
            --pulse-shadow:{pulse_shadow};
         ">
        <span class="pulse-ring"></span>
        <span class="pulse-ring delay"></span>
        <span class="pulse-ring intense"></span>
        <span class="pulse-core"></span>
    </div>
    """
    return folium.DivIcon(html=html, icon_size=(size, size), icon_anchor=(size // 2, size // 2))


def build_map(region: str) -> folium.Map:
    selected_name = region.replace("서울 ", "")
    fmap = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="CartoDB positron")
    inject_map_styles(fmap)

    for district in DISTRICTS:
        cfg = RISK_CFG[district["risk"]]
        otc_status = "▲ 급증" if district["risk"] >= 3 else "— 정상"
        sewage_status = "▲ 양성" if district["risk"] >= 3 else "— 정상"
        search_status = "▲ 급증" if district["risk"] >= 2 else "— 정상"
        is_selected = district["name"] == selected_name
        weight = 3 if is_selected else 1.5
        fill_opacity = 0.20 if is_selected else 0.12

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
            radius=cfg["radius"] + 8,
            color=cfg["color"],
            fill=True,
            fill_color=cfg["color"],
            fill_opacity=fill_opacity,
            weight=weight,
            opacity=0.65,
        ).add_to(fmap)

        folium.Marker(
            location=[district["lat"], district["lon"]],
            icon=build_pulse_marker(district["risk"], cfg, is_selected),
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{district['name']} — {cfg['label']}",
        ).add_to(fmap)

    return fmap
