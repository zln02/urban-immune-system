"""중간발표용 성능 재현 스크립트.

목적: ml/outputs/validation.json 을 생성해 발표 슬라이드의 F1/Precision/Recall/AUC
숫자를 코드로부터 직접 검증한다.

두 단계로 실행:
  1) synthetic_hardened — 선행 예측 task walk-forward CV (재현성 보장)
  2) real — TimescaleDB의 OTC/Wastewater/Search 시계열을 주차로 정렬하여 동일 평가 시도
     데이터 부족·불일치 시 단계 스킵 + 사유를 결과에 명시.

CLI 예시:
  python -m ml.reproduce_validation
  python -m ml.reproduce_validation --skip-real
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.xgboost.model import (
    ALERT_COL,
    ALERT_THRESHOLD,
    FEATURE_COLS,
    HARDENED_ALERT_COL,
    HARDENED_ALERT_THRESHOLD,
    HARDENED_TARGET_COL,
    generate_synthetic_data,
    train,
)

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_PATH = OUTPUT_DIR / "validation.json"
BACKTEST_17_PATH = Path(__file__).parent.parent / "analysis" / "outputs" / "backtest_17regions.json"
LEAD_TIME_PATH = Path(__file__).parent.parent / "analysis" / "outputs" / "lead_time_summary.json"


def _load_realistic_stage() -> dict[str, Any]:
    """analysis/outputs 의 17지역 백테스트 + lead_time 산출물을 realistic stage 로 통합.

    deck 의 F1 0.621 / Recall 0.838 / +5.9주 선행 등 실데이터 측정값이
    validation.json 한 파일에서 단일 출처로 재현 가능하도록 한다.
    """
    if not BACKTEST_17_PATH.exists():
        return {
            "status": "missing",
            "reason": f"{BACKTEST_17_PATH} 가 없음. analysis/backtest_2025_flu_multi_17regions.py 먼저 실행.",
        }

    backtest = json.loads(BACKTEST_17_PATH.read_text(encoding="utf-8"))
    summary = backtest.get("summary", {})
    out: dict[str, Any] = {
        "status": "ok",
        "data_source": "17regions_backtest",
        "task": "alert_classification (composite ≥ alert_threshold)",
        "n_regions": summary.get("ok_regions"),
        "cv_mean_f1": summary.get("mean_f1"),
        "cv_mean_precision": summary.get("mean_precision"),
        "cv_mean_recall": summary.get("mean_recall"),
        "cv_mean_far": summary.get("mean_far_with_gate"),
        "skipped_regions": summary.get("skipped_regions", []),
        "source_file": str(BACKTEST_17_PATH.relative_to(Path(__file__).parent.parent)),
    }

    if LEAD_TIME_PATH.exists():
        lead = json.loads(LEAD_TIME_PATH.read_text(encoding="utf-8"))
        out["lead_time_weeks"] = lead.get("signal_lead_weeks", {})
        out["ccf_max"] = lead.get("ccf_max", {})
        out["granger_p"] = lead.get("granger_p", {})
        out["analysis_window"] = lead.get("window")
    return out


def _summary_from_train_result(result: dict[str, Any]) -> dict[str, Any]:
    """train()이 반환한 결과에서 발표용 요약 지표를 뽑는다."""
    cv_scores = result.get("cv_scores", [])
    final_eval = result.get("final_eval", {})
    valid_f1 = [s["f1"] for s in cv_scores if not np.isnan(s.get("f1", float("nan")))]
    valid_auc = [s["auc_roc"] for s in cv_scores if not np.isnan(s.get("auc_roc", float("nan")))]
    valid_pr = [s["precision"] for s in cv_scores if not np.isnan(s.get("precision", float("nan")))]
    valid_rc = [s["recall"] for s in cv_scores if not np.isnan(s.get("recall", float("nan")))]
    valid_mae = [s["mae"] for s in cv_scores]

    return {
        "n_folds_total": len(cv_scores),
        "n_folds_valid": len(valid_f1),
        "cv_mean_f1": float(np.mean(valid_f1)) if valid_f1 else None,
        "cv_mean_precision": float(np.mean(valid_pr)) if valid_pr else None,
        "cv_mean_recall": float(np.mean(valid_rc)) if valid_rc else None,
        "cv_mean_auc_roc": float(np.mean(valid_auc)) if valid_auc else None,
        "cv_mean_mae": float(np.mean(valid_mae)) if valid_mae else None,
        "fold_scores": cv_scores,
        "final_eval": final_eval,
    }


def _run_synthetic_hardened() -> dict[str, Any]:
    """진짜 검증: t주 피처로 t+2주 후 확진자 임계값 초과 예측 (선행 검증)."""
    logger.info("[2/3] synthetic-hardened 합성 데이터 walk-forward CV (선행 예측 task)")
    df = generate_synthetic_data(n_weeks=104, seed=42)
    n_alert = int(df[HARDENED_ALERT_COL].sum())
    logger.info("hardened 합성 데이터: %d주 / 미래 경보 양성 %d주 (%.1f%%)",
                len(df), n_alert, n_alert / len(df) * 100)
    result = train(
        df, n_splits=5, gap=4,
        target_col=HARDENED_TARGET_COL,
        alert_col=HARDENED_ALERT_COL,
        alert_threshold=HARDENED_ALERT_THRESHOLD,
        save_checkpoint=False,
    )
    return {
        "data_source": "synthetic_hardened",
        "task": "confirmed_future (t+2주 후 확진자 ≥ 70 예측)",
        "data_seed": 42,
        "lead_weeks": 2,
        "n_weeks": int(len(df)),
        "n_alert_positive": n_alert,
        "alert_threshold": HARDENED_ALERT_THRESHOLD,
        "feature_cols": FEATURE_COLS,
        **_summary_from_train_result(result),
    }


def _fetch_real_dataset(region: str = "서울특별시") -> pd.DataFrame | None:
    """TimescaleDB에서 OTC/Wastewater/Search 주간 시계열을 동기 조회해
    XGBoost 입력 형태(DataFrame)로 정렬한다.

    실패하거나 row가 부족하면 None.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        logger.warning("psycopg2 미설치 — 실데이터 단계 스킵 (pip install psycopg2-binary)")
        return None

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url or "changeme" in db_url:
        logger.warning("DATABASE_URL 미설정 또는 placeholder — 실데이터 스킵")
        return None

    # asyncpg URL → psycopg2 URL
    sync_url = db_url.replace("+asyncpg", "")

    try:
        with psycopg2.connect(sync_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT date_trunc('week', time) AS week,
                           layer,
                           AVG(value) AS value
                    FROM layer_signals
                    WHERE region = %s
                      AND layer IN ('otc', 'wastewater', 'search')
                      AND value > 0
                    GROUP BY date_trunc('week', time), layer
                    ORDER BY week
                    """,
                    (region,),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger.warning("DB 조회 실패: %s", exc)
        return None

    if not rows:
        return None

    df_long = pd.DataFrame(rows)
    df_wide = df_long.pivot(index="week", columns="layer", values="value")
    df_wide = df_wide.rename(columns={
        "otc": "l1_otc", "wastewater": "l2_wastewater", "search": "l3_search",
    })
    # 3계층 모두 존재하는 주만 사용
    df_wide = df_wide.dropna(subset=["l1_otc", "l2_wastewater", "l3_search"])
    if df_wide.empty:
        return None
    # 결측 보조 피처 (기온/습도)는 평균값으로 보정
    df_wide["temperature"] = 15.0
    df_wide["humidity"] = 60.0
    df_wide["composite_score"] = (
        0.35 * df_wide["l1_otc"]
        + 0.40 * df_wide["l2_wastewater"]
        + 0.25 * df_wide["l3_search"]
    )
    df_wide["alert_label"] = (df_wide["composite_score"] > ALERT_THRESHOLD).astype(int)
    return df_wide


def _run_real(region: str) -> dict[str, Any]:
    logger.info("[2/2] real 실데이터 walk-forward CV 시도 (region=%s)", region)
    df = _fetch_real_dataset(region)
    if df is None or len(df) < 30:
        n = 0 if df is None else len(df)
        msg = f"실데이터 부족 (3계층 교집합 {n}주, 최소 30주 필요) — 단계 스킵"
        logger.warning(msg)
        return {
            "data_source": "real",
            "region": region,
            "status": "skipped",
            "reason": msg,
            "n_weeks_3layer_intersection": n,
        }
    n_alert = int(df[ALERT_COL].sum())
    logger.info("실데이터: %d주 / 경보 양성 %d주", len(df), n_alert)
    # 데이터 작을 수 있으니 splits 적게
    n_splits = max(2, min(5, (len(df) - 4) // 4))
    result = train(df, n_splits=n_splits, gap=4)
    return {
        "data_source": "real",
        "region": region,
        "status": "ok",
        "n_weeks": int(len(df)),
        "n_alert_positive": n_alert,
        "alert_threshold": ALERT_THRESHOLD,
        "feature_cols": FEATURE_COLS,
        "first_week": str(df.index.min().date()),
        "last_week": str(df.index.max().date()),
        **_summary_from_train_result(result),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="중간발표용 성능 재현 스크립트")
    parser.add_argument("--skip-real", action="store_true", help="실데이터 단계 스킵")
    parser.add_argument("--region", default="서울특별시")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_branch": os.popen("git rev-parse --abbrev-ref HEAD").read().strip(),
        "git_commit": os.popen("git rev-parse --short HEAD").read().strip(),
        "stages": {},
    }

    try:
        result["stages"]["synthetic_hardened"] = _run_synthetic_hardened()
    except Exception as exc:
        logger.exception("synthetic_hardened 단계 실패")
        result["stages"]["synthetic_hardened"] = {"status": "error", "error": str(exc)}

    if not args.skip_real:
        try:
            result["stages"]["real"] = _run_real(args.region)
        except Exception as exc:
            logger.exception("real 단계 실패")
            result["stages"]["real"] = {"status": "error", "error": str(exc)}

    # realistic stage = 17지역 백테스트 단일 출처 통합 (deck F1 0.621 출처)
    try:
        result["stages"]["realistic"] = _load_realistic_stage()
    except Exception as exc:
        logger.exception("realistic 단계 실패")
        result["stages"]["realistic"] = {"status": "error", "error": str(exc)}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("결과 저장: %s", args.output)

    # 발표용 요약 출력
    print("\n=== 발표용 요약 ===")

    def _print(label: str, s: dict[str, Any]) -> None:
        if s.get("cv_mean_f1") is not None:
            print(
                f"  [{label:<20}] F1={s['cv_mean_f1']:.3f}  "
                f"P={s['cv_mean_precision']:.3f}  R={s['cv_mean_recall']:.3f}  "
                f"AUC={s['cv_mean_auc_roc']:.3f}  MAE={s['cv_mean_mae']:.2f}  "
                f"(n_weeks={s.get('n_weeks', '?')}, "
                f"valid_folds={s.get('n_folds_valid', '?')}/{s.get('n_folds_total', '?')})"
            )

    _print("synthetic_hardened", result["stages"].get("synthetic_hardened", {}))
    real = result["stages"].get("real", {})
    if real.get("status") == "ok":
        _print(f"real ({real.get('region', '?')})", real)
    else:
        print(f"  [real] {real.get('status', 'N/A')}: {real.get('reason', '')}")

    realistic = result["stages"].get("realistic", {})
    if realistic.get("status") == "ok":
        comp_lead = (realistic.get("lead_time_weeks") or {}).get("composite")
        print(
            f"  [{'realistic_17regions':<20}] F1={realistic['cv_mean_f1']:.3f}  "
            f"P={realistic['cv_mean_precision']:.3f}  R={realistic['cv_mean_recall']:.3f}  "
            f"FAR={realistic['cv_mean_far']:.3f}  "
            f"(n_regions={realistic.get('n_regions', '?')}, "
            f"lead_composite={comp_lead}주)"
        )
    else:
        print(f"  [realistic] {realistic.get('status', 'N/A')}: {realistic.get('reason', '')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
