"""부하테스트 결과 분석 스크립트 — locust CSV → JSON + PNG 차트.

사용법:
    python tests/load/analyze_results.py [--csv tests/load/results_stats.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from datetime import datetime


def parse_stats(csv_path: pathlib.Path) -> list[dict]:
    """locust _stats.csv 파싱 — Aggregated 행 제외."""
    rows: list[dict] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "")
            if name in ("Aggregated", ""):
                continue
            rows.append({
                "endpoint": name,
                "method": row.get("Type", "GET"),
                "request_count": int(row.get("Request Count", 0) or 0),
                "failure_count": int(row.get("Failure Count", 0) or 0),
                "p50_ms": float(row.get("50%", 0) or 0),
                "p95_ms": float(row.get("95%", 0) or 0),
                "p99_ms": float(row.get("99%", 0) or 0),
                "avg_ms": float(row.get("Average (ms)", 0) or 0),
                "min_ms": float(row.get("Min (ms)", 0) or 0),
                "max_ms": float(row.get("Max (ms)", 0) or 0),
                "rps": float(row.get("Requests/s", 0) or 0),
            })
    return rows


def compute_verdict(rows: list[dict], p95_target_ms: float = 500.0) -> dict:
    """엔드포인트별 p95 목표 충족 여부 + 종합 판정."""
    results: list[dict] = []
    all_pass = True
    total_requests = 0
    total_failures = 0
    total_rps = 0.0

    for r in rows:
        fail_rate = (
            round(r["failure_count"] / r["request_count"] * 100, 2)
            if r["request_count"] > 0 else 0.0
        )
        pass_p95 = r["p95_ms"] < p95_target_ms
        if not pass_p95:
            all_pass = False
        total_requests += r["request_count"]
        total_failures += r["failure_count"]
        total_rps += r["rps"]
        results.append({**r, "failure_rate_pct": fail_rate, "p95_pass": pass_p95})

    overall_fail_rate = (
        round(total_failures / total_requests * 100, 2) if total_requests > 0 else 0.0
    )
    return {
        "generated_at": datetime.now().isoformat(),
        "p95_target_ms": p95_target_ms,
        "endpoints": results,
        "summary": {
            "total_requests": total_requests,
            "total_failures": total_failures,
            "overall_failure_rate_pct": overall_fail_rate,
            "total_rps": round(total_rps, 2),
            "all_p95_pass": all_pass,
            "overall_verdict": "PASS" if all_pass else "FAIL",
        },
    }


def save_chart(verdict: dict, output_path: pathlib.Path) -> None:
    """엔드포인트별 p50/p95/p99 bar chart 저장 (matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib 미설치 — 차트 생략 (pip install matplotlib 후 재실행)")
        return

    endpoints = [e["endpoint"].replace("/api/v1/", "") for e in verdict["endpoints"]]
    p50_vals = [e["p50_ms"] for e in verdict["endpoints"]]
    p95_vals = [e["p95_ms"] for e in verdict["endpoints"]]
    p99_vals = [e["p99_ms"] for e in verdict["endpoints"]]
    target = verdict["p95_target_ms"]

    x = np.arange(len(endpoints))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width, p50_vals, width, label="p50", color="#3b82f6", alpha=0.85)
    ax.bar(x,         p95_vals, width, label="p95", color="#f59e0b", alpha=0.85)
    ax.bar(x + width, p99_vals, width, label="p99", color="#ef4444", alpha=0.85)
    ax.axhline(y=target, color="red", linestyle="--", linewidth=1.5,
               label=f"p95 목표 {target}ms (조달청 기준)")

    ax.set_xticks(x)
    ax.set_xticklabels(endpoints, rotation=15, ha="right", fontsize=9)
    ax.set_ylabel("응답시간 (ms)")
    ax.set_title("UIS FastAPI 부하테스트 — 엔드포인트별 응답시간 분포\n(50 동시 사용자, 6분)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"차트 저장: {output_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="locust 결과 분석")
    parser.add_argument(
        "--csv",
        default="tests/load/results_stats.csv",
        help="locust _stats.csv 경로 (기본: tests/load/results_stats.csv)",
    )
    parser.add_argument(
        "--output-json",
        default="analysis/outputs/load_test_results.json",
        help="JSON 출력 경로",
    )
    parser.add_argument(
        "--output-chart",
        default="analysis/outputs/load_test_summary.png",
        help="bar chart PNG 출력 경로",
    )
    parser.add_argument(
        "--p95-target",
        type=float,
        default=500.0,
        help="p95 목표 (ms, 기본 500)",
    )
    args = parser.parse_args(argv)

    csv_path = pathlib.Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: {csv_path} 없음. 먼저 부하테스트를 실행하세요.", file=sys.stderr)
        return 1

    rows = parse_stats(csv_path)
    if not rows:
        print("ERROR: 파싱 가능한 행 없음.", file=sys.stderr)
        return 1

    verdict = compute_verdict(rows, args.p95_target)

    # JSON 저장
    json_path = pathlib.Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"\nJSON 결과 저장: {json_path}")

    # 콘솔 출력
    print("\n" + "=" * 60)
    print(f"{'엔드포인트':<40} {'p50':>6} {'p95':>6} {'p99':>6} {'RPS':>6}  판정")
    print("=" * 60)
    for e in verdict["endpoints"]:
        status = "PASS" if e["p95_pass"] else "FAIL"
        print(
            f"{e['endpoint']:<40} {e['p50_ms']:>5.0f} {e['p95_ms']:>5.0f} "
            f"{e['p99_ms']:>5.0f} {e['rps']:>5.1f}  {status}"
        )
    s = verdict["summary"]
    print("=" * 60)
    print(
        f"종합  요청={s['total_requests']}  실패율={s['overall_failure_rate_pct']:.1f}%  "
        f"총RPS={s['total_rps']:.1f}"
    )
    print(f"종합 판정: {s['overall_verdict']}")

    # 차트 저장
    chart_path = pathlib.Path(args.output_chart)
    save_chart(verdict, chart_path)

    return 0 if verdict["summary"]["all_p95_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
