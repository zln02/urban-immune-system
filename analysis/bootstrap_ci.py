"""V11.1 Bootstrap 95% CI — per-region metrics (n=17).

Non-parametric percentile bootstrap. Reads canonical 17-region backtest,
resamples per-region metric vectors, reports CI for the mean.

Canonical source (read-only):
    analysis/outputs/backtest_17regions.json
Output:
    analysis/outputs/bootstrap_ci_results.json
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np

SEED = 42
N_RESAMPLES = 1000
CANONICAL = Path("analysis/outputs/backtest_17regions.json")
OUTPUT = Path("analysis/outputs/bootstrap_ci_results.json")

METRIC_MAP = {
    "recall": "recall",
    "precision": "precision",
    "f1": "f1",
    "far_gate_on": "false_alarm_rate",
    "mcc": "mcc",
}

THRESHOLDS = {
    "recall": (">=", 0.85),
    "f1": (">=", 0.80),
    "far_gate_on": ("<", 0.30),
    "precision": (None, None),
    "mcc": (None, None),
}


def _load_per_region(path: Path) -> dict[str, list[float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    regions = data["regions"]
    vectors: dict[str, list[float]] = {k: [] for k in METRIC_MAP}
    region_names: list[str] = []
    for name, rec in regions.items():
        if rec.get("status") != "ok":
            continue
        region_names.append(name)
        for metric, canonical_key in METRIC_MAP.items():
            vectors[metric].append(float(rec[canonical_key]))
    if len(region_names) != 17:
        raise RuntimeError(f"expected 17 ok regions, got {len(region_names)}")
    return vectors


def _bootstrap_mean_ci(values: list[float], rng: np.random.Generator) -> dict:
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    means = np.empty(N_RESAMPLES, dtype=float)
    for i in range(N_RESAMPLES):
        sample = rng.choice(arr, size=n, replace=True)
        means[i] = sample.mean()
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)),
        "ci_lower": float(np.percentile(means, 2.5)),
        "ci_upper": float(np.percentile(means, 97.5)),
        "bootstrap_mean": float(means.mean()),
        "bootstrap_std": float(means.std(ddof=1)),
        "n": n,
    }


def _threshold_status(metric: str, ci_lower: float, ci_upper: float) -> str:
    op, thr = THRESHOLDS[metric]
    if op is None:
        return "n/a"
    if op == ">=":
        return "pass" if ci_lower >= thr else ("borderline" if ci_upper >= thr else "fail")
    if op == "<":
        return "pass" if ci_upper < thr else ("borderline" if ci_lower < thr else "fail")
    return "n/a"


def main() -> None:
    rng = np.random.default_rng(SEED)
    vectors = _load_per_region(CANONICAL)

    results: dict[str, dict] = {}
    for metric in METRIC_MAP:
        ci = _bootstrap_mean_ci(vectors[metric], rng)
        op, thr = THRESHOLDS[metric]
        ci["threshold"] = (
            None if op is None else {"op": op, "value": thr, "status": _threshold_status(metric, ci["ci_lower"], ci["ci_upper"])}
        )
        ci["raw_values"] = vectors[metric]
        results[metric] = ci

    out = {
        "method": "non-parametric percentile bootstrap",
        "n_resamples": N_RESAMPLES,
        "seed": SEED,
        "data_basis": "per_region",
        "canonical_source": str(CANONICAL),
        "n_regions": 17,
        "results": results,
        "timestamp": str(date.today()),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[bootstrap_ci] wrote {OUTPUT}")
    for metric, r in results.items():
        thr = r["threshold"]
        thr_str = "" if thr is None else f"  {thr['op']} {thr['value']} → {thr['status']}"
        print(
            f"  {metric:12s} mean={r['mean']:.4f}  CI=[{r['ci_lower']:.4f}, {r['ci_upper']:.4f}]  n={r['n']}{thr_str}"
        )


if __name__ == "__main__":
    main()
