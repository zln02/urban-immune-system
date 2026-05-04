"""XGBoost 모델 학습 및 체크포인트 저장 스크립트."""
if __name__ == "__main__":
    from ml.xgboost.model import generate_synthetic_data, train
    df = generate_synthetic_data()
    result = train(df)
    print(f"Training complete: {result}")
