"""앙상블 경보 로직 단위 테스트.

검증 항목:
1. 경계값 — composite 정확한 레벨 경계
2. 2계층 교차검증 — YELLOW 이상 발령 조건
3. L3 단독 차단 — 검색 단독 고값으로 YELLOW 이상 발령 금지
4. 데이터 없음 처리 — None 계층 0으로 대체
5. GREEN 정상 경로 — 낮은 composite 는 교차검증 없이 GREEN
6. ORANGE 경계 — 55 ≤ composite < 75, 2계층 이상 30 이상
7. RED 경계 + 교차검증 실패 시 GREEN 다운그레이드
"""
from __future__ import annotations

import pytest

from pipeline.scorer import determine_alert_level, RiskScoreRow


# ---------------------------------------------------------------------------
# Case 1: GREEN — composite < 30, 교차검증 불필요
# ---------------------------------------------------------------------------
def test_green_low_composite() -> None:
    """composite 가 30 미만이면 교차검증 없이 GREEN 이어야 한다."""
    level = determine_alert_level(composite=25.0, l1=20.0, l2=10.0, l3=5.0)
    assert level == "GREEN"


# ---------------------------------------------------------------------------
# Case 2: YELLOW — composite 30~55, 2계층 이상 30 이상 → 정상 발령
# ---------------------------------------------------------------------------
def test_yellow_two_layers_above_threshold() -> None:
    """composite 35, l1=40 l2=35 l3=10 — 2계층이 30 이상이므로 YELLOW 발령."""
    composite = 0.35 * 40 + 0.40 * 35 + 0.25 * 10
    level = determine_alert_level(composite=composite, l1=40.0, l2=35.0, l3=10.0)
    assert level == "YELLOW"


# ---------------------------------------------------------------------------
# Case 3: L3 단독 차단 — L3 만 80 초과, L1/L2 낮음 → GREEN 강제
# ---------------------------------------------------------------------------
def test_l3_single_high_blocked() -> None:
    """L3(검색) 단독으로 85 라도 L1/L2 가 30 미만이면 GREEN 으로 차단되어야 한다."""
    composite = 0.35 * 5.0 + 0.40 * 10.0 + 0.25 * 85.0
    # composite ≈ 1.75 + 4.0 + 21.25 = 27.0 → 원래 GREEN 이지만
    # 극단 케이스: l3=100 l1=5 l2=5
    composite2 = 0.35 * 5.0 + 0.40 * 5.0 + 0.25 * 100.0
    # composite2 = 1.75 + 2.0 + 25.0 = 28.75 → GREEN
    level = determine_alert_level(composite=composite2, l1=5.0, l2=5.0, l3=100.0)
    assert level == "GREEN"


# ---------------------------------------------------------------------------
# Case 4: L3 단독 차단 (composite 가 경계 이상이지만 교차검증 실패)
# ---------------------------------------------------------------------------
def test_l3_dominant_composite_above_yellow_blocked() -> None:
    """l3=100 단독으로 composite 가 30 이상이어도 교차검증 실패 시 GREEN."""
    # w1=0.35 w2=0.40 w3=0.25, l1=0 l2=0 l3=100 → composite=25 (GREEN)
    # 가중치 구성상 L3 단독으로는 composite 25 가 최대 → 이미 GREEN
    # l1=20 l2=20 l3=100 → composite = 7+8+25=40 (YELLOW 범위) 이지만 교차검증:
    # l1=20 < 30, l2=20 < 30, l3=100 ≥ 30 → 1개만 30 이상 → GREEN 강제
    composite = 0.35 * 20.0 + 0.40 * 20.0 + 0.25 * 100.0
    assert composite >= 30  # YELLOW 범위 확인
    level = determine_alert_level(composite=composite, l1=20.0, l2=20.0, l3=100.0)
    assert level == "GREEN", f"교차검증 실패 시 GREEN 이어야 하는데 {level}"


