"""AnomalyDetector / SignalAutoencoder 단위 테스트.

CPU 고정, 최소 에폭(1~2), 소형 데이터(input_dim=4, 50샘플)로 빠르게 실행.
학습(fit) 경로도 커버하되 에폭 수를 최소화해 CI 시간을 절감한다.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

# ──────────────────────────────────────────────────────────────────────────────
# 공통 픽스처
# ──────────────────────────────────────────────────────────────────────────────

INPUT_DIM = 4
N_SAMPLES = 50


@pytest.fixture()
def normal_data() -> np.ndarray:
    """정상 범위(0~1) 합성 데이터."""
    rng = np.random.default_rng(42)
    return rng.random((N_SAMPLES, INPUT_DIM)).astype("float32")


@pytest.fixture()
def fitted_detector(normal_data: np.ndarray):
    """fit()이 완료된 AnomalyDetector 반환."""
    from ml.anomaly.autoencoder import AnomalyDetector

    det = AnomalyDetector(input_dim=INPUT_DIM, threshold_percentile=95.0)
    det.fit(normal_data, epochs=2, lr=1e-3)
    return det


# ──────────────────────────────────────────────────────────────────────────────
# SignalAutoencoder
# ──────────────────────────────────────────────────────────────────────────────


class TestSignalAutoencoder:
    def test_init_default(self) -> None:
        """기본값(input_dim=4, latent_dim=16)으로 초기화된다."""
        from ml.anomaly.autoencoder import SignalAutoencoder

        model = SignalAutoencoder()
        assert model is not None

    def test_init_custom_dims(self) -> None:
        """커스텀 input_dim=8, latent_dim=8 초기화."""
        from ml.anomaly.autoencoder import SignalAutoencoder

        model = SignalAutoencoder(input_dim=8, latent_dim=8)
        x = torch.rand(5, 8)
        out = model(x)
        assert out.shape == (5, 8)

    def test_forward_output_shape(self) -> None:
        """forward 출력 shape == 입력 shape."""
        from ml.anomaly.autoencoder import SignalAutoencoder

        model = SignalAutoencoder(input_dim=INPUT_DIM)
        x = torch.rand(10, INPUT_DIM)
        out = model(x)
        assert out.shape == (10, INPUT_DIM)

    def test_forward_output_range_sigmoid(self) -> None:
        """Decoder 마지막 레이어가 Sigmoid이므로 출력 0~1 범위."""
        from ml.anomaly.autoencoder import SignalAutoencoder

        model = SignalAutoencoder(input_dim=INPUT_DIM)
        x = torch.rand(20, INPUT_DIM)
        out = model(x)
        assert float(out.min()) >= 0.0
        assert float(out.max()) <= 1.0

    def test_reconstruction_error_shape(self) -> None:
        """reconstruction_error 반환 텐서 shape == (batch_size,)."""
        from ml.anomaly.autoencoder import SignalAutoencoder

        model = SignalAutoencoder(input_dim=INPUT_DIM)
        x = torch.rand(15, INPUT_DIM)
        err = model.reconstruction_error(x)
        assert err.shape == (15,)

    def test_reconstruction_error_nonnegative(self) -> None:
        """재구성 오차는 항상 0 이상이다."""
        from ml.anomaly.autoencoder import SignalAutoencoder

        model = SignalAutoencoder(input_dim=INPUT_DIM)
        x = torch.rand(10, INPUT_DIM)
        err = model.reconstruction_error(x)
        assert bool((err >= 0).all())

    def test_reconstruction_error_no_grad(self) -> None:
        """reconstruction_error는 torch.no_grad() 내에서 실행된다 (그라디언트 없음)."""
        from ml.anomaly.autoencoder import SignalAutoencoder

        model = SignalAutoencoder(input_dim=INPUT_DIM)
        x = torch.rand(5, INPUT_DIM)
        err = model.reconstruction_error(x)
        assert not err.requires_grad


# ──────────────────────────────────────────────────────────────────────────────
# AnomalyDetector — 초기화
# ──────────────────────────────────────────────────────────────────────────────


class TestAnomalyDetectorInit:
    def test_init_default(self) -> None:
        """기본 input_dim=4, threshold_percentile=95.0 초기화."""
        from ml.anomaly.autoencoder import AnomalyDetector

        det = AnomalyDetector()
        assert det.threshold is None
        assert det.threshold_percentile == 95.0

    def test_init_custom_percentile(self) -> None:
        """99th percentile 설정."""
        from ml.anomaly.autoencoder import AnomalyDetector

        det = AnomalyDetector(threshold_percentile=99.0)
        assert det.threshold_percentile == 99.0

    def test_model_is_signal_autoencoder(self) -> None:
        """내부 model이 SignalAutoencoder 타입이다."""
        from ml.anomaly.autoencoder import AnomalyDetector, SignalAutoencoder

        det = AnomalyDetector(input_dim=INPUT_DIM)
        assert isinstance(det.model, SignalAutoencoder)


# ──────────────────────────────────────────────────────────────────────────────
# AnomalyDetector — fit()
# ──────────────────────────────────────────────────────────────────────────────


class TestAnomalyDetectorFit:
    def test_fit_sets_threshold(self, normal_data: np.ndarray) -> None:
        """fit 완료 후 threshold가 float으로 설정된다."""
        from ml.anomaly.autoencoder import AnomalyDetector

        det = AnomalyDetector(input_dim=INPUT_DIM)
        det.fit(normal_data, epochs=2)
        assert isinstance(det.threshold, float)
        assert det.threshold > 0.0

    def test_fit_returns_loss_list(self, normal_data: np.ndarray) -> None:
        """fit은 에폭 수와 동일한 길이의 손실 리스트를 반환한다."""
        from ml.anomaly.autoencoder import AnomalyDetector

        det = AnomalyDetector(input_dim=INPUT_DIM)
        losses = det.fit(normal_data, epochs=3)
        assert len(losses) == 3
        assert all(isinstance(loss, float) for loss in losses)

    def test_fit_losses_are_positive(self, normal_data: np.ndarray) -> None:
        """손실값은 모두 양수이다."""
        from ml.anomaly.autoencoder import AnomalyDetector

        det = AnomalyDetector(input_dim=INPUT_DIM)
        losses = det.fit(normal_data, epochs=2)
        assert all(loss > 0 for loss in losses)

    def test_fit_99th_percentile_threshold(self, normal_data: np.ndarray) -> None:
        """threshold_percentile=99 적용: threshold가 95p보다 크거나 같다."""
        from ml.anomaly.autoencoder import AnomalyDetector

        rng = np.random.default_rng(0)
        data = rng.random((N_SAMPLES, INPUT_DIM)).astype("float32")

        det95 = AnomalyDetector(input_dim=INPUT_DIM, threshold_percentile=95.0)
        det99 = AnomalyDetector(input_dim=INPUT_DIM, threshold_percentile=99.0)

        # 동일 모델 가중치 사용을 위해 동일 seed로 재초기화
        torch.manual_seed(42)
        det95.fit(data, epochs=1)
        torch.manual_seed(42)
        det99.fit(data, epochs=1)

        assert det99.threshold >= det95.threshold  # 99p >= 95p


# ──────────────────────────────────────────────────────────────────────────────
# AnomalyDetector — predict()
# ──────────────────────────────────────────────────────────────────────────────


class TestAnomalyDetectorPredict:
    def test_predict_requires_fit_first(self, normal_data: np.ndarray) -> None:
        """fit() 전에 predict() 호출하면 RuntimeError 발생."""
        from ml.anomaly.autoencoder import AnomalyDetector

        det = AnomalyDetector(input_dim=INPUT_DIM)
        with pytest.raises(RuntimeError, match="fit"):
            det.predict(normal_data)

    def test_predict_returns_dict_keys(self, fitted_detector, normal_data: np.ndarray) -> None:
        """predict 결과 딕셔너리가 4개 필수 키를 포함한다."""
        result = fitted_detector.predict(normal_data)
        assert set(result.keys()) == {"is_anomaly", "reconstruction_error", "threshold", "error_series"}

    def test_predict_is_anomaly_is_bool(self, fitted_detector, normal_data: np.ndarray) -> None:
        """is_anomaly 값이 Python bool 타입이다."""
        result = fitted_detector.predict(normal_data)
        assert isinstance(result["is_anomaly"], bool)

    def test_predict_reconstruction_error_is_float(self, fitted_detector, normal_data: np.ndarray) -> None:
        """reconstruction_error가 float 타입이다."""
        result = fitted_detector.predict(normal_data)
        assert isinstance(result["reconstruction_error"], float)

    def test_predict_threshold_matches_fit(self, fitted_detector, normal_data: np.ndarray) -> None:
        """predict 결과의 threshold가 fit 시 계산한 threshold와 일치한다."""
        result = fitted_detector.predict(normal_data)
        assert result["threshold"] == pytest.approx(fitted_detector.threshold)

    def test_predict_error_series_length(self, fitted_detector, normal_data: np.ndarray) -> None:
        """error_series 길이 == 입력 샘플 수."""
        result = fitted_detector.predict(normal_data)
        assert len(result["error_series"]) == N_SAMPLES

    def test_predict_normal_data_mostly_not_anomaly(self, fitted_detector, normal_data: np.ndarray) -> None:
        """정상 데이터의 마지막 샘플은 대부분 이상이 아니다 (확률적이므로 error_series 확인)."""
        result = fitted_detector.predict(normal_data)
        # error_series 전체 평균이 threshold보다 낮아야 정상 데이터 학습이 올바른 것
        avg_error = sum(result["error_series"]) / len(result["error_series"])
        assert avg_error < result["threshold"] * 2  # 느슨한 검증

    def test_predict_anomaly_detected_with_spike(self, fitted_detector) -> None:
        """정상 범위를 크게 벗어난 데이터(spike)는 이상으로 탐지될 가능성이 높다."""

        # 완전히 다른 분포: 매우 큰 값
        spike_data = np.full((5, INPUT_DIM), 100.0, dtype="float32")

        # threshold를 매우 낮게 수동 설정해 강제 이상 탐지 테스트
        fitted_detector.threshold = 1e-10
        result = fitted_detector.predict(spike_data)
        assert result["is_anomaly"] is True

    def test_predict_is_anomaly_uses_last_sample(self, fitted_detector, normal_data: np.ndarray) -> None:
        """is_anomaly는 error_series의 마지막 값과 threshold를 비교한다."""
        result = fitted_detector.predict(normal_data)
        last_error = result["error_series"][-1]
        expected = last_error > result["threshold"]
        assert result["is_anomaly"] == expected

    def test_predict_single_sample(self, fitted_detector) -> None:
        """입력이 1개 샘플이어도 오류 없이 동작한다."""
        rng = np.random.default_rng(7)
        single = rng.random((1, INPUT_DIM)).astype("float32")
        result = fitted_detector.predict(single)
        assert len(result["error_series"]) == 1

    def test_predict_large_batch(self, fitted_detector) -> None:
        """200개 배치 추론도 오류 없이 동작한다."""
        rng = np.random.default_rng(99)
        large = rng.random((200, INPUT_DIM)).astype("float32")
        result = fitted_detector.predict(large)
        assert len(result["error_series"]) == 200
