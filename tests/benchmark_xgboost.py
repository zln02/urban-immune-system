"""XGBoost 모델 종합 벤치마크.

캡스톤 성공 기준:
- F1-Score >= 0.70
- Precision >= 0.80 (오경보 0건 목표)
- AUC-ROC >= 0.75
- MAE < 15.0

실행: python -m tests.benchmark_xgboost
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.xgboost.model import (  # noqa: E402
    FEATURE_COLS,
    generate_synthetic_data,
    load_model,
    predict,
    train,
)


def run_benchmark() -> dict:
    """XGBoost 전체 벤치마크 실행."""
    results: dict = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S KST")}

    # 1. 합성 데이터 생성
    print("=" * 60)
    print("Urban Immune System — XGBoost Benchmark")
    print("=" * 60)

    t0 = time.time()
    df = generate_synthetic_data(n_weeks=104)
    gen_time = time.time() - t0
    print(f"\n[1] 합성 데이터 생성: {len(df)}주, {gen_time:.2f}초")
    print(f"    경보 비율: {df['alert_label'].mean():.1%}")
    results["data_weeks"] = len(df)
    results["alert_ratio"] = float(df["alert_label"].mean())

    # 2. Walk-forward 학습
    print("\n[2] Walk-forward 5-fold 학습 시작...")
    t0 = time.time()
    train_result = train(df, n_splits=5, gap=4)
    train_time = time.time() - t0
    print(f"    학습 시간: {train_time:.2f}초")
    results["train_time_sec"] = train_time

    # CV 결과 출력
    print("\n[3] 교차검증 결과:")
    print(f"    {'Fold':>4} | {'MAE':>8} | {'F1':>8} | {'Prec':>8} | {'Recall':>8} | {'AUC':>8}")
    print("    " + "-" * 55)
    for s in train_result["cv_scores"]:
        print(
            f"    {s['fold']:>4d} | {s['mae']:>8.2f} | {s['f1']:>8.3f} | "
            f"{s['precision']:>8.3f} | {s['recall']:>8.3f} | {s['auc_roc']:>8.3f}"
        )
    results["cv_scores"] = train_result["cv_scores"]

    if "cv_mean_f1" in train_result:
        print(f"\n    CV 평균 — F1={train_result['cv_mean_f1']:.3f}, "
              f"MAE={train_result['cv_mean_mae']:.2f}, AUC={train_result['cv_mean_auc']:.3f}")
        results["cv_mean_f1"] = train_result["cv_mean_f1"]
        results["cv_mean_mae"] = train_result["cv_mean_mae"]
        results["cv_mean_auc"] = train_result["cv_mean_auc"]

    # 3. 최종 모델 평가
    print("\n[4] 최종 모델 전체 데이터 평가:")
    final = train_result["final_eval"]
    print(f"    MAE       = {final['mae']:.2f}")
    print(f"    F1-Score  = {final['f1']:.3f}")
    print(f"    Precision = {final['precision']:.3f}")
    print(f"    Recall    = {final['recall']:.3f}")
    print(f"    AUC-ROC   = {final['auc_roc']:.3f}")
    results["final_eval"] = final

    # 4. 추론 속도 벤치마크
    print("\n[5] 추론 속도 벤치마크:")
    model = load_model()
    assert model is not None

    # 단일 추론
    single_feature = np.array([[60.0, 70.0, 55.0, 10.0, 40.0]])
    t0 = time.time()
    for _ in range(1000):
        predict(model, single_feature)
    single_time = (time.time() - t0) / 1000 * 1000  # ms
    print(f"    단일 추론: {single_time:.3f}ms/건")
    results["inference_single_ms"] = single_time

    # 배치 추론 (100건)
    batch_features = np.random.rand(100, 5) * 100
    t0 = time.time()
    for _ in range(100):
        predict(model, batch_features)
    batch_time = (time.time() - t0) / 100 * 1000  # ms
    print(f"    배치 추론 (100건): {batch_time:.3f}ms/batch")
    results["inference_batch_100_ms"] = batch_time

    # 5. 경보 레벨별 정확도
    print("\n[6] 경보 레벨별 분석:")
    X = df[FEATURE_COLS].values
    y_pred = predict(model, X)
    y_true = df["composite_score"].values

    for level_name, lo, hi in [("GREEN", 0, 30), ("YELLOW", 30, 55), ("ORANGE", 55, 75), ("RED", 75, 101)]:
        mask = (y_true >= lo) & (y_true < hi)
        if mask.sum() > 0:
            level_mae = float(np.mean(np.abs(y_pred[mask] - y_true[mask])))
            print(f"    {level_name:>8}: {mask.sum():>3}건, MAE={level_mae:.2f}")

    # 6. 캡스톤 목표 달성 여부
    print("\n" + "=" * 60)
    print("캡스톤 목표 달성 여부:")
    targets = {
        "F1 >= 0.70": final["f1"] >= 0.70,
        "Precision >= 0.80": final["precision"] >= 0.80,
        "AUC-ROC >= 0.75": final["auc_roc"] >= 0.75,
        "MAE < 15.0": final["mae"] < 15.0,
    }
    all_pass = True
    for name, passed in targets.items():
        status = "PASS" if passed else "FAIL"
        print(f"    [{status}] {name}")
        if not passed:
            all_pass = False
    results["targets"] = targets

    overall = "ALL PASS" if all_pass else "SOME FAILED"
    print(f"\n    >>> 종합: {overall} <<<")
    print("=" * 60)
    results["overall_pass"] = all_pass

    # 결과 JSON 저장
    output_path = PROJECT_ROOT / "tests" / "benchmark_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n결과 저장: {output_path}")

    return results


if __name__ == "__main__":
    results = run_benchmark()
    sys.exit(0 if results["overall_pass"] else 1)
