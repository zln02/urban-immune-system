"""Deep Autoencoder 기반 이상탐지 모델.

각 Layer 신호를 재구성하여 reconstruction error가 임계값을 초과할 때
이상(anomaly)으로 판정한다. 라벨 없이 학습 가능한 비지도 방식.

아키텍처: Encoder(64→32→16) + Decoder(16→32→64→input_dim)
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


class SignalAutoencoder(nn.Module):
    def __init__(self, input_dim: int = 4, latent_dim: int = 16) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, latent_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            recon = self.forward(x)
            return torch.mean((recon - x) ** 2, dim=1)


class AnomalyDetector:
    """Autoencoder 학습·추론 래퍼."""

    def __init__(self, input_dim: int = 4, threshold_percentile: float = 95.0) -> None:
        self.model = SignalAutoencoder(input_dim)
        self.threshold: float | None = None
        self.threshold_percentile = threshold_percentile

    def fit(self, X: np.ndarray, epochs: int = 50, lr: float = 1e-3) -> list[float]:
        """정상 데이터로 Autoencoder를 학습한다. 학습 손실 리스트 반환."""
        tensor = torch.FloatTensor(X)
        loader = DataLoader(TensorDataset(tensor), batch_size=32, shuffle=True)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        self.model.train()
        losses: list[float] = []
        for _ in range(epochs):
            epoch_loss = 0.0
            for (batch,) in loader:
                optimizer.zero_grad()
                recon = self.model(batch)
                loss = criterion(recon, batch)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            losses.append(epoch_loss / len(loader))

        # 학습 데이터 기반 임계값 설정
        self.model.eval()
        errors = self.model.reconstruction_error(tensor).numpy()
        self.threshold = float(np.percentile(errors, self.threshold_percentile))
        return losses

    def predict(self, X: np.ndarray) -> dict:
        """이상 여부와 reconstruction error를 반환한다."""
        if self.threshold is None:
            raise RuntimeError("fit()을 먼저 호출하세요")
        self.model.eval()
        tensor = torch.FloatTensor(X)
        errors = self.model.reconstruction_error(tensor).numpy()
        return {
            "is_anomaly": bool(errors[-1] > self.threshold),
            "reconstruction_error": float(errors[-1]),
            "threshold": self.threshold,
            "error_series": errors.tolist(),
        }
