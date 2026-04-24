"""3계층 신호 앙상블 점수 계산 및 risk_scores 테이블 배치 적재.

수집된 layer_signals (otc / wastewater / search) 를 읽어
composite_score 를 계산하고 risk_scores 에 upsert 한다.

경보 레벨 규칙:
  composite < 30            → GREEN
  30 ≤ composite < 55       → YELLOW
  55 ≤ composite < 75       → ORANGE
  composite ≥ 75            → RED
  단, YELLOW 이상은 2개 이상 계층이 30 이상이어야 한다.
  조건 미충족 시 GREEN 으로 강제 다운그레이드.
"""
from __future__ import annotations

import asyncio
import logging
import os
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# 프로젝트 루트 .env 로드 (python-dotenv)
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env", override=False)

logger = logging.getLogger(__name__)

_DEFAULT_DB_URL = "postgresql://uis_user:changeme_local@localhost:5432/urban_immune"

# DB 커넥션 풀 싱글톤
_pool: asyncpg.Pool | None = None


# ---------------------------------------------------------------------------
# 설정 로딩 — config.py 가중치 사용
# ---------------------------------------------------------------------------

def _load_weights() -> tuple[float, float, float]:
    """backend/app/config.py 에서 앙상블 가중치를 로드한다.

    Returns:
        (w1_otc, w2_wastewater, w3_search) 튜플
    """
    try:
        from backend.app.config import settings
        return (
            settings.ensemble_weight_l1,
            settings.ensemble_weight_l2,
            settings.ensemble_weight_l3,
        )
    except Exception as exc:
        logger.warning("config.py 로드 실패, 기본값 사용 (w1=0.35 w2=0.40 w3=0.25): %s", exc)
        return (0.35, 0.40, 0.25)


# ---------------------------------------------------------------------------
# 결과 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class RiskScoreRow:
    """risk_scores 한 행을 표현하는 데이터 클래스."""

    region: str
    time: datetime
    composite_score: float
    l1_score: float | None
    l2_score: float | None
    l3_score: float | None
    alert_level: str


# ---------------------------------------------------------------------------
# 경보 레벨 계산
# ---------------------------------------------------------------------------

def determine_alert_level(
    composite: float,
    l1: float | None,
    l2: float | None,
    l3: float | None,
) -> str:
    """composite_score 와 계층별 값으로 경보 레벨을 결정한다.

    YELLOW 이상은 반드시 2개 이상 계층이 30 이상이어야 발령.
    L3 단독 고값이어도 교차검증 없으면 GREEN/YELLOW 이하로 제한.

    Args:
        composite: 가중합 점수 (0-100)
        l1: OTC 정규화 점수 (None = 데이터 없음)
        l2: 하수도 정규화 점수 (None = 데이터 없음)
        l3: 검색트렌드 정규화 점수 (None = 데이터 없음)

    Returns:
        'GREEN' | 'YELLOW' | 'ORANGE' | 'RED'
    """
    # 30 이상인 계층 수 카운트 (None 은 0으로 처리)
    above_threshold = sum(
        1 for v in (l1, l2, l3) if v is not None and v >= 30
    )

    # composite 기반 원래 레벨 결정
    if composite >= 75:
        raw_level = "RED"
    elif composite >= 55:
        raw_level = "ORANGE"
    elif composite >= 30:
        raw_level = "YELLOW"
    else:
        raw_level = "GREEN"

    # 2개 이상 계층 교차검증 없으면 GREEN 으로 강제 다운그레이드
    if raw_level in ("YELLOW", "ORANGE", "RED") and above_threshold < 2:
        logger.info(
            "교차검증 실패 (30 이상 계층 %d개) — %s → GREEN 다운그레이드 "
            "(l1=%.1f l2=%.1f l3=%.1f composite=%.1f)",
            above_threshold,
            raw_level,
            l1 or 0.0,
            l2 or 0.0,
            l3 or 0.0,
            composite,
        )
        return "GREEN"

    return raw_level


