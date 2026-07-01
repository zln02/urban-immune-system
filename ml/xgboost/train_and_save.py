"""XGBoost 합성데이터 스모크 학습 스크립트 (개발용).

주의: 이 스크립트는 **합성 데이터**로 학습 파이프라인 동작만 확인하는 용도다.
실 성능 지표(17개 시·도 walk-forward, F1=0.907 · self-proxy 라벨)는
`analysis/backtest_xgboost_influenza_17regions.py` 등 analysis/ 백테스트에서 산출한다.
"""

if __name__ == "__main__":
    from ml.xgboost.model import generate_synthetic_data, train

    df = generate_synthetic_data()
    result = train(df)
    print(f"[synthetic smoke-train] complete: {result}")
