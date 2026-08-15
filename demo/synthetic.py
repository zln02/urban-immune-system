"""합성 신호 생성기 — 데모 전용.

이 모듈은 **실제 데이터를 일절 읽지 않는다.** 약국 OTC·하수 바이오마커·검색
트렌드 3계층을 흉내 낸 시계열을 난수로 만들어낼 뿐이다. 고정 시드를 쓰므로
같은 입력이면 항상 같은 그림이 나온다.

실제 파이프라인(`pipeline/`, `ml/`, `backend/`)과는 아무런 코드도 공유하지
않는다. 데모가 본 저장소의 운영 코드에 영향을 주지 않게 하기 위해서다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# 백테스트 산출물(analysis/outputs/backtest_17regions.json)과 동일한 17개 시·도.
# 이름만 빌려온 것이고, 값은 전부 합성이다.
REGIONS: list[str] = [
    "서울특별시",
    "경기도",
    "부산광역시",
    "인천광역시",
    "대구광역시",
    "대전광역시",
    "광주광역시",
    "울산광역시",
    "세종특별자치시",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]

# 실제 게이트 설정과 같은 값을 쓴다.
# 출처: analysis/outputs/backtest_17regions.json → gate_config
GATE_MIN_LAYERS = 2
GATE_LAYER_THRESHOLD = 30.0
RED_THRESHOLD = 75.0

# 계층별 선행 주수 — README의 "단독 선행" 표를 재현한 것이다.
# L1 약국 OTC 8주 · L2 하수 2주 · L3 검색 3주
LAYER_LEAD_WEEKS: dict[str, int] = {"L1": 8, "L2": 2, "L3": 3}

LAYER_LABELS: dict[str, str] = {
    "L1": "💊 L1 약국 OTC",
    "L2": "🚰 L2 하수 바이오마커",
    "L3": "🔍 L3 검색 트렌드",
}

# Okabe-Ito 색맹 안전 팔레트 (본 저장소 src/config.py와 같은 값)
LAYER_COLORS: dict[str, str] = {"L1": "#D55E00", "L2": "#0072B2", "L3": "#009E73"}


@dataclass(frozen=True)
class DemoConfig:
    """데모 시계열 생성 파라미터."""

    weeks: int = 104
    seed: int = 20260815
    noise: float = 6.0


def _latent_outbreak(weeks: int, rng: np.random.Generator, phase: float) -> np.ndarray:
    """실제 유행 곡선을 대신할 잠재 신호를 만든다.

    겨울철 정점을 갖는 계절 성분에 완만한 추세와 잡음을 얹는다.
    이 곡선이 '임상 신고'에 해당하고, 각 계층은 이 곡선을 앞당겨 관측한 것으로
    취급한다.
    """
    t = np.arange(weeks)
    seasonal = 45 + 38 * np.sin(2 * np.pi * (t / 52.0) + phase)
    drift = np.linspace(0, 6, weeks)
    wobble = rng.normal(0, 3.0, weeks).cumsum() * 0.25
    return np.clip(seasonal + drift + wobble, 0, 100)


def _shift_forward(series: np.ndarray, lead: int) -> np.ndarray:
    """계층 신호가 임상보다 `lead` 주 앞서 움직이도록 당긴다."""
    if lead <= 0:
        return series.copy()
    return np.concatenate([series[lead:], np.repeat(series[-1], lead)])


def build_region_frame(region: str, cfg: DemoConfig | None = None) -> pd.DataFrame:
    """한 지역의 3계층 합성 시계열을 만든다.

    Args:
        region: 지역명. 시드를 흔드는 용도로만 쓰인다.
        cfg: 생성 파라미터.

    Returns:
        week / clinical / L1 / L2 / L3 / composite / gate_layers / alert 컬럼을
        가진 DataFrame.
    """
    cfg = cfg or DemoConfig()
    # 지역명을 시드에 섞어 지역마다 다른 곡선이 나오되, 실행할 때마다는 같게 한다.
    rng = np.random.default_rng(cfg.seed + (abs(hash(region)) % 10_000))
    phase = rng.uniform(0, 2 * np.pi)

    clinical = _latent_outbreak(cfg.weeks, rng, phase)

    frame = pd.DataFrame(
        {
            "week": pd.date_range("2024-09-02", periods=cfg.weeks, freq="7D"),
            "clinical": clinical,
        }
    )

    for layer, lead in LAYER_LEAD_WEEKS.items():
        shifted = _shift_forward(clinical, lead)
        observed = shifted + rng.normal(0, cfg.noise, cfg.weeks)
        frame[layer] = np.clip(observed, 0, 100)

    # 단일 계층 급등 이벤트를 심는다.
    # 실제로 조기경보를 망가뜨리는 건 유행이 아니라 이런 잡음이다 — 언론 보도로
    # 검색량만 폭증하거나(L3), 할인 행사로 약국 판매만 뛰는(L1) 경우.
    # Google Flu Trends가 과대예측으로 실패한 지점이 정확히 여기다.
    # 유행이 잠잠한 구간에만 심어야 "단독 신호"가 된다.
    frame["spike_layer"] = ""
    quiet = np.where(clinical < 35)[0]
    quiet = quiet[(quiet > 2) & (quiet < cfg.weeks - 2)]
    if len(quiet) > 0:
        n_spikes = min(3, len(quiet))
        for idx in rng.choice(quiet, size=n_spikes, replace=False):
            layer = str(rng.choice(["L1", "L3"]))  # 검색·OTC가 특히 잘 튄다
            frame.loc[idx, layer] = float(rng.uniform(82, 97))
            frame.loc[idx, "spike_layer"] = layer

    # 3계층 가중 융합
    frame["composite"] = (
        0.40 * frame["L1"] + 0.30 * frame["L2"] + 0.30 * frame["L3"]
    ).round(2)

    # 게이트를 끈 상태의 순진한 규칙 — "어느 한 계층이라도 경보 임계를 넘으면
    # 발령". 단일 신호만 믿는 방식이며, 위에서 심은 급등에 그대로 걸린다.
    frame["alert_raw"] = frame[["L1", "L2", "L3"]].max(axis=1) >= RED_THRESHOLD

    # Gate B — 임계를 넘긴 계층 수를 센다. 최소 2개가 함께 올라야 경보를 낸다.
    over = (frame[["L1", "L2", "L3"]] >= GATE_LAYER_THRESHOLD).sum(axis=1)
    frame["gate_layers"] = over
    frame["alert"] = frame["alert_raw"] & (over >= GATE_MIN_LAYERS)

    return frame


def build_region_summary(cfg: DemoConfig | None = None) -> pd.DataFrame:
    """17개 지역의 최근 시점 위험도 요약."""
    cfg = cfg or DemoConfig()
    rows = []
    for region in REGIONS:
        frame = build_region_frame(region, cfg)
        last = frame.iloc[-1]
        rows.append(
            {
                "지역": region,
                "종합 위험도": round(float(last["composite"]), 1),
                "L1": round(float(last["L1"]), 1),
                "L2": round(float(last["L2"]), 1),
                "L3": round(float(last["L3"]), 1),
                "게이트 통과 계층": int(last["gate_layers"]),
                "경보": "🔴 발령" if bool(last["alert"]) else "🟢 정상",
            }
        )
    return pd.DataFrame(rows).sort_values("종합 위험도", ascending=False, ignore_index=True)


def gate_effect(cfg: DemoConfig | None = None) -> dict[str, int]:
    """게이트를 켰을 때와 껐을 때 경보 건수를 센다.

    Google Flu Trends 실패의 교훈 — 단일 계층 단독 경보를 막는 것 — 을
    합성 데이터 위에서 눈으로 확인시키기 위한 집계다. 실제 성능 수치가 아니다.
    """
    cfg = cfg or DemoConfig()
    raw = blocked = 0
    for region in REGIONS:
        frame = build_region_frame(region, cfg)
        raw += int(frame["alert_raw"].sum())
        blocked += int((frame["alert_raw"] & ~frame["alert"]).sum())
    return {"gate_off": raw, "blocked": blocked, "gate_on": raw - blocked}
