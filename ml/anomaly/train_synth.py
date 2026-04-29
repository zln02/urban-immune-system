"""Autoencoder 이상탐지 PoC 학습 — 합성 정상기 데이터 또는 실 DB 데이터로 fit + 인공 spike 검출 입증.

발표 메시지: "라벨 없이 학습 → '평소와 다른 신호' 검출 → 다음 팬데믹 조기 발견"
의 코드적 근거.

CLI:
  python -m ml.anomaly.train_synth                           # 기본 50 epoch (합성 데이터)
  python -m ml.anomaly.train_synth --epochs 100
  python -m ml.anomaly.train_synth --epochs 100 --save-checkpoint
  python -m ml.anomaly.train_synth --use-real-data --threshold-pct 99.0 --epochs 100 --save-checkpoint
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from ml.anomaly.autoencoder import AnomalyDetector
from ml.xgboost.model import generate_synthetic_data

logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "anomaly_metrics.json"
CHECKPOINT_DIR = Path(__file__).parent.parent / "checkpoints" / "autoencoder"
FEATURE_COLS = ["l1_otc", "l2_wastewater", "l3_search", "temperature"]


def _make_normal_period(n_weeks: int, seed: int) -> np.ndarray:
    """비유행 기간(여름·가을) 정상 신호만 생성. 0-1 정규화."""
    df = generate_synthetic_data(n_weeks=n_weeks, seed=seed)
    # composite_score < 30 (= GREEN 구간) 만 정상으로 가정
    normal = df[df["composite_score"] < 30][FEATURE_COLS].to_numpy()
    return normal


def _make_anomaly_period(n_weeks: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """전체 시계열 중 인공 spike 5건 삽입한 평가용 데이터 + 라벨."""
    df = generate_synthetic_data(n_weeks=n_weeks, seed=seed + 100)
    X = df[FEATURE_COLS].to_numpy().copy()
    y = np.zeros(len(X), dtype=int)
    # 5개 인공 spike: 무작위 위치에 모든 피처 동시 +50 ~ +80 (비정상 동시 상승)
    rng = np.random.default_rng(seed + 200)
    spike_idx = rng.choice(np.arange(20, len(X) - 5), size=5, replace=False)
    for idx in spike_idx:
        X[idx, :3] += rng.uniform(50, 80, size=3)  # L1/L2/L3 동시 spike
        y[idx] = 1
    return X, y


async def _fetch_real_normal_data(min_rows: int = 50) -> tuple[np.ndarray, list[str]]:
    """risk_scores 의 GREEN 구간 + (가능하면) weather 를 결합해 학습 행렬 생성.

    Returns:
        (X, regions_used) — X.shape = (n_rows, 4)  [l1, l2, l3, temperature]
    Raises:
        RuntimeError: 실데이터가 min_rows 미만일 때
    """
    try:
        import asyncpg
    except ImportError as exc:
        raise RuntimeError("asyncpg 미설치 — pip install asyncpg") from exc

    # DATABASE_URL 로드 (dotenv 또는 환경변수)
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env")
    except ImportError:
        pass

    import os
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL 환경변수 없음")

    # asyncpg 는 postgresql+asyncpg:// 접두사 미지원 → 변환
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(pg_url)
    try:
        # 1) GREEN 구간 risk_scores (최근 60일)
        risk_rows = await conn.fetch("""
            SELECT region, time, l1_score, l2_score, l3_score
            FROM risk_scores
            WHERE alert_level = 'GREEN'
              AND time >= NOW() - INTERVAL '60 days'
            ORDER BY region, time DESC
        """)

        if len(risk_rows) < min_rows:
            raise RuntimeError(
                f"실데이터 부족 (현재 {len(risk_rows)}행 / 최소 {min_rows}행 필요)"
            )

        # 2) weather 온도 조회 (region + time 근접 매칭)
        temp_rows = await conn.fetch("""
            SELECT DISTINCT ON (region)
                region, value AS temperature
            FROM layer_signals
            WHERE (source ILIKE '%weather%' OR layer = 'AUX')
              AND time >= NOW() - INTERVAL '60 days'
            ORDER BY region, time DESC
        """)
        temp_map: dict[str, float] = {r["region"]: float(r["temperature"]) for r in temp_rows}

    finally:
        await conn.close()

    # 3) numpy array 조립
    rng = np.random.default_rng(seed=99)
    rows_list: list[list[float]] = []
    regions_used: list[str] = []

    for r in risk_rows:
        region = r["region"]
        l1 = float(r["l1_score"] or 0.0)
        l2 = float(r["l2_score"] or 0.0)
        l3 = float(r["l3_score"] or 0.0)
        if region in temp_map:
            temperature = temp_map[region]
        else:
            # fallback: 20.0 ± 2 가우시안 노이즈 (학습 다양성)
            temperature = 20.0 + float(rng.normal(0, 2))

        rows_list.append([l1, l2, l3, temperature])
        regions_used.append(region)

    X = np.array(rows_list, dtype=np.float32)
    logger.info(
        "실데이터 로드 완료: %d행, 지역 수 %d",
        len(X),
        len(set(regions_used)),
    )
    return X, regions_used


def main() -> int:
    parser = argparse.ArgumentParser(description="Autoencoder 이상탐지 PoC")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--threshold-pct", type=float, default=99.0,
                        help="threshold 퍼센타일 (기본 99.0 — 실데이터 모드 권장)")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--save-checkpoint", action="store_true",
                        help="학습 후 ml/checkpoints/autoencoder/ 에 model.pt + meta.json 저장")
    parser.add_argument("--checkpoint-dir", type=Path, default=CHECKPOINT_DIR)
    parser.add_argument("--use-real-data", action="store_true",
                        help="DB risk_scores GREEN 구간 실데이터로 학습 (합성 대신)")
    parser.add_argument("--min-rows", type=int, default=50,
                        help="실데이터 최소 행 수 (기본 50)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")

    # ── 1) 정상기 학습 데이터 준비 ───────────────────────────────────────────
    if args.use_real_data:
        logger.info("실데이터 모드: DB risk_scores GREEN 구간 로드 중...")
        X_normal, regions_used = asyncio.run(
            _fetch_real_normal_data(min_rows=args.min_rows)
        )
        data_source = "real_db"
        n_normal_rows = len(X_normal)
    else:
        X_normal = _make_normal_period(n_weeks=104, seed=42)
        data_source = "synthetic"
        n_normal_rows = X_normal.shape[0]

    # 0-1 정규화 (Sigmoid 출력 매칭)
    X_min, X_max = X_normal.min(axis=0), X_normal.max(axis=0)
    span = np.maximum(X_max - X_min, 1e-6)
    X_normal_n = (X_normal - X_min) / span

    # 학습 데이터 통계 출력
    logger.info(
        "학습 데이터 통계 — l1: %.2f±%.2f  l2: %.2f±%.2f  l3: %.2f±%.2f",
        X_normal[:, 0].mean(), X_normal[:, 0].std(),
        X_normal[:, 1].mean(), X_normal[:, 1].std(),
        X_normal[:, 2].mean(), X_normal[:, 2].std(),
    )

    # ── 2) 학습 ─────────────────────────────────────────────────────────────
    detector = AnomalyDetector(input_dim=len(FEATURE_COLS), threshold_percentile=args.threshold_pct)
    logger.info("학습 시작: %d행 × %d 피처, threshold_pct=%.1f",
                X_normal_n.shape[0], X_normal_n.shape[1], args.threshold_pct)
    losses = detector.fit(X_normal_n, epochs=args.epochs, lr=1e-3)
    logger.info("학습 완료: 시작 loss %.5f → 최종 %.5f, threshold(%.0fpct) %.5f",
                losses[0], losses[-1], args.threshold_pct, detector.threshold)

    # ── 3) 인공 spike 평가 ──────────────────────────────────────────────────
    X_eval, y_true = _make_anomaly_period(n_weeks=104, seed=42)
    X_eval_n = np.clip((X_eval - X_min) / span, -0.5, 1.5)
    detector.model.eval()
    errors = detector.model.reconstruction_error(torch.FloatTensor(X_eval_n)).numpy()
    y_pred = (errors > detector.threshold).astype(int)

    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # ── 4) 17지역 latest inference (실데이터 모드일 때) ────────────────────
    real_data_inference: dict | None = None
    if args.use_real_data:
        real_data_inference = _infer_17_regions_from_db(detector, X_min, span)

    # ── 5) 결과 저장 ─────────────────────────────────────────────────────────
    train_stats: dict = {
        "l1_mean": float(X_normal[:, 0].mean()),
        "l1_std": float(X_normal[:, 0].std()),
        "l2_mean": float(X_normal[:, 1].mean()),
        "l2_std": float(X_normal[:, 1].std()),
        "l3_mean": float(X_normal[:, 2].mean()),
        "l3_std": float(X_normal[:, 2].std()),
    }

    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "data_source": data_source,
            "feature_cols": FEATURE_COLS,
            "n_normal_rows": n_normal_rows,
            "epochs": args.epochs,
            "threshold_percentile": args.threshold_pct,
            "n_artificial_spikes": int(y_true.sum()),
            "min_rows": args.min_rows if args.use_real_data else None,
        },
        "training": {
            "loss_first": float(losses[0]),
            "loss_last": float(losses[-1]),
            "loss_curve_tail": [float(x) for x in losses[-10:]],
            "threshold": float(detector.threshold),
            "train_stats": train_stats,
        },
        "evaluation": {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "max_error": float(errors.max()),
            "mean_error_normal": float(errors[y_true == 0].mean()),
            "mean_error_anomaly": float(errors[y_true == 1].mean()) if (y_true == 1).any() else None,
        },
    }

    if real_data_inference is not None:
        result["evaluation"]["real_data_inference"] = real_data_inference

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("결과 저장: %s", args.output)

    # ── 6) 체크포인트 저장 ──────────────────────────────────────────────────
    if args.save_checkpoint:
        ckpt_dir = args.checkpoint_dir
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        model_path = ckpt_dir / "model.pt"
        meta_path = ckpt_dir / "meta.json"
        torch.save(detector.model.state_dict(), model_path)
        meta = {
            "feature_cols": FEATURE_COLS,
            "threshold": float(detector.threshold),
            "threshold_percentile": args.threshold_pct,
            "X_min": X_min.tolist(),
            "X_max": X_max.tolist(),
            "input_dim": len(FEATURE_COLS),
            "data_source": data_source,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("체크포인트 저장: %s, %s", model_path, meta_path)

    # ── 7) 콘솔 요약 출력 ──────────────────────────────────────────────────
    print("\n=== Autoencoder PoC 요약 ===")
    print(f"  데이터 소스: {data_source}  ({n_normal_rows}행)")
    print(f"  학습 데이터 통계 — l1={train_stats['l1_mean']:.2f}±{train_stats['l1_std']:.2f}"
          f"  l2={train_stats['l2_mean']:.2f}±{train_stats['l2_std']:.2f}"
          f"  l3={train_stats['l3_mean']:.2f}±{train_stats['l3_std']:.2f}")
    print(f"  학습 loss: {result['training']['loss_first']:.5f} → {result['training']['loss_last']:.5f}")
    print(f"  threshold({args.threshold_pct:.0f}p): {result['training']['threshold']:.5f}")
    print(f"  spike 5개 vs 정상: TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}")
    mean_a = result['evaluation']['mean_error_anomaly']
    mean_n = result['evaluation']['mean_error_normal']
    if mean_a:
        print(f"  평균 오차 — 정상={mean_n:.4f}  이상={mean_a:.4f}  "
              f"(분리도 = {mean_a / max(mean_n, 1e-9):.1f}x)")
    if real_data_inference is not None:
        rdi = real_data_inference
        print(f"\n  [17지역 실데이터 추론] anomaly={rdi['anomaly']} "
              f"warning={rdi['warning']} normal={rdi['normal']}")
        print(f"  top3 스코어: {rdi['top3_by_error']}")
    return 0


def _infer_17_regions_from_db(
    detector: AnomalyDetector,
    X_min: np.ndarray,
    span: np.ndarray,
) -> dict:
    """DB에서 17지역 latest 행 읽어 status 카운트 반환 (동기 래퍼)."""
    return asyncio.run(_async_infer_17_regions(detector, X_min, span))


async def _async_infer_17_regions(
    detector: AnomalyDetector,
    X_min: np.ndarray,
    span: np.ndarray,
) -> dict:
    """17지역 최신 risk_scores로 Autoencoder 추론."""
    try:
        import asyncpg
    except ImportError:
        logger.warning("asyncpg 없음 — 17지역 추론 스킵")
        return {}

    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env")
    except ImportError:
        pass

    import os
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        return {}

    KR_REGIONS = [
        "서울특별시", "경기도", "인천광역시", "강원특별자치도",
        "충청북도", "충청남도", "대전광역시", "세종특별자치시",
        "전라북도", "전라남도", "광주광역시",
        "경상북도", "경상남도", "대구광역시", "울산광역시", "부산광역시",
        "제주특별자치도",
    ]

    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (region)
                region, l1_score, l2_score, l3_score
            FROM risk_scores
            WHERE region = ANY($1::text[])
            ORDER BY region, time DESC
        """, KR_REGIONS)
        risk_map = {r["region"]: r for r in rows}
    finally:
        await conn.close()

    counts: dict[str, int] = {"anomaly": 0, "warning": 0, "normal": 0}
    top3_list: list[dict] = []
    threshold = detector.threshold

    detector.model.eval()
    for region in KR_REGIONS:
        r = risk_map.get(region)
        l1 = float(r["l1_score"] or 0.0) if r else 0.0
        l2 = float(r["l2_score"] or 0.0) if r else 0.0
        l3 = float(r["l3_score"] or 0.0) if r else 0.0
        temperature = 20.0

        raw_feat = np.array([[l1, l2, l3, temperature]], dtype=np.float32)
        normalized = np.clip((raw_feat - X_min) / span, -0.5, 1.5)

        with torch.no_grad():
            tensor = torch.FloatTensor(normalized)
            error = float(detector.model.reconstruction_error(tensor).numpy()[0])

        if error > threshold:
            status = "anomaly"
        elif error > threshold * 0.7:
            status = "warning"
        else:
            status = "normal"

        counts[status] = counts.get(status, 0) + 1
        top3_list.append({"region": region, "error": round(error, 6), "status": status})

    top3_list.sort(key=lambda x: x["error"], reverse=True)
    return {
        "anomaly": counts["anomaly"],
        "warning": counts["warning"],
        "normal": counts["normal"],
        "top3_by_error": top3_list[:3],
    }


if __name__ == "__main__":
    sys.exit(main())
