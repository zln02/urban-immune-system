"""공통 유틸리티."""

from __future__ import annotations

from pathlib import Path


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0.0 and 1.0")

    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError("hex_color must be a 6-digit hex string")

    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def asset_path(filename: str) -> str:
    assets_dir = Path(__file__).resolve().parents[1] / "prototype" / "assets"
    candidate = (assets_dir / filename).resolve()
    candidate.relative_to(assets_dir.resolve())
    return str(candidate)