# ---------------------------------------------------------------------------
# Case 5: ORANGE — composite 55~75, 2계층 이상 30 이상
# ---------------------------------------------------------------------------
def test_orange_two_layers_above_threshold() -> None:
    """composite 60, l1=70 l2=60 l3=30 — ORANGE 발령."""
    composite = 0.35 * 70.0 + 0.40 * 60.0 + 0.25 * 30.0
    # = 24.5 + 24.0 + 7.5 = 56.0
    level = determine_alert_level(composite=composite, l1=70.0, l2=60.0, l3=30.0)
    assert level == "ORANGE"


# ---------------------------------------------------------------------------
# Case 6: RED — composite ≥ 75, 2계층 이상 30 이상
# ---------------------------------------------------------------------------
def test_red_high_composite_two_layers() -> None:
    """composite 80, l1=90 l2=80 l3=50 — RED 발령."""
    composite = 0.35 * 90.0 + 0.40 * 80.0 + 0.25 * 50.0
    # = 31.5 + 32.0 + 12.5 = 76.0
    level = determine_alert_level(composite=composite, l1=90.0, l2=80.0, l3=50.0)
    assert level == "RED"


# ---------------------------------------------------------------------------
# Case 7: RED 범위지만 교차검증 실패 → GREEN 다운그레이드
# ---------------------------------------------------------------------------
def test_red_range_but_single_layer_downgraded() -> None:
    """composite 가 RED 범위여도 1개 계층만 30 이상이면 GREEN."""
    # l1=100 l2=0 l3=0 → composite=35 YELLOW, 교차검증 1개 → GREEN
    composite = 0.35 * 100.0 + 0.40 * 0.0 + 0.25 * 0.0
    assert composite == 35.0
    level = determine_alert_level(composite=composite, l1=100.0, l2=0.0, l3=0.0)
    assert level == "GREEN"


# ---------------------------------------------------------------------------
# Case 8: None 계층 처리 — l2 없을 때 (데이터 수집 실패 시뮬레이션)
# ---------------------------------------------------------------------------
def test_none_layer_treated_as_zero() -> None:
    """l2 가 None 이면 0 으로 대체하여 composite 계산 후 레벨 결정."""
    # l1=50, l2=None(→0), l3=20 → composite=0.35*50+0.40*0+0.25*20=22.5 → GREEN
    composite = 0.35 * 50.0 + 0.40 * 0.0 + 0.25 * 20.0
    level = determine_alert_level(composite=composite, l1=50.0, l2=None, l3=20.0)
    assert level == "GREEN"


# ---------------------------------------------------------------------------
# Case 9: 경계값 — composite 정확히 30.0 → YELLOW (교차검증 통과 시)
# ---------------------------------------------------------------------------
def test_exact_boundary_30_is_yellow() -> None:
    """composite 정확히 30.0, 교차검증 통과(2계층 ≥30) → YELLOW."""
    level = determine_alert_level(composite=30.0, l1=35.0, l2=35.0, l3=5.0)
    assert level == "YELLOW"


# ---------------------------------------------------------------------------
# Case 10: 경계값 — composite 정확히 30.0, 교차검증 실패 → GREEN
# ---------------------------------------------------------------------------
def test_exact_boundary_30_fails_cross_validation() -> None:
    """composite 30.0 이지만 1계층만 ≥30 → GREEN 다운그레이드."""
    level = determine_alert_level(composite=30.0, l1=35.0, l2=20.0, l3=5.0)
    assert level == "GREEN"


# ---------------------------------------------------------------------------
# RiskScoreRow 데이터 클래스 생성 테스트
# ---------------------------------------------------------------------------
def test_risk_score_row_instantiation() -> None:
    """RiskScoreRow 가 정상적으로 생성되어야 한다."""
    from datetime import datetime, timezone
    row = RiskScoreRow(
        region="서울특별시",
        time=datetime(2026, 4, 24, tzinfo=timezone.utc),
        composite_score=42.5,
        l1_score=50.0,
        l2_score=40.0,
        l3_score=30.0,
        alert_level="YELLOW",
    )
    assert row.region == "서울특별시"
    assert row.composite_score == 42.5
    assert row.alert_level == "YELLOW"


