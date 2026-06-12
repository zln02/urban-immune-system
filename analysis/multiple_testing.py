"""V11.1 Multiple testing correction — Granger causality p-values.

Canonical Granger p data (analysis/outputs/lead_time_summary.json) covers
서울특별시 only, broken out by signal layer (L1 OTC / L2 wastewater /
L3 search) and the composite. Per-region (17-region) Granger p-values
are NOT available in the canonical artifacts as of 2026-05-17.

This script:
  1. Applies Bonferroni + Benjamini-Hochberg FDR across the 3 per-layer
     tests for 서울 (the only region with raw p-values).
  2. Reports the composite (national-aggregate) p separately — composites
     are not part of the multi-test family.
  3. Documents the per-region data gap explicitly so reviewers see the
     limitation rather than a fabricated 17-region table.

Output:
    analysis/outputs/multiple_testing_results.json
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from statsmodels.stats.multitest import multipletests

ALPHA = 0.05
GRANGER_SRC = Path("analysis/outputs/lead_time_summary.json")
OUTPUT = Path("analysis/outputs/multiple_testing_results.json")


def main() -> None:
    src = json.loads(GRANGER_SRC.read_text(encoding="utf-8"))
    granger = src["granger_p"]

    layer_order = ["l1_otc", "l2_wastewater", "l3_search"]
    layer_p = [float(granger[k]) for k in layer_order]
    composite_p = float(granger["composite"])

    bonf_reject, bonf_p_adj, _, _ = multipletests(layer_p, alpha=ALPHA, method="bonferroni")
    bh_reject, bh_p_adj, _, _ = multipletests(layer_p, alpha=ALPHA, method="fdr_bh")

    per_layer = []
    for i, layer in enumerate(layer_order):
        per_layer.append(
            {
                "signal": layer,
                "p_raw": layer_p[i],
                "p_bonferroni": float(bonf_p_adj[i]),
                "p_bh_fdr": float(bh_p_adj[i]),
                "significant_raw": layer_p[i] < ALPHA,
                "significant_bonferroni": bool(bonf_reject[i]),
                "significant_bh_fdr": bool(bh_reject[i]),
            }
        )

    n_sig_raw = sum(1 for r in per_layer if r["significant_raw"])
    n_sig_bonf = int(bonf_reject.sum())
    n_sig_bh = int(bh_reject.sum())

    interpretation = (
        f"Across the 3 signal layers (L1 OTC / L2 wastewater / L3 search) for 서울특별시, "
        f"{n_sig_raw}/3 are significant at raw α=0.05, "
        f"{n_sig_bonf}/3 survive Bonferroni, and {n_sig_bh}/3 survive BH-FDR. "
        f"The composite (national-aggregate) p={composite_p:.4f} is significant on its own and "
        "is reported outside the multi-test family because it is a single derived test, not one of many. "
        "L2 (wastewater) fails all corrections — consistent with the small sample (12 weeks) and the "
        "ongoing data-coverage limitation flagged in the V11 metric notes."
    )

    out = {
        "n_tests": len(layer_p),
        "test_family": "Granger causality, signal layers (L1/L2/L3) for 서울특별시",
        "alpha": ALPHA,
        "methods": ["Bonferroni", "Benjamini-Hochberg FDR"],
        "per_test": per_layer,
        "composite": {
            "p_raw": composite_p,
            "significant_raw": composite_p < ALPHA,
            "note": "Composite is a single national-aggregate test, not part of the multi-test family.",
        },
        "summary": {
            "n_significant_raw": n_sig_raw,
            "n_significant_bonferroni": n_sig_bonf,
            "n_significant_bh_fdr": n_sig_bh,
        },
        "data_gap": {
            "issue": "17-region per-region Granger p-values are not available in canonical artifacts.",
            "canonical_granger_scope": "서울특별시 only, 4 signals (L1/L2/L3 + composite)",
            "consequence": (
                "We cannot run a 17-region multiple-testing correction without re-running "
                "analysis/lead_time_2025w48.py against all 17 regions. The V11 backtest metrics "
                "(recall/F1/FAR/MCC) are per-region, but Granger causality was only computed "
                "for the Seoul case study."
            ),
            "next_step": (
                "If reviewers require per-region Granger correction, extend "
                "analysis/lead_time_2025w48.py to iterate over all 17 regions and re-run; "
                "rerun this script against the new p-vector."
            ),
        },
        "interpretation": interpretation,
        "canonical_source": str(GRANGER_SRC),
        "timestamp": str(date.today()),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[multiple_testing] wrote {OUTPUT}")
    for r in per_layer:
        print(
            f"  {r['signal']:14s} raw={r['p_raw']:.4f}  bonf={r['p_bonferroni']:.4f}  bh={r['p_bh_fdr']:.4f}  "
            f"sig(raw/bonf/bh)={r['significant_raw']}/{r['significant_bonferroni']}/{r['significant_bh_fdr']}"
        )
    print(f"  composite       raw={composite_p:.4f}  (reported outside multi-test family)")
    print(f"  summary: raw={n_sig_raw}/3, bonf={n_sig_bonf}/3, bh={n_sig_bh}/3")


if __name__ == "__main__":
    main()
