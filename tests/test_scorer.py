"""앙상블 경보 로직 + scorer 유틸리티 단위 테스트.

검증 항목:
1. 경계값 — composite 정확한 레벨 경계
2. 2계층 교차검증 — YELLOW 이상 발령 조건
3. L3 단독 차단 — 검색 단독 고값으로 YELLOW 이상 발령 금지
4. 데이터 없음 처리 — None 계층 0으로 대체
5. GREEN 정상 경로 — 낮은 composite 는 교차검증 없이 GREEN
6. ORANGE 경계 — 55 ≤ composite < 75, 2계층 이상 30 이상
7. RED 경계 + 교차검증 실패 시 GREEN 다운그레이드
8. 단독 계층 차단 — 한 계층만 30+ 이면 GREEN 다운그레이드
9. asyncpg.Pool mock — _upsert_risk_score, run_weekly_scoring, backfill 경로
10. compute_risk_scores_for_region — 정상/데이터없음/에러 경로

NOTE: 게이트 A (L2 미달 시 GREEN 강제) 는 17지역 sweep 결과 임계값 어느 값도
sweet spot 못 찾아서 폐기 (analysis/outputs/l2_gate_sweep.json). 게이트 B
(2계층 교차검증) 만 유지.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pipeline.scorer as _scorer_module
from pipeline.scorer import (
    RiskScoreRow,
    _fetch_latest_signals,
    _get_composite_threshold,
    _get_layer_threshold,
    _load_weights,
    _normalize_dsn,
    _upsert_risk_score,
    backfill_risk_scores,
    compute_risk_scores_for_region,
    determine_alert_level,
    run_weekly_scoring,
)


def _make_mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """asyncpg Pool mock 헬퍼."""
    mock_pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool.acquire = _acquire
    return mock_pool


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
    # composite = 0.35*5 + 0.40*10 + 0.25*85 ≈ 27.0 → 원래 GREEN 이지만
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


# ---------------------------------------------------------------------------
# Case 12: _normalize_dsn — SQLAlchemy dialect 치환
# ---------------------------------------------------------------------------
def test_normalize_dsn_replaces_dialect() -> None:
    """'postgresql+asyncpg://' 스킴을 'postgresql://'로 치환해야 한다."""
    result = _normalize_dsn("postgresql+asyncpg://u:p@h/db")
    assert result == "postgresql://u:p@h/db"


# ---------------------------------------------------------------------------
# Case 13: _normalize_dsn — 일반 DSN은 변경 없이 통과
# ---------------------------------------------------------------------------
def test_normalize_dsn_plain_passthrough() -> None:
    """일반 'postgresql://' DSN은 변경 없이 그대로 반환해야 한다."""
    dsn = "postgresql://u:p@h/db"
    result = _normalize_dsn(dsn)
    assert result == dsn


# ---------------------------------------------------------------------------
# Case 14: _load_weights — 3개 float 튜플, 합계 ≈ 1.0
# ---------------------------------------------------------------------------
def test_load_weights_returns_tuple() -> None:
    """_load_weights()는 합계가 약 1.0인 3-tuple of floats를 반환해야 한다."""
    weights = _load_weights()
    assert isinstance(weights, tuple)
    assert len(weights) == 3
    assert all(isinstance(w, float) for w in weights)
    assert abs(sum(weights) - 1.0) < 1e-6, f"가중치 합={sum(weights):.6f}, 1.0이어야 함"


# ---------------------------------------------------------------------------
# Case 15: _fetch_latest_signals — 데이터 없음 → l1/l2/l3 모두 None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_latest_signals_no_data() -> None:
    """pool.fetch가 빈 리스트를 반환하면 l1/l2/l3가 모두 None이어야 한다."""
    mock_pool = MagicMock()
    mock_pool.fetch = AsyncMock(return_value=[])

    result = await _fetch_latest_signals(mock_pool, "서울특별시")

    assert result.get("otc") is None
    assert result.get("wastewater") is None
    assert result.get("search") is None


# ---------------------------------------------------------------------------
# 공통 픽스처 — asyncpg Pool mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_conn() -> AsyncMock:
    """asyncpg Connection AsyncMock."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=None)  # 기본: 신규 레코드
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    conn.fetch = AsyncMock(return_value=[])
    return conn


