"""통합 테스트: /api/v1/predictions/anomaly Autoencoder 엔드포인트 검증.

케이스:
  1. 체크포인트 부재 시 503 반환
  2. 체크포인트 존재 시 200 + anomaly_scores 17개 반환
  3. reconstruction_error > threshold 케이스 → status="anomaly"
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
import torch


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼: mock AsyncSession (risk_scores / layer_signals 빈 결과 반환)
# ──────────────────────────────────────────────────────────────────────────────

def _make_empty_session() -> AsyncMock:
    """risk_scores 및 layer_signals 둘 다 빈 행 반환하는 mock session."""

    class _FakeResult:
        def mappings(self):
            return self
        def all(self):
            return []

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_FakeResult())
    return session


# ──────────────────────────────────────────────────────────────────────────────
# 케이스 1 — 체크포인트 없으면 503
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_anomaly_503_when_no_checkpoint(tmp_path: Path) -> None:
    """체크포인트 디렉토리가 비어있으면 503 HTTPException 반환."""
    from fastapi import HTTPException

    # 체크포인트 없는 빈 디렉토리로 패치
    with patch(
        "backend.app.api.predictions._CKPT_DIR",
        tmp_path / "autoencoder",
    ), patch(
        "backend.app.api.predictions._AUTOENCODER_CACHE",
        None,  # 미시도 상태로 초기화
    ):
        # 전역 캐시를 None으로 강제 리셋
        import backend.app.api.predictions as pred_module
        pred_module._AUTOENCODER_CACHE = None

        from backend.app.api.predictions import get_anomaly_scores

        with pytest.raises(HTTPException) as exc_info:
            await get_anomaly_scores(db=_make_empty_session())
        assert exc_info.value.status_code == 503
        assert "train_synth" in exc_info.value.detail


# ──────────────────────────────────────────────────────────────────────────────
# 케이스 2 — 체크포인트 존재 시 200 + 17개 지역
# ──────────────────────────────────────────────────────────────────────────────

def _make_fake_cache() -> dict[str, Any]:
    """실제 SignalAutoencoder 인스턴스를 사용하는 fake cache (학습 없이 초기화된 가중치)."""
    from ml.anomaly.autoencoder import SignalAutoencoder
    model = SignalAutoencoder(input_dim=4)
    model.eval()
    return {
        "model": model,
        "threshold": 0.05,
        "threshold_percentile": 95.0,
        "X_min": np.array([0.0, 0.0, 0.0, 10.0], dtype=np.float32),
        "X_max": np.array([100.0, 100.0, 100.0, 35.0], dtype=np.float32),
        "feature_cols": ["l1_otc", "l2_wastewater", "l3_search", "temperature"],
    }


@pytest.mark.asyncio
async def test_anomaly_200_returns_17_regions() -> None:
    """체크포인트 캐시 주입 시 200 + anomaly_scores 17개 반환."""
    import backend.app.api.predictions as pred_module

    # 싱글톤 캐시를 fake cache로 주입
    original_cache = pred_module._AUTOENCODER_CACHE
    pred_module._AUTOENCODER_CACHE = _make_fake_cache()

    try:
        from backend.app.api.predictions import get_anomaly_scores, _KR_REGIONS

        result = await get_anomaly_scores(db=_make_empty_session())

        assert result["model"] == "autoencoder"
        assert "threshold" in result
        assert "generated_at" in result
        scores = result["anomaly_scores"]
        assert len(scores) == 17, f"17개 지역이어야 하는데 {len(scores)}개"
        region_names = [s["region"] for s in scores]
        for region in _KR_REGIONS:
            assert region in region_names, f"{region}이 응답에 없음"
        # 각 항목 필드 확인
        first = scores[0]
        assert "score" in first
        assert "reconstruction_error" in first
        assert first["status"] in ("anomaly", "warning", "normal")
        assert "features" in first
        assert "fallback_temperature" in first
    finally:
        pred_module._AUTOENCODER_CACHE = original_cache


# ──────────────────────────────────────────────────────────────────────────────
# 케이스 3 — reconstruction_error > threshold → status="anomaly"
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_anomaly_status_when_error_exceeds_threshold() -> None:
    """model이 큰 reconstruction_error를 반환할 때 status='anomaly' 확인."""
    import backend.app.api.predictions as pred_module

    # reconstruction_error를 threshold의 2배로 강제 반환하는 mock model
    class _HighErrorModel:
        def eval(self):
            return self
        def reconstruction_error(self, tensor: torch.Tensor) -> torch.Tensor:
            # 모든 샘플에 대해 threshold * 2.0 반환
            return torch.full((tensor.shape[0],), 0.10)  # threshold=0.05 의 2배

    fake_cache: dict[str, Any] = {
        "model": _HighErrorModel(),
        "threshold": 0.05,
        "threshold_percentile": 95.0,
        "X_min": np.array([0.0, 0.0, 0.0, 10.0], dtype=np.float32),
        "X_max": np.array([100.0, 100.0, 100.0, 35.0], dtype=np.float32),
        "feature_cols": ["l1_otc", "l2_wastewater", "l3_search", "temperature"],
    }

    original_cache = pred_module._AUTOENCODER_CACHE
    pred_module._AUTOENCODER_CACHE = fake_cache

    try:
        from backend.app.api.predictions import get_anomaly_scores

        result = await get_anomaly_scores(db=_make_empty_session())
        scores = result["anomaly_scores"]
        # 모든 지역이 anomaly 상태여야 함 (error 0.10 > threshold 0.05)
        for s in scores:
            assert s["status"] == "anomaly", (
                f"{s['region']} status={s['status']}, error={s['reconstruction_error']}"
            )
        # score = min(0.10 / 0.05 * 50, 100) = 100
        for s in scores:
            assert s["score"] == 100.0
    finally:
        pred_module._AUTOENCODER_CACHE = original_cache
