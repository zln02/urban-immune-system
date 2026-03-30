"""ML inference service entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Query

app = FastAPI(title="Urban Immune System ML Service", version="0.2.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ml"}


@app.get("/predict/tft")
async def predict_tft(region: str = Query("서울특별시", min_length=2, max_length=100)) -> dict[str, object]:
    from ml.tft.model import load_model

    model = load_model()
    if model is None:
        return {
            "region": region,
            "status": "model_not_loaded",
            "forecast_7d": None,
            "forecast_14d": None,
            "forecast_21d": None,
        }

    return {
        "region": region,
        "status": "model_loaded",
        "forecast_7d": None,
        "forecast_14d": None,
        "forecast_21d": None,
        "message": "Inference dataframe wiring is not implemented yet",
    }


@app.get("/predict/anomaly")
async def predict_anomaly(region: str = Query("서울특별시", min_length=2, max_length=100)) -> dict[str, object]:
    return {
        "region": region,
        "status": "not_implemented",
        "is_anomaly": None,
        "reconstruction_error": None,
        "threshold": None,
    }