@pytest.fixture
def mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """asyncpg Pool mock — pool.acquire() async context manager 포함."""
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    pool.acquire = _acquire
    pool.fetch = AsyncMock(return_value=[])
    return pool


# ---------------------------------------------------------------------------
# Case 16: _upsert_risk_score — 신규 INSERT (fetchval=None → is_new=True)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_risk_score_new_insert(mock_pool: MagicMock, mock_conn: AsyncMock) -> None:
    """기존 레코드 없을 때 _upsert_risk_score 는 True(신규 INSERT) 반환."""
    mock_conn.fetchval = AsyncMock(return_value=None)  # 신규

    row = RiskScoreRow(
        region="서울특별시",
        time=datetime(2026, 5, 1, tzinfo=timezone.utc),
        composite_score=45.0,
        l1_score=50.0,
        l2_score=40.0,
        l3_score=30.0,
        alert_level="YELLOW",
    )
    is_new = await _upsert_risk_score(mock_pool, row)

    assert is_new is True
    # execute 는 INSERT 1번만 호출
    assert mock_conn.execute.call_count == 1
    # DELETE 는 호출되지 않아야 함
    for call in mock_conn.execute.call_args_list:
        assert "DELETE" not in call.args[0]


@pytest.mark.asyncio
async def test_upsert_risk_score_update_existing(mock_pool: MagicMock, mock_conn: AsyncMock) -> None:
    """기존 레코드 있을 때 _upsert_risk_score 는 False(UPDATE) 반환 + DELETE+INSERT."""
    mock_conn.fetchval = AsyncMock(return_value=42)  # 기존 id=42

    row = RiskScoreRow(
        region="부산광역시",
        time=datetime(2026, 5, 1, tzinfo=timezone.utc),
        composite_score=60.0,
        l1_score=70.0,
        l2_score=55.0,
        l3_score=35.0,
        alert_level="ORANGE",
    )
    is_new = await _upsert_risk_score(mock_pool, row)

    assert is_new is False
    # execute: DELETE + INSERT = 2번
    assert mock_conn.execute.call_count == 2
    calls_sql = [c.args[0] for c in mock_conn.execute.call_args_list]
    assert any("DELETE" in sql for sql in calls_sql)
    assert any("INSERT" in sql for sql in calls_sql)


# ---------------------------------------------------------------------------
# Case 17: _upsert_risk_score — None 점수 처리 (l1/l2/l3 가 None 인 경우)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_risk_score_none_scores(mock_pool: MagicMock, mock_conn: AsyncMock) -> None:
    """l1/l2/l3 가 None 이어도 _upsert_risk_score 가 정상 작동해야 한다."""
    mock_conn.fetchval = AsyncMock(return_value=None)

    row = RiskScoreRow(
        region="대구광역시",
        time=datetime(2026, 5, 1, tzinfo=timezone.utc),
        composite_score=0.0,
        l1_score=None,
        l2_score=None,
        l3_score=None,
        alert_level="GREEN",
    )
    is_new = await _upsert_risk_score(mock_pool, row)
    assert is_new is True


# ---------------------------------------------------------------------------
# Case 18: compute_risk_scores_for_region — 정상 경로
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_risk_scores_for_region_normal() -> None:
    """정상 신호 데이터가 있을 때 RiskScoreRow 를 반환해야 한다."""
    target = date(2026, 5, 1)

    mock_fetch_result = {
        "otc": 50.0,
        "wastewater": 40.0,
        "search": 30.0,
        "latest_time": datetime(2026, 4, 28, tzinfo=timezone.utc),
    }

    with (
        patch.object(_scorer_module, "_get_pool", new=AsyncMock()) as mock_get_pool,
        patch.object(_scorer_module, "_fetch_latest_signals", new=AsyncMock(return_value=mock_fetch_result)),
    ):
        mock_get_pool.return_value = MagicMock()
        result = await compute_risk_scores_for_region("서울특별시", target)

    assert result is not None
    assert result.region == "서울특별시"
    assert result.l1_score == 50.0
    assert result.l2_score == 40.0
    assert result.l3_score == 30.0
    assert result.time == datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert result.alert_level in ("GREEN", "YELLOW", "ORANGE", "RED")


