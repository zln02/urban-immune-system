"""기상청 API 기온·습도 수집기 테스트.

케이스:
1. API 키 없을 때 None 반환 (경고 로그)
2. 정상 응답 mock — 기온·습도 파싱 검증
3. 기온 정규화 범위 검증 (-20~40°C → 0~100)
4. 기온만 있고 습도 없는 경우 insert_signal_sync 호출 검증
5. HTTP 예외 → None 반환 (오류 처리)
6. 응답 파싱 실패 (KeyError 등) → None 반환
7. 서울 격자 좌표 (SEOUL_NX=60, SEOUL_NY=127) 검증
8. insert_signal_sync 호출 파라미터 검증 (source='kma_temperature')
9. 기온 경계값 정규화: -20°C → 0, 40°C → 100
10. result dict에 temperature + humidity 모두 포함되는지 검증
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────── Case 1: API 키 없을 때 None 반환 ─────────────────
def test_collect_weather_no_api_key(monkeypatch: pytest.MonkeyPatch):
    """KMA_API_KEY 환경변수 없으면 None 반환 (경고 로그)."""
    monkeypatch.delenv("KMA_API_KEY", raising=False)

    from pipeline.collectors.weather_collector import collect_weather

    result = collect_weather(region="서울특별시")
    assert result is None


# ─────────────────────── Case 2: 정상 응답 mock ────────────────────────────
def test_collect_weather_normal(monkeypatch: pytest.MonkeyPatch):
    """기상청 API 정상 응답 시 temperature, humidity 포함 dict 반환."""
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    fake_response = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"category": "T1H", "obsrValue": "15.5"},  # 기온
                        {"category": "REH", "obsrValue": "60.0"},  # 습도
                        {"category": "WSD", "obsrValue": "2.5"},   # 풍속 (무시)
                    ]
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=fake_response)

    with (
        patch("httpx.get", return_value=mock_resp),
        patch("pipeline.collectors.weather_collector.insert_signal_sync") as mock_insert,
    ):
        result = collect_weather(region="서울특별시")

    assert result is not None
    assert "temperature" in result
    assert "humidity" in result
    assert result["temperature"] == pytest.approx(15.5)
    assert result["humidity"] == pytest.approx(60.0)


# ─────────────────────── Case 3: 기온 정규화 범위 검증 ─────────────────────
def test_collect_weather_temperature_normalization(monkeypatch: pytest.MonkeyPatch):
    """기온 15.5°C → (15.5 + 20) / 60 * 100 = 59.17 정규화 검증."""
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    temp_value = 15.5
    expected_norm = round((temp_value + 20) / 60 * 100, 2)

    fake_response = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"category": "T1H", "obsrValue": str(temp_value)},
                        {"category": "REH", "obsrValue": "65.0"},
                    ]
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=fake_response)

    insert_calls: list[dict] = []

    def fake_insert_signal_sync(region, layer, value, raw_value=None, source=None):
        insert_calls.append({"region": region, "layer": layer, "value": value, "raw_value": raw_value, "source": source})

    with (
        patch("httpx.get", return_value=mock_resp),
        patch("pipeline.collectors.weather_collector.insert_signal_sync", side_effect=fake_insert_signal_sync),
    ):
        collect_weather(region="서울특별시")

    assert len(insert_calls) == 1
    assert insert_calls[0]["value"] == pytest.approx(expected_norm, abs=0.01)
    assert insert_calls[0]["raw_value"] == pytest.approx(temp_value)


# ─────────────────────── Case 4: insert_signal_sync 호출 검증 ─────────────
def test_collect_weather_calls_insert_with_correct_params(monkeypatch: pytest.MonkeyPatch):
    """기온 수집 후 insert_signal_sync가 올바른 파라미터로 호출되는지 검증."""
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    fake_response = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"category": "T1H", "obsrValue": "20.0"},
                    ]
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=fake_response)

    with (
        patch("httpx.get", return_value=mock_resp),
        patch("pipeline.collectors.weather_collector.insert_signal_sync") as mock_insert,
    ):
        collect_weather(region="서울특별시")

    mock_insert.assert_called_once()
    call_kwargs = mock_insert.call_args

    # insert_signal_sync(region, "AUX", norm_temp, raw_value=..., source="kma_temperature")
    args = call_kwargs[0]
    kwargs = call_kwargs[1]

    assert args[0] == "서울특별시"
    assert args[1] == "AUX"
    # 기온 20°C → (20 + 20) / 60 * 100 = 66.67
    expected_norm = round((20.0 + 20) / 60 * 100, 2)
    assert args[2] == pytest.approx(expected_norm, abs=0.01)
    assert kwargs.get("raw_value") == pytest.approx(20.0)
    assert kwargs.get("source") == "kma_temperature"


# ─────────────────────── Case 5: HTTP 예외 → None 반환 ─────────────────────
def test_collect_weather_http_error(monkeypatch: pytest.MonkeyPatch):
    """HTTP 요청 실패 시 None 반환 (예외 처리)."""
    import httpx
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    with patch("httpx.get", side_effect=httpx.HTTPStatusError(
        "500 Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )):
        result = collect_weather(region="서울특별시")

    assert result is None


def test_collect_weather_connection_error(monkeypatch: pytest.MonkeyPatch):
    """연결 오류 시 None 반환."""
    import httpx
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    with patch("httpx.get", side_effect=httpx.ConnectError("연결 실패")):
        result = collect_weather(region="서울특별시")

    assert result is None


# ─────────────────────── Case 6: 응답 파싱 실패 → None 반환 ─────────────────
def test_collect_weather_parse_error(monkeypatch: pytest.MonkeyPatch):
    """응답 JSON 구조가 예상과 다를 때(KeyError) None 반환."""
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    # 잘못된 응답 구조
    bad_response = {"wrong_key": {}}

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=bad_response)

    with patch("httpx.get", return_value=mock_resp):
        result = collect_weather(region="서울특별시")

    assert result is None


# ─────────────────────── Case 7: 서울 격자 좌표 상수 검증 ─────────────────
def test_seoul_grid_coordinates():
    """기상청 서울 격자 좌표가 (60, 127)인지 검증."""
    from pipeline.collectors.weather_collector import SEOUL_NX, SEOUL_NY

    assert SEOUL_NX == 60
    assert SEOUL_NY == 127


# ─────────────────────── Case 8: KMA_CURRENT_URL 상수 검증 ─────────────────
def test_kma_url_constant():
    """기상청 API URL이 정확히 설정되어 있는지 검증."""
    from pipeline.collectors.weather_collector import KMA_CURRENT_URL

    assert "data.go.kr" in KMA_CURRENT_URL
    assert "VilageFcstInfoService" in KMA_CURRENT_URL


# ─────────────────────── Case 9: 경계값 정규화 검증 ─────────────────────────
@pytest.mark.parametrize("temp_c, expected_norm", [
    (-20.0, 0.0),    # 최저 → 0
    (40.0, 100.0),   # 최고 → 100
    (0.0, 33.33),    # 0°C → 33.33
    (20.0, 66.67),   # 20°C → 66.67
])
def test_temperature_normalization_formula(temp_c: float, expected_norm: float, monkeypatch: pytest.MonkeyPatch):
    """기온 정규화 공식 (-20~40°C → 0~100) 경계값 및 중간값 검증."""
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    fake_response = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"category": "T1H", "obsrValue": str(temp_c)},
                    ]
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=fake_response)

    insert_calls: list[dict] = []

    def fake_insert(region, layer, value, raw_value=None, source=None):
        insert_calls.append({"value": value})

    with (
        patch("httpx.get", return_value=mock_resp),
        patch("pipeline.collectors.weather_collector.insert_signal_sync", side_effect=fake_insert),
    ):
        collect_weather(region="서울특별시")

    assert len(insert_calls) == 1
    assert insert_calls[0]["value"] == pytest.approx(expected_norm, abs=0.01)


# ─────────────────────── Case 10: temperature + humidity 모두 반환 ──────────
def test_collect_weather_returns_both_temperature_and_humidity(monkeypatch: pytest.MonkeyPatch):
    """T1H(기온) + REH(습도) 모두 응답에 포함 시 두 값 모두 반환."""
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    fake_response = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"category": "T1H", "obsrValue": "5.0"},
                        {"category": "REH", "obsrValue": "80.0"},
                    ]
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=fake_response)

    with (
        patch("httpx.get", return_value=mock_resp),
        patch("pipeline.collectors.weather_collector.insert_signal_sync"),
    ):
        result = collect_weather(region="서울특별시")

    assert result is not None
    assert result["temperature"] == pytest.approx(5.0)
    assert result["humidity"] == pytest.approx(80.0)


# ─────────────────────── Case 11: 기온 없을 때 insert 미호출 ─────────────────
def test_collect_weather_no_temperature_no_insert(monkeypatch: pytest.MonkeyPatch):
    """응답에 T1H(기온) 없을 때 insert_signal_sync 호출 안 함."""
    monkeypatch.setenv("KMA_API_KEY", "test-key")

    from pipeline.collectors.weather_collector import collect_weather

    fake_response = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"category": "REH", "obsrValue": "75.0"},  # 습도만
                        {"category": "WSD", "obsrValue": "3.0"},   # 풍속만
                    ]
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=fake_response)

    with (
        patch("httpx.get", return_value=mock_resp),
        patch("pipeline.collectors.weather_collector.insert_signal_sync") as mock_insert,
    ):
        result = collect_weather(region="서울특별시")

    # 기온 없으면 insert 호출 안 함
    mock_insert.assert_not_called()
    assert result is not None
    assert "humidity" in result
    assert "temperature" not in result