# ---------------------------------------------------------------------------
# DB 커넥션 풀
# ---------------------------------------------------------------------------

def _normalize_dsn(db_url: str) -> str:
    """asyncpg 가 이해하는 DSN 형태로 변환한다.

    SQLAlchemy 의 'postgresql+asyncpg://' 스킴을 asyncpg 표준 'postgresql://' 으로 치환.

    Args:
        db_url: DATABASE_URL 환경변수 값

    Returns:
        asyncpg 호환 DSN 문자열
    """
    return db_url.replace("postgresql+asyncpg://", "postgresql://")


async def _get_pool() -> asyncpg.Pool:
    """asyncpg 커넥션 풀 싱글톤을 반환한다."""
    global _pool
    if _pool is None:
        raw_url = os.getenv("DATABASE_URL", _DEFAULT_DB_URL)
        if "changeme" in raw_url:
            warnings.warn(
                "DATABASE_URL 에 플레이스홀더(changeme)가 포함되어 있습니다.",
                UserWarning,
                stacklevel=2,
            )
        db_url = _normalize_dsn(raw_url)
        _pool = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=5)
        logger.info("TimescaleDB 커넥션 풀 생성 완료")
    return _pool


async def _close_pool() -> None:
    """커넥션 풀을 닫는다."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ---------------------------------------------------------------------------
# 지역별 최신 계층 신호 조회
# ---------------------------------------------------------------------------

async def _fetch_latest_signals(
    pool: asyncpg.Pool,
    region: str,
) -> dict[str, float | None]:
    """해당 지역의 L1/L2/L3 최신 값을 각각 조회한다.

    layer_signals 에서 region 별로 각 계층(otc / wastewater / search) 의
    가장 최근 row 를 가져온다.

    Args:
        pool: asyncpg 커넥션 풀
        region: 지역명

    Returns:
        {'otc': float|None, 'wastewater': float|None, 'search': float|None,
         'latest_time': datetime|None}
    """
    rows = await pool.fetch(
        """
        SELECT DISTINCT ON (layer)
            layer,
            value,
            time
        FROM layer_signals
        WHERE region = $1
          AND layer IN ('otc', 'wastewater', 'search')
        ORDER BY layer, time DESC
        """,
        region,
    )

    result: dict[str, float | None] = {
        "otc": None,
        "wastewater": None,
        "search": None,
    }
    latest_time: datetime | None = None

    for row in rows:
        layer_name: str = row["layer"]
        result[layer_name] = float(row["value"])
        t: datetime = row["time"]
        if latest_time is None or t > latest_time:
            latest_time = t

    result["latest_time"] = latest_time  # type: ignore[assignment]
    return result


# ---------------------------------------------------------------------------
# 단일 지역 점수 계산
# ---------------------------------------------------------------------------

async def compute_risk_scores_for_region(
    region: str,
    target_date: date,
) -> RiskScoreRow | None:
    """단일 지역의 최신 신호로 composite_score 를 계산한다.

    Args:
        region: 지역명 (예: '서울특별시')
        target_date: 점수 기준 날짜 (time 컬럼에 UTC 00:00 으로 저장)

    Returns:
        RiskScoreRow — 데이터 없으면 None
    """
    w1, w2, w3 = _load_weights()
    pool = await _get_pool()
    signals = await _fetch_latest_signals(pool, region)

    l1 = signals["otc"]
    l2 = signals["wastewater"]
    l3 = signals["search"]

    # 데이터가 하나도 없으면 None 반환
    if l1 is None and l2 is None and l3 is None:
        logger.warning("지역 '%s' — 모든 계층 데이터 없음. 스킵.", region)
        return None

    # 없는 계층은 0 으로 대체 (NaN 전파 방지)
    safe_l1 = l1 if l1 is not None else 0.0
    safe_l2 = l2 if l2 is not None else 0.0
    safe_l3 = l3 if l3 is not None else 0.0

    composite = round(w1 * safe_l1 + w2 * safe_l2 + w3 * safe_l3, 4)
    alert_level = determine_alert_level(composite, l1, l2, l3)

    score_time = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        tzinfo=timezone.utc,
    )

    return RiskScoreRow(
        region=region,
        time=score_time,
        composite_score=composite,
        l1_score=l1,
        l2_score=l2,
        l3_score=l3,
        alert_level=alert_level,
    )


# ---------------------------------------------------------------------------
# risk_scores upsert
# ---------------------------------------------------------------------------

async def _upsert_risk_score(pool: asyncpg.Pool, row: RiskScoreRow) -> bool:
    """risk_scores 에 upsert 한다 (동일 region + time 중복 방지).

    TimescaleDB 하이퍼테이블은 ON CONFLICT 가 제한적이므로
    DELETE + INSERT 패턴을 사용한다.

    Args:
        pool: asyncpg 커넥션 풀
        row: 삽입할 RiskScoreRow

    Returns:
        True — 신규 INSERT, False — 기존 레코드 업데이트
    """
    async with pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM risk_scores WHERE region = $1 AND time = $2",
            row.region,
            row.time,
        )
        is_new = existing is None

        if not is_new:
            await conn.execute(
                "DELETE FROM risk_scores WHERE region = $1 AND time = $2",
                row.region,
                row.time,
            )

        await conn.execute(
            """
            INSERT INTO risk_scores
                (time, region, composite_score, l1_score, l2_score, l3_score, alert_level)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            row.time,
            row.region,
            row.composite_score,
            row.l1_score,
            row.l2_score,
            row.l3_score,
            row.alert_level,
        )

    action = "INSERT" if is_new else "UPDATE"
    logger.info(
        "[%s] region=%s composite=%.2f level=%s (l1=%.1f l2=%.1f l3=%.1f)",
        action,
        row.region,
        row.composite_score,
        row.alert_level,
        row.l1_score or 0.0,
        row.l2_score or 0.0,
        row.l3_score or 0.0,
    )
    return is_new