@pytest.mark.asyncio
async def test_compute_risk_scores_for_region_all_none() -> None:
    """모든 계층이 None 이면 None 반환해야 한다."""
    mock_fetch_result = {
        "otc": None,
        "wastewater": None,
        "search": None,
        "latest_time": None,
    }

    with (
        patch.object(_scorer_module, "_get_pool", new=AsyncMock()) as mock_get_pool,
        patch.object(_scorer_module, "_fetch_latest_signals", new=AsyncMock(return_value=mock_fetch_result)),
    ):
        mock_get_pool.return_value = MagicMock()
        result = await compute_risk_scores_for_region("강원도", date(2026, 5, 1))

    assert result is None


@pytest.mark.asyncio
async def test_compute_risk_scores_gate_b_threshold() -> None:
    """게이트B: composite ≥ 30 이어도 계층 1개만 30+ 이면 GREEN 이어야 한다."""
    # l1=80(단독), l2=10, l3=10 → composite=0.35*80+0.40*10+0.25*10=32.5 YELLOW 범위
    # 게이트B: 30+ 계층 1개 → GREEN 다운그레이드
    mock_fetch_result = {
        "otc": 80.0,
        "wastewater": 10.0,
        "search": 10.0,
        "latest_time": datetime(2026, 4, 28, tzinfo=timezone.utc),
    }

    with (
        patch.object(_scorer_module, "_get_pool", new=AsyncMock()) as mock_get_pool,
        patch.object(_scorer_module, "_fetch_latest_signals", new=AsyncMock(return_value=mock_fetch_result)),
    ):
        mock_get_pool.return_value = MagicMock()
        result = await compute_risk_scores_for_region("경기도", date(2026, 5, 1))

    assert result is not None
    assert result.alert_level == "GREEN", f"게이트B 차단 기대 GREEN, 실제 {result.alert_level}"


# ---------------------------------------------------------------------------
# Case 19: run_weekly_scoring — 정상 처리 / 빈 regions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_weekly_scoring_no_regions() -> None:
    """layer_signals 에 데이터 없을 때 run_weekly_scoring 는 0 반환."""
    mock_p = MagicMock()
    mock_p.fetch = AsyncMock(return_value=[])  # 빈 regions

    with patch.object(_scorer_module, "_get_pool", new=AsyncMock(return_value=mock_p)):
        count = await run_weekly_scoring()

    assert count == 0


@pytest.mark.asyncio
async def test_run_weekly_scoring_normal() -> None:
    """정상 지역 2개가 있을 때 run_weekly_scoring 이 2를 반환해야 한다."""
    mock_p = MagicMock()
    mock_p.fetch = AsyncMock(
        return_value=[
            {"region": "서울특별시"},
            {"region": "부산광역시"},
        ]
    )

    dummy_row = RiskScoreRow(
        region="서울특별시",
        time=datetime(2026, 5, 1, tzinfo=timezone.utc),
        composite_score=42.0,
        l1_score=50.0,
        l2_score=40.0,
        l3_score=30.0,
        alert_level="YELLOW",
    )

    with (
        patch.object(_scorer_module, "_get_pool", new=AsyncMock(return_value=mock_p)),
        patch.object(_scorer_module, "compute_risk_scores_for_region", new=AsyncMock(return_value=dummy_row)),
        patch.object(_scorer_module, "_upsert_risk_score", new=AsyncMock(return_value=True)),
    ):
        count = await run_weekly_scoring()

    assert count == 2


@pytest.mark.asyncio
async def test_run_weekly_scoring_region_error_skipped() -> None:
    """한 지역 처리 중 예외 발생 시 나머지 지역은 계속 처리해야 한다."""
    mock_p = MagicMock()
    mock_p.fetch = AsyncMock(
        return_value=[
            {"region": "서울특별시"},
            {"region": "부산광역시"},
        ]
    )

    dummy_row = RiskScoreRow(
        region="부산광역시",
        time=datetime(2026, 5, 1, tzinfo=timezone.utc),
        composite_score=35.0,
        l1_score=40.0,
        l2_score=35.0,
        l3_score=20.0,
        alert_level="YELLOW",
    )

    call_count = 0

    async def _side_effect(region: str, target_date: date):
        nonlocal call_count
        call_count += 1
        if region == "서울특별시":
            raise RuntimeError("DB 연결 실패")
        return dummy_row

    with (
        patch.object(_scorer_module, "_get_pool", new=AsyncMock(return_value=mock_p)),
        patch.object(_scorer_module, "compute_risk_scores_for_region", side_effect=_side_effect),
        patch.object(_scorer_module, "_upsert_risk_score", new=AsyncMock(return_value=True)),
    ):
        count = await run_weekly_scoring()

    assert count == 1  # 서울 실패 → 부산만 성공
    assert call_count == 2


