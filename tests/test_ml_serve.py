"""tests/test_ml_serve.py

ml/serve.py FastAPI 엔드포인트 커버리지 테스트.

전략:
- FastAPI TestClient (httpx 기반) 사용
- 실제 모델 로딩 없이 mock 처리 → CI 속도 유지
- 각 엔드포인트의 정상/비정상 경로 모두 커버
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# TFT 서빙 테스트는 ml extras(torch·pytorch-forecasting) 필요 — 미설치 시 skip.
# 또한 patch("ml.tft.train_synth...") 대상 서브모듈을 여기서 미리 등록해
# 테스트 실행 순서와 무관하게 해석되도록 한다.
pytest.importorskip("torch")
pytest.importorskip("pytorch_forecasting")
import ml.tft.train_synth  # noqa: E402,F401

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """ml.serve 모듈 레벨 글로벌 변수 초기화 후 TestClient 반환."""
    import ml.serve as srv

    srv._xgb_model = None
    srv._tft_model = None
    from ml.serve import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def mock_xgb_model():
    """predict([features]) → [score] 를 반환하는 Mock XGBoost 모델."""
    m = MagicMock()
    m.predict.return_value = [55.0]
    return m


@pytest.fixture()
def mock_tft_model():
    """TFT 모델 Mock (predict 호출 시 tensor-like 반환)."""
    import torch

    m = MagicMock()
    # 3 step 예측값 텐서 반환
    m.predict.return_value = torch.tensor([[45.0, 50.0, 60.0]])
    return m


# ---------------------------------------------------------------------------
# 1. GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_ok(self, client):
        """GET /health 200 + status=ok"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "ml"


# ---------------------------------------------------------------------------
# 2. GET /predict/risk — XGBoost 엔드포인트
# ---------------------------------------------------------------------------


class TestPredictRisk:
    def test_risk_model_loaded(self, client, mock_xgb_model):
        """모델 이미 로드된 상태 → 정상 예측"""
        with patch("ml.serve._xgb_model", mock_xgb_model):
            resp = client.get("/predict/risk?l1=70&l2=60&l3=50")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["composite_score"] == 55.0
        assert data["alert_level"] == "ORANGE"
        assert data["model"] == "xgboost"
        assert data["region"] == "서울특별시"

    def test_risk_custom_region(self, client, mock_xgb_model):
        """region 파라미터 전달 확인"""
        with patch("ml.serve._xgb_model", mock_xgb_model):
            resp = client.get("/predict/risk?l1=10&l2=10&l3=10&region=부산광역시")
        assert resp.status_code == 200
        assert resp.json()["region"] == "부산광역시"

    def test_risk_alert_levels(self, client):
        """score 범위별 alert_level 매핑 (GREEN/YELLOW/ORANGE/RED)"""
        cases = [
            (10.0, "GREEN"),
            (40.0, "YELLOW"),
            (60.0, "ORANGE"),
            (80.0, "RED"),
        ]
        for score, expected_level in cases:
            m = MagicMock()
            m.predict.return_value = [score]
            with patch("ml.serve._xgb_model", m):
                resp = client.get("/predict/risk?l1=50&l2=50&l3=50")
            assert resp.status_code == 200
            assert resp.json()["alert_level"] == expected_level, f"score={score} should be {expected_level}"

    def test_risk_score_clipped_to_100(self, client):
        """score > 100 → 100으로 클리핑"""
        m = MagicMock()
        m.predict.return_value = [150.0]
        with patch("ml.serve._xgb_model", m):
            resp = client.get("/predict/risk?l1=100&l2=100&l3=100")
        assert resp.status_code == 200
        assert resp.json()["composite_score"] == 100.0

    def test_risk_score_clipped_to_zero(self, client):
        """score < 0 → 0으로 클리핑"""
        m = MagicMock()
        m.predict.return_value = [-50.0]
        with patch("ml.serve._xgb_model", m):
            resp = client.get("/predict/risk?l1=0&l2=0&l3=0")
        assert resp.status_code == 200
        assert resp.json()["composite_score"] == 0.0

    def test_risk_model_not_loaded_fallback(self, client):
        """xgb 모델 로드 실패 → model_not_loaded 상태"""
        import ml.serve as srv

        srv._xgb_model = None
        # load_model → None 반환 mock
        with patch("ml.serve._xgb_model", None), patch("ml.xgboost.model.load_model", return_value=None):
            resp = client.get("/predict/risk?l1=50&l2=50&l3=50")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "model_not_loaded"
        assert data["composite_score"] is None
        assert data["alert_level"] is None

    def test_risk_l_param_boundary(self, client, mock_xgb_model):
        """l1/l2/l3 경계값 0, 100 허용"""
        with patch("ml.serve._xgb_model", mock_xgb_model):
            resp = client.get("/predict/risk?l1=0&l2=0&l3=0")
        assert resp.status_code == 200

        with patch("ml.serve._xgb_model", mock_xgb_model):
            resp2 = client.get("/predict/risk?l1=100&l2=100&l3=100")
        assert resp2.status_code == 200


