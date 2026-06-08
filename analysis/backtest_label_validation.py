"""KDCA ILI ground truth 와 self-target proxy 라벨 비교 — backtest 신뢰도 정량화.

배경:
  현재 `analysis/backtest_xgboost_multipath.py` 의 라벨은 self-target proxy:
  `alert_future = (L2_wastewater(t+2주) >= threshold)`
  → 모델이 자기 입력의 미래값을 예측하는 구조 (외부 ground truth 아님)
  → 보고된 F1=0.882 가 진짜 임상 유행을 얼마나 맞히는지는 검증 안 됨

목표 (PoC):
  KDCA 표본감시 ILI 라벨 (https://dportal.kdca.go.kr/pot/is/st/influ.do, ≥5.8/1000 = 유행)
  과 self-proxy 라벨이 같은 ISO 주차에서 얼마나 일치하는지 측정.

해석:
  - 일치율 ↑ → self-proxy 가 외부 ground truth 와 정렬 → 기존 F1 신뢰도 ↑
  - 일치율 ↓ → self-proxy 가 진짜 유행 시그널과 분리 → 풀 라벨 교체 필요

한계 (정직):
  - 받은 KDCA 데이터: 2025-2026 절기 1개 (39주만)
  - backtest 기간 (53주, 2025-06 ~ 2026-06) 와 부분 overlap
  - 전국 단일값 → 17 region 모두 같은 라벨 (broadcast)
  - 풀 평가는 절기 6개 다운로드 후 (B 옵션) 가능

usage:
  python -m analysis.backtest_label_validation \
      --kdca-dir pipeline/data/kdca \
      --pathogen influenza \
      --proxy-threshold 70.0 \
      --output analysis/outputs/label_validation_influenza.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# 워크트리 안에서 import 가능하도록 sys.path 보강 (CLI 단독 호출 시)
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import numpy as np  # noqa: E402

from pipeline.collectors.kdca_sentinel_parser import (  # noqa: E402
    ILI_EPIDEMIC_THRESHOLD, parse_all_seasons, to_epidemic_label,
)

logger = logging.getLogger(__name__)


# ─────────────────────── 라벨 비교 ─────────────────────────────────────────
def compute_label_agreement(
    proxy_labels: dict[tuple[int, int], int],
    truth_labels: dict[tuple[int, int], int],
) -> dict[str, object]:
    """proxy 라벨 vs KDCA 진짜 라벨 일치율 + 혼동 행렬.

    Args:
        proxy_labels: {(iso_year, iso_week): 0|1} self-target proxy
        truth_labels: {(iso_year, iso_week): 0|1} KDCA ILI ≥ 5.8
    """
    overlap_keys = sorted(proxy_labels.keys() & truth_labels.keys())
    if not overlap_keys:
        return {"n_overlap": 0, "reason": "no overlap between backtest period and KDCA data"}

    y_proxy = np.array([proxy_labels[k] for k in overlap_keys])
    y_truth = np.array([truth_labels[k] for k in overlap_keys])

    agree = int((y_proxy == y_truth).sum())
    tp = int(((y_proxy == 1) & (y_truth == 1)).sum())
    tn = int(((y_proxy == 0) & (y_truth == 0)).sum())
    fp = int(((y_proxy == 1) & (y_truth == 0)).sum())  # proxy 양성, truth 음성
    fn = int(((y_proxy == 0) & (y_truth == 1)).sum())  # proxy 음성, truth 양성

    # cohen's kappa: chance-adjusted agreement
    n = len(overlap_keys)
    po = agree / n
    p_proxy_pos = y_proxy.mean()
    p_truth_pos = y_truth.mean()
    pe = p_proxy_pos * p_truth_pos + (1 - p_proxy_pos) * (1 - p_truth_pos)
    kappa = (po - pe) / (1 - pe) if pe != 1 else None

    return {
        "n_overlap": int(n),
        "agreement_rate": round(float(po), 4),
        "cohen_kappa": (round(float(kappa), 4) if kappa is not None else None),
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "proxy_positive_rate": round(float(p_proxy_pos), 4),
        "truth_positive_rate": round(float(p_truth_pos), 4),
        "overlap_period": {
            "first": f"{overlap_keys[0][0]}-W{overlap_keys[0][1]:02d}",
            "last": f"{overlap_keys[-1][0]}-W{overlap_keys[-1][1]:02d}",
        },
    }


# ─────────────────────── proxy 라벨 재구성 ────────────────────────────────
async def fetch_proxy_labels(
    db_url: str, pathogen: str, threshold: float, lead_weeks: int = 2,
) -> dict[tuple[int, int], int]:
    """기존 backtest 와 동일 로직으로 self-target proxy 라벨 재구성.

    region 별로 계산 후 (iso_year, iso_week) 기준 다수결 (any region 양성 → 양성).
    KDCA ILI 는 전국 단일이므로 region 차원을 어떻게 reduce 할지 정책 필요:
        - any: 한 region 이라도 양성 → 양성 (민감)
        - majority: 과반 region 양성 → 양성 (보수)
        - all: 전 region 양성 → 양성 (매우 보수)
    여기선 majority 사용.
    """
    import asyncpg

    conn = await asyncpg.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        rows = await conn.fetch(
            """
            SELECT time, region, value FROM layer_signals
            WHERE pathogen = $1 AND layer = 'wastewater'
            ORDER BY region, time
            """,
            pathogen,
        )
    finally:
        await conn.close()

    if not rows:
        logger.warning("DB 에 %s wastewater 신호 없음", pathogen)
        return {}

    # region 별 future label
    import pandas as pd
    df = pd.DataFrame([dict(r) for r in rows])
    df["time"] = pd.to_datetime(df["time"])

    per_week_pos: dict[tuple[int, int], list[int]] = {}
    for _region, g in df.groupby("region"):
        g = g.sort_values("time").reset_index(drop=True)
        g["value_future"] = g["value"].shift(-lead_weeks)
        g["alert"] = (g["value_future"] >= threshold).astype(int)
        for _, row in g.iterrows():
            if pd.isna(row["value_future"]):
                continue
            iso_y, iso_w, _ = row["time"].isocalendar()
            per_week_pos.setdefault((iso_y, iso_w), []).append(int(row["alert"]))

    # 다수결 → 단일 라벨
    return {
        k: (1 if sum(v) > len(v) / 2 else 0)
        for k, v in per_week_pos.items()
    }


def fetch_truth_labels(
    kdca_dir: Path, threshold: float = ILI_EPIDEMIC_THRESHOLD,
) -> dict[tuple[int, int], int]:
    """KDCA ILI CSV 파싱 → (iso_year, iso_week) → 0|1."""
    recs = parse_all_seasons(kdca_dir)
    labels = to_epidemic_label(recs, threshold=threshold)
    return {
        (int(row["iso_year"]), int(row["iso_week"])): int(row["label"])
        for row in labels
    }


# ─────────────────────── CLI ───────────────────────────────────────────────
async def _main() -> int:
    p = argparse.ArgumentParser(description="self-proxy 라벨 vs KDCA ILI ground truth 비교")
    p.add_argument("--kdca-dir", default="pipeline/data/kdca",
                   help="KDCA 인플루엔자 CSV 디렉토리")
    p.add_argument("--pathogen", default="influenza", choices=["influenza"],
                   help="비교 대상 (현재 influenza 만 KDCA 라벨 가용)")
    p.add_argument("--proxy-threshold", type=float,
                   help="self-proxy L2 임계 (기본: backtest_xgboost_multipath.py 와 동일)")
    p.add_argument("--ili-threshold", type=float, default=ILI_EPIDEMIC_THRESHOLD,
                   help="KDCA ILI 유행 임계 (per 1000)")
    p.add_argument("--lead-weeks", type=int, default=2)
    p.add_argument("--db-url", default=None,
                   help="DATABASE_URL override. 미설정 시 .env 사용.")
    p.add_argument("--skip-proxy", action="store_true",
                   help="DB 미가용 시 KDCA 라벨만 출력 (smoke test)")
    p.add_argument("--output", default=None, help="결과 JSON 저장 경로")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # KDCA truth labels
    truth = fetch_truth_labels(Path(args.kdca_dir), threshold=args.ili_threshold)
    logger.info("KDCA ILI truth: %d 주차 (threshold %.1f/1000)", len(truth), args.ili_threshold)

    result: dict[str, object] = {
        "pathogen": args.pathogen,
        "ili_threshold": args.ili_threshold,
        "lead_weeks": args.lead_weeks,
        "kdca_truth_weeks": len(truth),
        "kdca_positive_rate": round(
            sum(truth.values()) / max(1, len(truth)), 4
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "KDCA 데이터: 받은 절기 수만큼만 — 1절기 (39주) 만 있으면 부분 overlap",
            "전국 단일값 → region 차원 미지원 — proxy 라벨은 majority reduce",
            "self-proxy 가 음→양 transition 아닌 level 라벨이면 KDCA 와 정렬 차이 정상",
        ],
    }

    if args.skip_proxy:
        logger.info("--skip-proxy: KDCA 라벨만 보고")
    else:
        from dotenv import load_dotenv
        load_dotenv(_repo_root / ".env", override=False)
        import os
        db_url = args.db_url or os.getenv("DATABASE_URL", "")
        if not db_url:
            logger.error("DATABASE_URL 없음 — --db-url 명시 또는 .env 확인")
            return 2
        thr = args.proxy_threshold
        if thr is None:
            from analysis.backtest_xgboost_multipath import DEFAULT_THRESHOLDS
            thr = DEFAULT_THRESHOLDS.get(args.pathogen, 50.0)
        result["proxy_threshold"] = thr

        proxy = await fetch_proxy_labels(
            db_url=db_url, pathogen=args.pathogen,
            threshold=thr, lead_weeks=args.lead_weeks,
        )
        logger.info("self-proxy: %d 주차 (threshold L2 ≥ %.1f, lead %d주)",
                    len(proxy), thr, args.lead_weeks)
        agreement = compute_label_agreement(proxy, truth)
        result["agreement"] = agreement
        logger.info("일치율: %s%% | kappa: %s | confusion: %s",
                    100 * agreement.get("agreement_rate", 0) if isinstance(agreement.get("agreement_rate"), float) else "?",
                    agreement.get("cohen_kappa"),
                    agreement.get("confusion"))

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        logger.info("결과 저장: %s", out_path)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