@pytest.mark.asyncio
async def test_run_weekly_scoring_score_row_none_skipped() -> None:
    """compute_risk_scores_for_region 이 None 반환 시 해당 지역 카운트 제외."""
    mock_p = MagicMock()
    mock_p.fetch = AsyncMock(return_value=[{"region": "제주특별자치도"}])

    with (
        patch.object(_scorer_module, "_get_pool", new=AsyncMock(return_value=mock_p)),
        patch.object(_scorer_module, "compute_risk_scores_for_region", new=AsyncMock(return_value=None)),
        patch.object(_scorer_module, "_upsert_risk_score", new=AsyncMock(return_value=True)),
    ):
        count = await run_weekly_scoring()

    assert count == 0


# ---------------------------------------------------------------------------
# Case 20: backfill_risk_scores — 날짜 범위 백필
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backfill_risk_scores_no_regions() -> None:
    """layer_signals 비어있으면 backfill 은 0 반환."""
    mock_p = MagicMock()
    mock_p.fetch = AsyncMock(return_value=[])

    with patch.object(_scorer_module, "_get_pool", new=AsyncMock(return_value=mock_p)):
        count = await backfill_risk_scores(date(2026, 1, 1), date(2026, 1, 7))

    assert count == 0


@pytest.mark.asyncio
async def test_backfill_risk_scores_two_weeks() -> None:
    """2주 범위 (step_days=7) + 지역 1개 → 처리 행 2개 기대."""
    mock_p = MagicMock()
    mock_p.fetch = AsyncMock(return_value=[{"region": "서울특별시"}])

    dummy_row = RiskScoreRow(
        region="서울특별시",
        time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        composite_score=40.0,
        l1_score=50.0,
        l2_score=35.0,
        l3_score=25.0,
        alert_level="YELLOW",
    )

    with (
        patch.object(_scorer_module, "_get_pool", new=AsyncMock(return_value=mock_p)),
        patch.object(_scorer_module, "compute_risk_scores_for_region", new=AsyncMock(return_value=dummy_row)),
        patch.object(_scorer_module, "_upsert_risk_score", new=AsyncMock(return_value=True)),
    ):
        count = await backfill_risk_scores(date(2026, 1, 1), date(2026, 1, 8), step_days=7)

    # 1/1 → 1/8 → loop: cur=1/1 (≤1/8), cur=1/8 (≤1/8), cur=1/15 (>1/8) → 2회 × 1 지역 = 2
    assert count == 2


@pytest.mark.asyncio
async def test_backfill_risk_scores_error_skipped() -> None:
    """backfill 중 특정 지역/날짜 오류는 로그 후 계속 진행해야 한다."""
    mock_p = MagicMock()
    mock_p.fetch = AsyncMock(
        return_value=[
            {"region": "서울특별시"},
            {"region": "부산광역시"},
        ]
    )

    dummy_row = RiskScoreRow(
        region="부산광역시",
        time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        composite_score=35.0,
        l1_score=40.0,
        l2_score=30.0,
        l3_score=20.0,
        alert_level="YELLOW",
    )

    async def _side_effect(region: str, cur_date: date):
        if region == "서울특별시":
            raise ValueError("테스트용 오류")
        return dummy_row

    with (
        patch.object(_scorer_module, "_get_pool", new=AsyncMock(return_value=mock_p)),
        patch.object(_scorer_module, "compute_risk_scores_for_region", side_effect=_side_effect),
        patch.object(_scorer_module, "_upsert_risk_score", new=AsyncMock(return_value=True)),
    ):
        count = await backfill_risk_scores(date(2026, 1, 1), date(2026, 1, 1), step_days=7)

    # 서울 실패, 부산 성공 → 1
    assert count == 1