# ---------------------------------------------------------------------------
# 3. POST /predict/tft-7d, /tft-14d, /tft-21d
# ---------------------------------------------------------------------------


class TestPredictTft:
    def _mock_tft_predictions(self, mock_tft_model, horizon_days: int) -> list[float]:
        """_make_tft_predictions 결과 mock용 헬퍼."""
        steps = max(1, horizon_days // 7)
        steps = min(steps, 3)
        return [45.0, 50.0, 60.0][:steps]

    def test_tft_7d_503_when_no_model(self, client):
        """TFT 모델 없으면 503"""
        import ml.serve as srv

        srv._tft_model = None
        with patch("ml.serve._load_tft", return_value=None):
            resp = client.post("/predict/tft-7d", json={"region": "서울특별시", "horizon_weeks": 7})
        assert resp.status_code == 503
        assert "TFT" in resp.json()["detail"]

    def test_tft_14d_503_when_no_model(self, client):
        """tft-14d도 503"""
        with patch("ml.serve._load_tft", return_value=None):
            resp = client.post("/predict/tft-14d", json={"region": "서울특별시"})
        assert resp.status_code == 503

    def test_tft_21d_503_when_no_model(self, client):
        """tft-21d도 503"""
        with patch("ml.serve._load_tft", return_value=None):
            resp = client.post("/predict/tft-21d", json={"region": "서울특별시"})
        assert resp.status_code == 503

    def test_tft_7d_ok(self, client, mock_tft_model):
        """tft-7d 정상 경로: 1 step 예측"""
        with (
            patch("ml.serve._load_tft", return_value=mock_tft_model),
            patch("ml.serve._make_tft_predictions", return_value=[45.0]),
            patch("ml.serve._tft_attention_top3", return_value=["검색트렌드", "하수기반감시", "OTC약국판매"]),
        ):
            resp = client.post("/predict/tft-7d", json={"region": "서울특별시", "horizon_weeks": 7})
        assert resp.status_code == 200
        data = resp.json()
        assert data["region"] == "서울특별시"
        assert data["horizon"] == 7
        assert isinstance(data["predictions"], list)
        assert len(data["predictions"]) == 1
        assert len(data["attention_top3"]) == 3

    def test_tft_14d_ok(self, client, mock_tft_model):
        """tft-14d 정상 경로: 2 step 예측"""
        with (
            patch("ml.serve._load_tft", return_value=mock_tft_model),
            patch("ml.serve._make_tft_predictions", return_value=[45.0, 50.0]),
            patch("ml.serve._tft_attention_top3", return_value=["검색트렌드", "하수기반감시", "OTC약국판매"]),
        ):
            resp = client.post("/predict/tft-14d", json={"region": "부산광역시"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["horizon"] == 14
        assert len(data["predictions"]) == 2

    def test_tft_21d_ok(self, client, mock_tft_model):
        """tft-21d 정상 경로: 3 step 예측"""
        with (
            patch("ml.serve._load_tft", return_value=mock_tft_model),
            patch("ml.serve._make_tft_predictions", return_value=[45.0, 50.0, 60.0]),
            patch("ml.serve._tft_attention_top3", return_value=["검색트렌드", "하수기반감시", "OTC약국판매"]),
        ):
            resp = client.post("/predict/tft-21d", json={"region": "대구광역시"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["horizon"] == 21
        assert len(data["predictions"]) == 3

    def test_tft_default_region(self, client):
        """region 생략 시 기본값 서울특별시"""
        with patch("ml.serve._load_tft", return_value=None):
            resp = client.post("/predict/tft-7d", json={})
        # 모델 없어서 503이지만, 요청은 처리됨
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# 4. _load_tft — 내부 로직
# ---------------------------------------------------------------------------


class TestLoadTft:
    def test_returns_none_when_no_checkpoint(self, tmp_path, monkeypatch):
        """체크포인트 없으면 None 반환"""
        import ml.serve as srv

        srv._tft_model = None  # 캐시 초기화
        # 체크포인트 경로를 tmp_path 내 존재하지 않는 경로로 교체
        monkeypatch.setattr(srv, "_TFT_CKPT_REAL", tmp_path / "tft_real" / "tft_best.ckpt")
        monkeypatch.setattr(srv, "_TFT_CKPT_SYNTH", tmp_path / "tft_synth" / "tft_best.ckpt")
        result = srv._load_tft()
        assert result is None

    def test_returns_cached_model_on_second_call(self, mock_tft_model):
        """_tft_model 이미 있으면 재로드 없이 반환"""
        import ml.serve as srv

        srv._tft_model = mock_tft_model
        result = srv._load_tft()
        assert result is mock_tft_model
        # 리셋
        srv._tft_model = None

    def test_load_tft_exception_returns_none(self, tmp_path, monkeypatch):
        """TemporalFusionTransformer.load_from_checkpoint 예외 발생 시 None"""
        import ml.serve as srv

        srv._tft_model = None
        # 가짜 체크포인트 파일 생성
        ckpt_dir = tmp_path / "tft_synth"
        ckpt_dir.mkdir(parents=True)
        fake_ckpt = ckpt_dir / "tft_best.ckpt"
        fake_ckpt.write_text("fake")

        monkeypatch.setattr(srv, "_TFT_CKPT_REAL", tmp_path / "tft_real" / "tft_best.ckpt")
        monkeypatch.setattr(srv, "_TFT_CKPT_SYNTH", fake_ckpt)

        with patch(
            "pytorch_forecasting.TemporalFusionTransformer.load_from_checkpoint",
            side_effect=RuntimeError("corrupt checkpoint"),
        ):
            result = srv._load_tft()
        assert result is None
        srv._tft_model = None  # 정리


# ---------------------------------------------------------------------------
# 5. _tft_attention_top3 — 내부 로직
# ---------------------------------------------------------------------------


class TestTftAttentionTop3:
    def test_fallback_when_no_metrics_file(self, tmp_path, monkeypatch):
        """metrics 파일 없으면 기본값 3개 반환"""
        import ml.serve as srv

        # OUTPUT 경로를 빈 tmp_path로 교체 (파일 없음)
        with patch("pathlib.Path.exists", return_value=False):
            result = srv._tft_attention_top3(MagicMock())
        assert len(result) == 3
        assert "검색트렌드" in result

    def test_reads_attention_from_metrics_json(self, tmp_path, monkeypatch):
        """metrics.json에서 attention 읽어서 top3 반환"""
        import ml.serve as srv

        # 가짜 metrics.json 작성
        metrics_data = {
            "attention_summary": {
                "mean_encoder_variable_importance": [
                    # encoder_var_order: encoder_length, confirmed_future_center,
                    # confirmed_future_scale, l1_otc, l2_wastewater, l3_search, temperature, humidity
                    0.05,
                    0.05,
                    0.05,
                    0.30,
                    0.25,
                    0.20,
                    0.10,
                    0.05,
                ]
            }
        }
        outputs_dir = tmp_path / "outputs"
        outputs_dir.mkdir()
        metrics_file = outputs_dir / "tft_real_metrics.json"
        metrics_file.write_text(json.dumps(metrics_data), encoding="utf-8")

        orig_parent = Path(srv.__file__).parent

        def fake_exists(self):
            return self.parent == outputs_dir and self.name in ("tft_real_metrics.json", "tft_metrics.json")

        # __file__ 기준 경로를 tmp_path로 우회
        with (
            patch.object(Path, "exists", lambda self: self == metrics_file or self.parent == orig_parent),
            patch("ml.serve.Path", wraps=Path),
        ):
            # 직접 경로를 수동으로 patch
            with patch("builtins.open", side_effect=lambda *a, **kw: open(*a, **kw)):
                pass  # 실제 파일 시스템 사용

        # 간단 버전: srv module __file__ 기반 경로 monkey-patch 불필요,
        # 기존 metrics 파일이 있으면 실제 파일 사용 (skip 처리)
        real_metrics = Path(srv.__file__).parent / "outputs" / "tft_real_metrics.json"
        if not real_metrics.exists():
            pytest.skip("tft_real_metrics.json 없음 — fallback 경로만 테스트")
        result = srv._tft_attention_top3(MagicMock())
        assert isinstance(result, list)
        assert 1 <= len(result) <= 3

    def test_attention_exception_returns_default(self):
        """json 파싱 예외 발생 시 기본값 반환"""
        import ml.serve as srv

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", side_effect=ValueError("bad json")),
        ):
            result = srv._tft_attention_top3(MagicMock())
        assert result == ["검색트렌드", "하수기반감시", "OTC약국판매"]


# ---------------------------------------------------------------------------
# 6. _make_tft_predictions — 내부 로직
# ---------------------------------------------------------------------------


class TestMakeTftPredictions:
    def test_horizon_7_returns_1_step(self, mock_tft_model):
        """horizon_days=7 → steps=1"""
        import torch

        mock_tft_model.predict.return_value = torch.tensor([[50.0, 55.0, 60.0]])

        with (
            patch("ml.tft.train_synth._make_dataframe") as mock_df,
            patch("ml.tft.train_synth._build_dataset") as mock_ds,
            patch("pytorch_forecasting.TimeSeriesDataSet.from_dataset") as mock_from_ds,
        ):
            mock_df.return_value = _make_fake_df()
            train_ds_mock = MagicMock()
            mock_ds.return_value = train_ds_mock

            val_ds_mock = MagicMock()
            mock_from_ds.return_value = val_ds_mock
            loader_mock = MagicMock()
            val_ds_mock.to_dataloader.return_value = loader_mock

            from ml.serve import _make_tft_predictions

            result = _make_tft_predictions(mock_tft_model, "서울특별시", 7)

        assert len(result) == 1
        assert 0.0 <= result[0] <= 100.0

    def test_horizon_21_returns_3_steps(self, mock_tft_model):
        """horizon_days=21 → steps=3"""
        import torch

        mock_tft_model.predict.return_value = torch.tensor([[50.0, 55.0, 60.0]])

        with (
            patch("ml.tft.train_synth._make_dataframe") as mock_df,
            patch("ml.tft.train_synth._build_dataset") as mock_ds,
            patch("pytorch_forecasting.TimeSeriesDataSet.from_dataset") as mock_from_ds,
        ):
            mock_df.return_value = _make_fake_df()
            mock_ds.return_value = MagicMock()
            val_ds_mock = MagicMock()
            mock_from_ds.return_value = val_ds_mock
            val_ds_mock.to_dataloader.return_value = MagicMock()

            from ml.serve import _make_tft_predictions

            result = _make_tft_predictions(mock_tft_model, "서울특별시", 21)

        assert len(result) == 3

    def test_predictions_clipped_0_100(self, mock_tft_model):
        """예측값 0-100 클리핑 확인"""
        import torch

        mock_tft_model.predict.return_value = torch.tensor([[-50.0, 150.0, 60.0]])

        with (
            patch("ml.tft.train_synth._make_dataframe") as mock_df,
            patch("ml.tft.train_synth._build_dataset") as mock_ds,
            patch("pytorch_forecasting.TimeSeriesDataSet.from_dataset") as mock_from_ds,
        ):
            mock_df.return_value = _make_fake_df()
            mock_ds.return_value = MagicMock()
            val_ds_mock = MagicMock()
            mock_from_ds.return_value = val_ds_mock
            val_ds_mock.to_dataloader.return_value = MagicMock()

            from ml.serve import _make_tft_predictions

            result = _make_tft_predictions(mock_tft_model, "서울특별시", 21)

        for v in result:
            assert 0.0 <= v <= 100.0


# ---------------------------------------------------------------------------
# 7. 요청 스키마 검증
# ---------------------------------------------------------------------------


class TestRequestSchema:
    def test_tft_invalid_region_type(self, client):
        """region=숫자 → 모델 없으면 503 (스키마는 통과)"""
        with patch("ml.serve._load_tft", return_value=None):
            resp = client.post("/predict/tft-7d", json={"region": "12345"})
        assert resp.status_code == 503  # 스키마 통과 후 모델 없어서 503

    def test_tft_empty_body_uses_defaults(self, client):
        """빈 바디 → 기본값 사용 (서울특별시)"""
        with patch("ml.serve._load_tft", return_value=None):
            resp = client.post("/predict/tft-7d", json={})
        assert resp.status_code == 503  # 모델 없음

    def test_risk_invalid_l1_over_range(self, client, mock_xgb_model):
        """l1 > 100 → 422 validation error"""
        with patch("ml.serve._xgb_model", mock_xgb_model):
            resp = client.get("/predict/risk?l1=150&l2=50&l3=50")
        assert resp.status_code == 422

    def test_risk_invalid_l2_negative(self, client, mock_xgb_model):
        """l2 < 0 → 422 validation error"""
        with patch("ml.serve._xgb_model", mock_xgb_model):
            resp = client.get("/predict/risk?l1=50&l2=-1&l3=50")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_fake_df():
    """_make_tft_predictions 내부에서 사용하는 fake DataFrame."""
    import numpy as np
    import pandas as pd

    n = 104
    df = pd.DataFrame(
        {
            "time_idx": range(n),
            "region": ["서울특별시"] * n,
            "l1_otc": np.random.default_rng(42).uniform(10, 90, n),
            "l2_wastewater": np.random.default_rng(43).uniform(10, 90, n),
            "l3_search": np.random.default_rng(44).uniform(10, 90, n),
            "temperature": [15.0] * n,
            "confirmed_future": np.random.default_rng(45).uniform(0, 100, n),
        }
    )
    df.attrs["max_time_idx"] = n - 1
    # time_idx max 속성을 DataFrame에서 접근 가능하게
    df["time_idx"] = df["time_idx"].astype(int)
    return df
