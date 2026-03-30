def collect_weather_data() -> list[dict]:
    return [
        {
            "source": "kma",
            "signal": "weather-risk-adjustment",
            "value": 0.0,
        }
    ]