# ---------------------------------------------------------------------------
# Case 21: _fetch_latest_signals — 데이터 있는 경우 값 파싱
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_latest_signals_with_data() -> None:
    """pool.fetch 가 3계층 데이터를 반환하면 otc/wastewater/search 값이 채워져야 한다."""
    from datetime import datetime, timezone

    t = datetime(2026, 4, 28, tzinfo=timezone.utc)

    rows = [
        {"layer": "otc", "value": 55.0, "time": t},
        {"layer": "wastewater", "value": 42.0, "time": t},
        {"layer": "search", "value": 30.0, "time": t},
    ]
    mock_pool = MagicMock()
    mock_pool.fetch = AsyncMock(return_value=rows)

    result = await _fetch_latest_signals(mock_pool, "서울특별시")

    assert result["otc"] == 55.0
    assert result["wastewater"] == 42.0
    assert result["search"] == 30.0
    assert result["latest_time"] == t


# ---------------------------------------------------------------------------
# Case 22: 지역별 Gate B threshold — Regional Tiered Threshold (feature/gate-b-regional-tuning)
# ---------------------------------------------------------------------------


def test_regional_threshold_chungbuk_pass() -> None:
    """충청북도 threshold=15: 점수 20인 계층 2개 → gate pass (YELLOW 발령)."""
    # l1=20, l2=20 → 둘 다 ≥15 → 2계층 통과
    # composite = 0.35*20 + 0.40*20 + 0.25*5 = 7+8+1.25 = 16.25 → GREEN 범위
    # YELLOW 범위가 되려면 composite≥30 필요 → l1=40, l2=40, l3=5
    # composite=0.35*40+0.40*40+0.25*5=14+16+1.25=31.25 → YELLOW 범위
    # threshold=15: l1=40≥15, l2=40≥15 → 2개 → YELLOW
    with patch("pipeline.scorer._get_layer_threshold", return_value=15.0):
        composite = 0.35 * 40.0 + 0.40 * 40.0 + 0.25 * 5.0
        level = determine_alert_level(composite=composite, l1=40.0, l2=40.0, l3=5.0, region="충청북도")
    assert level == "YELLOW", f"충북 threshold=15, l1=40 l2=40 → YELLOW 기대, 실제={level}"


def test_regional_threshold_seoul_fail() -> None:
    """서울 threshold=30: 점수 20인 계층 → gate fail (GREEN 강제)."""
    # l1=20, l2=20 → 둘 다 <30 → 0계층 통과 → GREEN 강제
    # composite=0.35*20+0.40*20+0.25*20=7+8+5=20 → GREEN 범위라서 이미 GREEN
    # composite≥30 이어야 gate 검사 진행. l1=20, l2=20, l3=60
    # composite=0.35*20+0.40*20+0.25*60=7+8+15=30 → YELLOW 범위
    # threshold=30: l1=20<30, l2=20<30, l3=60≥30 → 1개 → GREEN 강제
    with patch("pipeline.scorer._get_layer_threshold", return_value=30.0):
        composite = 0.35 * 20.0 + 0.40 * 20.0 + 0.25 * 60.0
        assert composite >= 30
        level = determine_alert_level(composite=composite, l1=20.0, l2=20.0, l3=60.0, region="서울특별시")
    assert level == "GREEN", f"서울 threshold=30, l1=20 l2=20 l3=60 → GREEN 기대, 실제={level}"


def test_regional_threshold_daegu_pass() -> None:
    """대구광역시 threshold=15: 점수 16인 계층 2개 → gate pass."""
    # l1=16, l2=16 → 둘 다 ≥15
    # composite=0.35*16+0.40*16+0.25*5=5.6+6.4+1.25=13.25 → GREEN 범위
    # composite≥30 필요: l1=50, l2=50, l3=5
    # composite=0.35*50+0.40*50+0.25*5=17.5+20+1.25=38.75 → YELLOW 범위
    # threshold=15: l1=50≥15, l2=50≥15 → 2개 → YELLOW
    with patch("pipeline.scorer._get_layer_threshold", return_value=15.0):
        composite = 0.35 * 50.0 + 0.40 * 50.0 + 0.25 * 5.0
        level = determine_alert_level(composite=composite, l1=50.0, l2=50.0, l3=5.0, region="대구광역시")
    assert level == "YELLOW", f"대구 threshold=15, l1=50 l2=50 → YELLOW 기대, 실제={level}"


