"""backend/app/api/alerts.py 단위 테스트."""
from __future__ import annotations

from backend.app.api.alerts import _compute_alert_level


def test_alert_level_green() -> None:
    assert _compute_alert_level(0.0) == "GREEN"
    assert _compute_alert_level(29.9) == "GREEN"


def test_alert_level_yellow() -> None:
    assert _compute_alert_level(30.0) == "YELLOW"
    assert _compute_alert_level(54.9) == "YELLOW"


def test_alert_level_orange() -> None:
    assert _compute_alert_level(55.0) == "ORANGE"
    assert _compute_alert_level(74.9) == "ORANGE"


def test_alert_level_red() -> None:
    assert _compute_alert_level(75.0) == "RED"
    assert _compute_alert_level(100.0) == "RED"


def test_ensemble_weights_sum_to_one() -> None:
    """앙상블 가중치 합이 1.0인지 확인."""
    from backend.app.api.alerts import W1, W2, W3
    assert abs(W1 + W2 + W3 - 1.0) < 1e-9
