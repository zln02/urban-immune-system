from anomaly.autoencoder import detect_anomaly
from tft.forecast import forecast_next_window


def generate_report() -> str:
    forecast = forecast_next_window()
    level = "high" if detect_anomaly(forecast["confidence"]) else "normal"
    return f"Forecast={forecast['prediction']:.2f}, confidence={forecast['confidence']:.2f}, risk={level}"