# ---------------------------------------------------------------------------
# 전체 지역 일괄 실행
# ---------------------------------------------------------------------------

async def run_weekly_scoring() -> int:
    """모든 지역의 최신 신호로 composite_score 를 계산하고 risk_scores 에 적재한다.

    layer_signals 에 존재하는 모든 region 을 자동 탐색하여 처리한다.

    Returns:
        INSERT(또는 UPDATE) 된 row 수
    """
    pool = await _get_pool()

    # 현재 DB 에 존재하는 모든 region 탐색
    regions: list[str] = [
        row["region"]
        for row in await pool.fetch(
            "SELECT DISTINCT region FROM layer_signals ORDER BY region"
        )
    ]

    if not regions:
        logger.warning("layer_signals 에 데이터가 없습니다.")
        return 0

    logger.info("대상 지역 %d개: %s", len(regions), regions)

    today = datetime.now(timezone.utc).date()
    inserted = 0

    for region in regions:
        try:
            score_row = await compute_risk_scores_for_region(region, today)
            if score_row is None:
                continue
            await _upsert_risk_score(pool, score_row)
            inserted += 1
        except Exception as exc:
            logger.error("지역 '%s' 처리 중 오류: %s", region, exc, exc_info=True)

    logger.info("run_weekly_scoring 완료 — 처리된 지역: %d/%d", inserted, len(regions))
    return inserted


# ---------------------------------------------------------------------------
# 직접 실행 엔트리포인트
# ---------------------------------------------------------------------------

async def _main() -> None:
    """python -m pipeline.scorer 실행 시 호출된다."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("=== 앙상블 scorer 수동 실행 시작 ===")
    try:
        count = await run_weekly_scoring()
        logger.info("완료 — risk_scores 적재 건수: %d", count)
    finally:
        await _close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
