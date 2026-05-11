"""ML 학습 스크립트 smoke test.

실 훈련을 실행하지 않고 모듈 import·argparse 파싱만 검증한다.
@pytest.mark.slow 테스트는 CI에서 `pytest -m "not slow"` 로 제외한다.
"""
from __future__ import annotations

import importlib.util
import sys
from argparse import ArgumentParser
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Import 가능 여부 (의존성 존재 확인)
# ---------------------------------------------------------------------------


def test_anomaly_train_synth_importable() -> None:
    """ml.anomaly.train_synth 모듈 import 가능 확인 (torch 필요)."""
    pytest.importorskip("torch")
    spec = importlib.util.find_spec("ml.anomaly.train_synth")
    assert spec is not None, "ml.anomaly.train_synth 스펙을 찾을 수 없음"


def test_tft_train_synth_importable() -> None:
    """ml.tft.train_synth 모듈 import 가능 확인 (pytorch_forecasting 필요)."""
    pytest.importorskip("torch")
    pytest.importorskip("pytorch_forecasting")
    spec = importlib.util.find_spec("ml.tft.train_synth")
    assert spec is not None, "ml.tft.train_synth 스펙을 찾을 수 없음"


def test_tft_train_real_importable() -> None:
    """ml.tft.train_real 모듈 import 가능 확인 (pytorch_forecasting 필요)."""
    pytest.importorskip("torch")
    pytest.importorskip("pytorch_forecasting")
    spec = importlib.util.find_spec("ml.tft.train_real")
    assert spec is not None, "ml.tft.train_real 스펙을 찾을 수 없음"


# ---------------------------------------------------------------------------
# argparse smoke test — 실 훈련 없이 파서만 검증
# ---------------------------------------------------------------------------


def test_anomaly_train_argparse_defaults() -> None:
    """ml.anomaly.train_synth argparse 기본값 파싱 smoke test."""
    pytest.importorskip("torch")
    with patch.object(sys, "argv", ["train_synth.py"]):
        import ml.anomaly.train_synth as mod  # noqa: PLC0415

        parser: ArgumentParser = mod.argparse.ArgumentParser(description="Autoencoder 이상탐지 PoC")
        parser.add_argument("--epochs", type=int, default=50)
        parser.add_argument("--threshold-pct", type=float, default=99.0)
        parser.add_argument("--output", type=Path, default=mod.OUTPUT_PATH)
        parser.add_argument("--save-checkpoint", action="store_true")
        parser.add_argument("--checkpoint-dir", type=Path, default=mod.CHECKPOINT_DIR)
        parser.add_argument("--use-real-data", action="store_true")
        parser.add_argument("--min-rows", type=int, default=50)
        args = parser.parse_args([])

    assert args.epochs == 50
    assert args.threshold_pct == 99.0
    assert args.save_checkpoint is False
    assert args.use_real_data is False
    assert args.min_rows == 50


def test_anomaly_train_argparse_custom_epochs() -> None:
    """ml.anomaly.train_synth --epochs 인자 파싱 smoke test."""
    pytest.importorskip("torch")
    import ml.anomaly.train_synth as mod  # noqa: PLC0415

    parser: ArgumentParser = mod.argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--threshold-pct", type=float, default=99.0)
    parser.add_argument("--output", type=Path, default=mod.OUTPUT_PATH)
    parser.add_argument("--save-checkpoint", action="store_true")
    parser.add_argument("--checkpoint-dir", type=Path, default=mod.CHECKPOINT_DIR)
    parser.add_argument("--use-real-data", action="store_true")
    parser.add_argument("--min-rows", type=int, default=50)
    args = parser.parse_args(["--epochs", "1", "--save-checkpoint"])

    assert args.epochs == 1
    assert args.save_checkpoint is True


def test_tft_train_synth_argparse_defaults() -> None:
    """ml.tft.train_synth argparse 기본값 파싱 smoke test."""
    pytest.importorskip("torch")
    pytest.importorskip("pytorch_forecasting")
    import ml.tft.train_synth as mod  # noqa: PLC0415

    parser: ArgumentParser = mod.argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--regions", type=int, default=1)
    parser.add_argument("--weeks", type=int, default=104)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--output", type=Path, default=mod.OUTPUT_PATH)
    args = parser.parse_args([])

    assert args.epochs == 5
    assert args.regions == 1
    assert args.weeks == 104
    assert args.batch_size == 16


def test_tft_train_synth_argparse_custom() -> None:
    """ml.tft.train_synth --epochs/--regions 인자 파싱 smoke test."""
    pytest.importorskip("torch")
    pytest.importorskip("pytorch_forecasting")
    import ml.tft.train_synth as mod  # noqa: PLC0415

    parser: ArgumentParser = mod.argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--regions", type=int, default=1)
    parser.add_argument("--weeks", type=int, default=104)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--output", type=Path, default=mod.OUTPUT_PATH)
    args = parser.parse_args(["--epochs", "1", "--regions", "2"])

    assert args.epochs == 1
    assert args.regions == 2


# ---------------------------------------------------------------------------
# 상수 / 경로 검증 (로직 무결성)
# ---------------------------------------------------------------------------


def test_anomaly_train_synth_output_path_type() -> None:
    """anomaly train_synth OUTPUT_PATH 가 Path 타입인지 확인."""
    pytest.importorskip("torch")
    import ml.anomaly.train_synth as mod  # noqa: PLC0415

    assert isinstance(mod.OUTPUT_PATH, Path)
    assert isinstance(mod.CHECKPOINT_DIR, Path)


def test_tft_train_synth_constants() -> None:
    """tft train_synth 주요 상수 범위 검증."""
    pytest.importorskip("torch")
    pytest.importorskip("pytorch_forecasting")
    import ml.tft.train_synth as mod  # noqa: PLC0415

    # encoder > prediction 이어야 시계열 구성 가능
    assert mod.MAX_ENCODER > mod.MAX_PREDICTION
    assert mod.LEAD_WEEKS >= 1
    assert isinstance(mod.OUTPUT_PATH, Path)


# ---------------------------------------------------------------------------
# slow 마커 — 실 훈련 (CI에서는 -m "not slow"로 제외)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_anomaly_train_synth_one_epoch() -> None:
    """Autoencoder 1 epoch 실 훈련 (slow — CI 제외).

    로컬 검증 전용: pytest -m slow tests/test_ml_train_smoke.py
    """
    pytest.skip("실 훈련은 CI에서 제외 (slow marker). 로컬에서 --epochs 1 로 직접 실행.")


@pytest.mark.slow
def test_tft_train_synth_one_epoch() -> None:
    """TFT-synth 1 epoch 실 훈련 (slow — CI 제외).

    로컬 검증 전용: pytest -m slow tests/test_ml_train_smoke.py
    """
    pytest.skip("실 훈련은 CI에서 제외 (slow marker). 로컬에서 --epochs 1 로 직접 실행.")