def test_regional_threshold_gyeongbuk_fail_below_threshold() -> None:
    """경상북도 threshold=15: 점수 14인 계층 → gate fail (threshold 미만)."""
    # l1=14, l2=14 → 둘 다 <15 → 0계층
    # composite≥30: l1=14, l2=14, l3=80
    # composite=0.35*14+0.40*14+0.25*80=4.9+5.6+20=30.5 → YELLOW 범위
    # threshold=15: l1=14<15, l2=14<15, l3=80≥15 → 1개 → GREEN 강제
    with patch("pipeline.scorer._get_layer_threshold", return_value=15.0):
        composite = 0.35 * 14.0 + 0.40 * 14.0 + 0.25 * 80.0
        assert composite >= 30
        level = determine_alert_level(composite=composite, l1=14.0, l2=14.0, l3=80.0, region="경상북도")
    assert level == "GREEN", f"경북 threshold=15, l1=14 l2=14 <15 → GREEN 기대, 실제={level}"


def test_regional_threshold_seoul_boundary_30_pass() -> None:
    """서울 threshold=30: 점수 정확히 30인 계층 2개 → gate pass (경계값)."""
    # l1=30, l2=30 → 둘 다 ≥30(경계 포함)
    # composite=0.35*30+0.40*30+0.25*5=10.5+12+1.25=23.75 → GREEN
    # composite≥30: l1=30, l2=30, l3=30
    # composite=0.35*30+0.40*30+0.25*30=10.5+12+7.5=30 → YELLOW 범위
    with patch("pipeline.scorer._get_layer_threshold", return_value=30.0):
        composite = 0.35 * 30.0 + 0.40 * 30.0 + 0.25 * 30.0
        assert composite == 30.0
        level = determine_alert_level(composite=composite, l1=30.0, l2=30.0, l3=30.0, region="서울특별시")
    assert level == "YELLOW", f"서울 threshold=30 경계값: 3계층 모두 30 → YELLOW 기대, 실제={level}"


def test_regional_same_score_chungbuk_pass_seoul_fail() -> None:
    """동일 점수 20으로 충청북도(threshold=15) → YELLOW, 서울(threshold=30) → GREEN 비교."""
    # composite≥30 필요: l1=20, l2=20, l3=60
    # composite=0.35*20+0.40*20+0.25*60=7+8+15=30 → YELLOW 범위
    # 충북 threshold=15: l1=20≥15, l2=20≥15 → 2개 → YELLOW
    # 서울 threshold=30: l1=20<30, l2=20<30, l3=60≥30 → 1개 → GREEN
    composite = 0.35 * 20.0 + 0.40 * 20.0 + 0.25 * 60.0
    assert composite >= 30

    with patch("pipeline.scorer._get_layer_threshold", return_value=15.0):
        level_chungbuk = determine_alert_level(composite=composite, l1=20.0, l2=20.0, l3=60.0, region="충청북도")

    with patch("pipeline.scorer._get_layer_threshold", return_value=30.0):
        level_seoul = determine_alert_level(composite=composite, l1=20.0, l2=20.0, l3=60.0, region="서울특별시")

    assert level_chungbuk == "YELLOW", f"충북 threshold=15 → YELLOW 기대, 실제={level_chungbuk}"
    assert level_seoul == "GREEN", f"서울 threshold=30 → GREEN 기대, 실제={level_seoul}"


def test_get_layer_threshold_weak_regions() -> None:
    """_get_layer_threshold: 약신호 3지역은 낮은 threshold, 그 외는 30.0 반환."""
    from unittest.mock import MagicMock

    mock_settings = MagicMock()
    mock_settings.regional_layer_thresholds = {
        "충청북도": 12.0,
        "대구광역시": 12.0,
        "경상북도": 12.0,
    }
    mock_settings.default_layer_threshold = 30.0

    # settings는 _get_layer_threshold 내부에서 'from backend.app.config import settings'로 로드
    with patch("backend.app.config.settings", mock_settings):
        assert _get_layer_threshold("충청북도") == 12.0
        assert _get_layer_threshold("대구광역시") == 12.0
        assert _get_layer_threshold("경상북도") == 12.0
        assert _get_layer_threshold("서울특별시") == 30.0
        assert _get_layer_threshold("부산광역시") == 30.0


