"""ML inference service entrypoint."""
from __future__ import annotations

import logging

import numpy as np
from fastapi import FastAPI, Query

logger = logging.getLogger(__name__)
app = FastAPI(title="Urban Immune System ML Service", version="0.3.0")

# Lazy-loaded models
_xgb_model = None
_anomaly_detector = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ml"}


@app.get("/predict/risk")
async def predict_risk(
    l1: float = Query(50.0, ge=0, le=100),
    l2: float = Query(50.0, ge=0, le=100),
    l3: float = Query(50.0, ge=0, le=100),
    temperature: float = Query(15.0),
    humidity: float = Query(50.0),
    region: str = Query("서울특별시"),
) -> dict:
    """XGBoost 기반 위험도 예측."""
    global _xgb_model
    if _xgb_model is None:
        from ml.xgboost.model import load_model
        _xgb_model = load_model()

    if _xgb_model is None:
        return {
            "region": region,
            "status": "model_not_loaded",
            "composite_score": None,
            "alert_level": None,
        }

    features = np.array([[l1, l2, l3, temperature, humidity]])
    score = float(_xgb_model.predict(features)[0])
    score = max(0.0, min(100.0, score))

    # Alert level from CLAUDE.md ensemble rules
    if score < 30:
        level = "GREEN"
    elif score < 55:
        level = "YELLOW"
    elif score < 75:
        level = "ORANGE"
    else:
        level = "RED"

    return {
        "region": region,
        "status": "ok",
        "composite_score": round(score, 2),
        "alert_level": level,
        "model": "xgboost",
    }


@app.get("/predict/anomaly")
async def predict_anomaly(
    l1: float = Query(50.0, ge=0, le=100),
    l2: float = Query(50.0, ge=0, le=100),
    l3: float = Query(50.0, ge=0, le=100),
    temperature: float = Query(15.0),
    region: str = Query("서울특별시"),
) -> dict:
    """Autoencoder 이상탐지."""
    global _anomaly_detector
    if _anomaly_detector is None:
        try:
            from ml.anomaly.autoencoder import AnomalyDetector
            _anomaly_detector = AnomalyDetector(input_dim=4)
            # Try to load saved model or train with synthetic data
            from ml.xgboost.model import generate_synthetic_data
            df = generate_synthetic_data()
            X = df[["l1_otc", "l2_wastewater", "l3_search", "temperature"]].values / 100.0
            _anomaly_detector.fit(X)
            logger.info("Anomaly detector trained on synthetic data")
        except Exception as e:
            logger.error("Anomaly detector init failed: %s", e)
            return {"region": region, "status": "error", "is_anomaly": None}

    features = np.array([[l1, l2, l3, temperature]]) / 100.0
    try:
        result = _anomaly_detector.predict(features)
        return {"region": region, "status": "ok", **result}
    except Exception as e:
        logger.error("Anomaly prediction failed: %s", e)
        return {"region": region, "status": "error", "is_anomaly": None}


# Keep old endpoint for backward compatibility
@app.get("/predict/tft")
async def predict_tft(region: str = Query("서울특별시")) -> dict:
    """Legacy TFT endpoint — redirects to XGBoost."""
    return await predict_risk(region=region)
