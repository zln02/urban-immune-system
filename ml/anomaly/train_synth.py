"""Autoencoder 이상탐지 PoC 학습 — 합성 정상기 데이터로 fit + 인공 spike 검출 입증.

발표 메시지: "라벨 없이 학습 → '평소와 다른 신호' 검출 → 다음 팬데믹 조기 발견"
의 코드적 근거.

CLI:
  python -m ml.anomaly.train_synth                   # 기본 50 epoch
  python -m ml.anomaly.train_synth --epochs 100
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ml.anomaly.autoencoder import AnomalyDetector
from ml.xgboost.model import generate_synthetic_data

logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "anomaly_metrics.json"
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Autoencoder 이상탐지 PoC")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--threshold-pct", type=float, default=95.0)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")

    # 1) 정상기 데이터로 학습 (라벨 없음)
    X_normal = _make_normal_period(n_weeks=104, seed=42)
    # 0-1 정규화 (Sigmoid 출력 매칭)
    X_min, X_max = X_normal.min(axis=0), X_normal.max(axis=0)
    span = np.maximum(X_max - X_min, 1e-6)
    X_normal_n = (X_normal - X_min) / span

    detector = AnomalyDetector(input_dim=len(FEATURE_COLS), threshold_percentile=args.threshold_pct)
    logger.info("정상기 데이터: %d 주 × %d 피처", X_normal_n.shape[0], X_normal_n.shape[1])
    losses = detector.fit(X_normal_n, epochs=args.epochs, lr=1e-3)
    logger.info("학습 완료: 시작 loss %.5f → 최종 %.5f, threshold(%dpct) %.5f",
                losses[0], losses[-1], int(args.threshold_pct), detector.threshold)

    # 2) 인공 spike 5건 삽입한 평가 데이터로 검증
    X_eval, y_true = _make_anomaly_period(n_weeks=104, seed=42)
    X_eval_n = np.clip((X_eval - X_min) / span, -0.5, 1.5)
    detector.model.eval()
    import torch
    errors = detector.model.reconstruction_error(torch.FloatTensor(X_eval_n)).numpy()
    y_pred = (errors > detector.threshold).astype(int)

    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "feature_cols": FEATURE_COLS,
            "n_normal_weeks": int(X_normal_n.shape[0]),
            "epochs": args.epochs,
            "threshold_percentile": args.threshold_pct,
            "n_artificial_spikes": int(y_true.sum()),
        },
        "training": {
            "loss_first": float(losses[0]),
            "loss_last": float(losses[-1]),
            "loss_curve_tail": [float(x) for x in losses[-10:]],
            "threshold": float(detector.threshold),
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("결과 저장: %s", args.output)

    print("\n=== Autoencoder PoC 요약 ===")
    print(f"  학습 loss: {result['training']['loss_first']:.5f} → {result['training']['loss_last']:.5f}")
    print(f"  threshold(95p): {result['training']['threshold']:.5f}")
    print(f"  spike 5개 vs 정상: TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}")
    print(f"  평균 오차 — 정상={result['evaluation']['mean_error_normal']:.4f}  "
          f"이상={result['evaluation']['mean_error_anomaly']:.4f}  (분리도 = "
          f"{result['evaluation']['mean_error_anomaly'] / max(result['evaluation']['mean_error_normal'], 1e-9):.1f}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