# ---------------------------------------------------------------------------
# Case 29~34: composite-level 차등화 — Regional Composite Threshold
# ---------------------------------------------------------------------------


def test_composite_threshold_chungbuk_yellow_at_20() -> None:
    """충청북도 composite=22: yellow_threshold=20 → YELLOW (gate B 통과)."""
    with (
        patch("pipeline.scorer._get_composite_threshold", return_value=20.0),
        patch("pipeline.scorer._get_layer_threshold", return_value=12.0),
    ):
        level = determine_alert_level(composite=22.0, l1=15.0, l2=15.0, l3=5.0, region="충청북도")
    assert level == "YELLOW", f"충북 composite=22, threshold=20 → YELLOW 기대, 실제={level}"


def test_composite_threshold_chungbuk_green_below_20() -> None:
    """충청북도 composite=19: yellow_threshold=20 → GREEN (임계값 미달)."""
    with (
        patch("pipeline.scorer._get_composite_threshold", return_value=20.0),
        patch("pipeline.scorer._get_layer_threshold", return_value=12.0),
    ):
        level = determine_alert_level(composite=19.0, l1=20.0, l2=20.0, l3=20.0, region="충청북도")
    assert level == "GREEN", f"충북 composite=19, threshold=20 → GREEN 기대, 실제={level}"


def test_composite_threshold_daegu_yellow_at_25() -> None:
    """대구광역시 composite=26: yellow_threshold=25 → YELLOW."""
    with (
        patch("pipeline.scorer._get_composite_threshold", return_value=25.0),
        patch("pipeline.scorer._get_layer_threshold", return_value=12.0),
    ):
        level = determine_alert_level(composite=26.0, l1=20.0, l2=20.0, l3=5.0, region="대구광역시")
    assert level == "YELLOW", f"대구 composite=26, threshold=25 → YELLOW 기대, 실제={level}"


def test_composite_threshold_seoul_unchanged_at_30() -> None:
    """서울특별시 composite=28: yellow_threshold=30 → GREEN (강한 지역 임계값 유지)."""
    with (
        patch("pipeline.scorer._get_composite_threshold", return_value=30.0),
        patch("pipeline.scorer._get_layer_threshold", return_value=30.0),
    ):
        level = determine_alert_level(composite=28.0, l1=35.0, l2=35.0, l3=5.0, region="서울특별시")
    assert level == "GREEN", f"서울 composite=28, threshold=30 → GREEN 기대, 실제={level}"


def test_composite_threshold_chungbuk_gate_b_still_enforced() -> None:
    """충청북도 composite=22 (≥20) 이어도 게이트 B 미달 시 GREEN 다운그레이드."""
    with (
        patch("pipeline.scorer._get_composite_threshold", return_value=20.0),
        patch("pipeline.scorer._get_layer_threshold", return_value=12.0),
    ):
        # l1=5, l2=5 둘 다 12 미만 → gate B 차단
        level = determine_alert_level(composite=22.0, l1=5.0, l2=5.0, l3=80.0, region="충청북도")
    assert level == "GREEN", f"충북 composite=22 but gate B 미달 → GREEN 기대, 실제={level}"


def test_get_composite_threshold_values() -> None:
    """_get_composite_threshold: 충북=20, 대구/경북=25, 그 외=30."""
    mock_settings = MagicMock()
    mock_settings.regional_composite_thresholds = {
        "충청북도": 20.0,
        "대구광역시": 25.0,
        "경상북도": 25.0,
    }
    mock_settings.default_composite_threshold = 30.0

    with patch("backend.app.config.settings", mock_settings):
        assert _get_composite_threshold("충청북도") == 20.0
        assert _get_composite_threshold("대구광역시") == 25.0
        assert _get_composite_threshold("경상북도") == 25.0
        assert _get_composite_threshold("서울특별시") == 30.0
        assert _get_composite_threshold(None) == 30.0
