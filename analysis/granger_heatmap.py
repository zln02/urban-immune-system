"""V11.2 — 17 region × 3 layer Granger -log10(p) heatmap.

Reads:  analysis/outputs/granger_17regions_results.json
Writes: analysis/outputs/granger_17regions_heatmap.png

annotation: '*' when significant under per-layer Bonferroni (family=17 within layer).
Composite per-region p 는 별도 subplot 으로 16th 행 추가 (참고).

seaborn 의존 회피 — matplotlib 만 사용.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("granger_heatmap")

RESULTS = PROJECT_ROOT / "analysis" / "outputs" / "granger_17regions_results.json"
OUT_PNG = PROJECT_ROOT / "analysis" / "outputs" / "granger_17regions_heatmap.png"

LAYERS = ["L1_otc", "L2_wastewater", "L3_search"]
LAYER_LABEL_SHORT = {
    "L1_otc":        "L1 OTC",
    "L2_wastewater": "L2 하수",
    "L3_search":     "L3 검색",
}


def _korean_font() -> str:
    candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            fm.fontManager.addfont(path)
            return fm.FontProperties(fname=path).get_name()
    return "DejaVu Sans"


def main() -> None:
    plt.rcParams["font.family"] = _korean_font()
    plt.rcParams["axes.unicode_minus"] = False

    with open(RESULTS, encoding="utf-8") as f:
        data = json.load(f)

    rows_by_region: dict[str, dict[str, dict]] = {}
    for r in data["results_per_region_layer"]:
        if r["status"] != "OK":
            continue
        rows_by_region.setdefault(r["region"], {})[r["layer"]] = r

    regions = list(rows_by_region.keys())
    n_reg = len(regions)
    n_lay = len(LAYERS)

    pmat = np.full((n_reg, n_lay), np.nan)
    sig_mat = np.zeros((n_reg, n_lay), dtype=bool)
    for i, region in enumerate(regions):
        for j, lbl in enumerate(LAYERS):
            r = rows_by_region[region].get(lbl)
            if r is None:
                continue
            pmat[i, j] = r["p_raw"]
            sig_mat[i, j] = bool(r.get("significant_per_layer_bonferroni", False))

    neg_log10 = -np.log10(np.clip(pmat, 1e-6, 1.0))

    fig, ax = plt.subplots(figsize=(7, 8.5))
    vmax = max(float(np.nanmax(neg_log10)), -np.log10(0.05) * 1.5)
    im = ax.imshow(neg_log10, aspect="auto", cmap="YlOrRd", vmin=0, vmax=vmax)

    ax.set_xticks(np.arange(n_lay))
    ax.set_xticklabels([LAYER_LABEL_SHORT[lbl] for lbl in LAYERS], fontsize=10)
    ax.set_yticks(np.arange(n_reg))
    ax.set_yticklabels(regions, fontsize=8)

    for i in range(n_reg):
        for j in range(n_lay):
            if np.isnan(pmat[i, j]):
                txt = "—"
            else:
                p = pmat[i, j]
                marker = "*" if sig_mat[i, j] else ""
                txt = f"{p:.3f}\n{marker}".rstrip()
            ax.text(j, i, txt, ha="center", va="center",
                    fontsize=7, color="black" if neg_log10[i, j] < vmax * 0.55 else "white")

    threshold_line = -np.log10(0.05)
    cbar = plt.colorbar(im, ax=ax, label="-log10(p_raw)", shrink=0.85)
    cbar.ax.axhline(threshold_line, color="navy", linewidth=1.2, linestyle="--")
    cbar.ax.text(1.7, threshold_line, " p=0.05", color="navy", fontsize=8, va="center")

    n_bonf_per_layer = data["summary"]["n_significant_per_layer_bonferroni"]
    n_sig_raw = data["summary"]["n_significant_raw"]
    n_eff = data["n_tests_effective_independent_estimate"]
    title = (
        "V11.2 — 17 region × 3 layer Granger -log10(p_raw)\n"
        f"raw α=0.05 sig: {n_sig_raw}/51 · per-layer Bonferroni sig: "
        f"{n_bonf_per_layer}/51 · effective uniq tests: {n_eff}/51"
    )
    ax.set_title(title, fontsize=10.5, pad=12)
    ax.set_xlabel(
        "L1·L3 broadcast (전국 단일값) → 같은 layer 내 17 region p 동일 정상; "
        "L2 wastewater 만 실 region 차별",
        fontsize=7.5, color="dimgray",
    )

    plt.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PNG, dpi=140, bbox_inches="tight")
    plt.close()
    logger.info("heatmap saved: %s", OUT_PNG)
    print(f"[granger_heatmap] wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
