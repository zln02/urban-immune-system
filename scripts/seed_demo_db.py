"""데모/로컬 가동용 시드 데이터 생성기.

TimescaleDB(docker) 없이 vanilla PostgreSQL 로 백엔드를 가동할 때
대시보드가 빈 화면(mock fallback)이 아닌 실제 DB 데이터를 보이도록
17개 시·도 × 40주 주간 시계열(layer_signals)과 융합 점수(risk_scores),
확진자(confirmed_cases), 경보 리포트(alert_reports) 1건을 적재한다.

- 신호 스케일: 0~100 (Min-Max 정규화 가정)
- 인플루엔자 계절 곡선: 가을 상승 → 2025-W50 부근 피크 → 봄 하강
- 앙상블 가중치/게이트: backend/app/config.py 와 동일 (0.35/0.40/0.25)

실행:
    python scripts/seed_demo_db.py
환경변수 DATABASE_URL(asyncpg) 또는 기본값(backend.app.config.settings) 사용.
"""

from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.config import settings

REGIONS: list[str] = [
    "서울특별시", "경기도", "인천광역시", "강원특별자치도", "충청북도",
    "충청남도", "대전광역시", "세종특별자치시", "전라북도", "전라남도",
    "광주광역시", "경상북도", "경상남도", "대구광역시", "울산광역시",
    "부산광역시", "제주특별자치도",
]

# 지역별 진폭 배수 (인구·신호 강도 차이 대용)
REGION_GAIN: dict[str, float] = {
    "서울특별시": 1.15, "경기도": 1.20, "인천광역시": 1.05, "부산광역시": 1.10,
    "대구광역시": 0.95, "대전광역시": 0.95, "광주광역시": 0.95, "울산광역시": 0.90,
    "세종특별자치시": 0.80, "제주특별자치도": 0.85,
}

WEEKS = 40
NOW = datetime(2026, 6, 22, 9, 0, tzinfo=timezone.utc)  # 최신 주(월요일 09:00 기준)
PEAK_WEEK_OFFSET = 1  # 최신 주를 피크 직후로 (대도시 RED + 나머지 YELLOW 혼합 데모)

W1, W2, W3 = 0.35, 0.40, 0.25


def seasonal(week_idx: int) -> float:
    """week_idx(0=가장 오래전 … WEEKS-1=최신)에 대한 0~1 계절 강도."""
    peak_idx = (WEEKS - 1) - PEAK_WEEK_OFFSET
    spread = 7.0
    return math.exp(-((week_idx - peak_idx) ** 2) / (2 * spread**2))


def jitter(seed: int) -> float:
    """결정론적 의사난수 0~1 (Math.random 회피)."""
    x = math.sin(seed * 12.9898) * 43758.5453
    return x - math.floor(x)


def compute(region: str, week_idx: int) -> dict[str, float]:
    base = seasonal(week_idx) * 100.0 * REGION_GAIN.get(region, 1.0)
    rk = sum(ord(c) for c in region)
    otc = max(0.0, min(100.0, base * 0.95 + (jitter(rk + week_idx) - 0.5) * 12))
    search = max(0.0, min(100.0, base * 1.05 + (jitter(rk * 2 + week_idx) - 0.5) * 14))
    waste = max(0.0, min(100.0, base * 0.85 + (jitter(rk * 3 + week_idx) - 0.5) * 10))
    weather = max(0.0, min(100.0, 60 - base * 0.4 + (jitter(rk + week_idx * 2) - 0.5) * 8))
    return {"otc": round(otc, 1), "search": round(search, 1),
            "wastewater": round(waste, 1), "weather": round(weather, 1)}


def alert_level(composite: float, l1: float, l2: float, l3: float, region: str) -> str:
    comp_thr = settings.regional_composite_thresholds.get(region, settings.default_composite_threshold)
    layer_thr = settings.regional_layer_thresholds.get(region, settings.default_layer_threshold)
    if composite >= 75:
        level = "RED"
    elif composite >= comp_thr:
        level = "YELLOW"
    else:
        level = "GREEN"
    if level != "GREEN":
        layers_above = sum(1 for v in (l1, l2, l3) if v >= layer_thr)
        if layers_above < 2:
            level = "GREEN"
    return level


async def _real_data_guard(conn, force: bool) -> None:
    """[파괴 가드 — 2026-06-23] DELETE 전, DB에 실데이터가 있으면 --force 없이는 중단.

    이 스크립트는 4개 테이블을 통째로 DELETE 하므로, 실 네이버/KOWAS 수집분이 적재된
    운영 DB 에서 실수로 돌리면 전소된다(실제로 2회 발생). seed_demo 이외 source 신호가
    하나라도 있으면 실데이터로 간주하고 거부한다.
    """
    real = (await conn.execute(text(
        "SELECT count(*) FROM layer_signals WHERE source IS NOT NULL AND source NOT LIKE 'seed%'"
    ))).scalar() or 0
    if real and not force:
        srcs = (await conn.execute(text(
            "SELECT DISTINCT source FROM layer_signals WHERE source NOT LIKE 'seed%' LIMIT 10"
        ))).scalars().all()
        raise SystemExit(
            f"\n[중단] layer_signals 에 실데이터 {real}행(비-seed source)이 있습니다: {srcs}\n"
            f"  이 스크립트는 4개 테이블을 전부 DELETE 합니다 — 실 네이버/KOWAS 수집분이 날아갑니다.\n"
            f"  정말 덮어쓰려면 명시적으로 실행하세요:  python scripts/seed_demo_db.py --force\n"
        )


async def main() -> None:
    import sys
    force = "--force" in sys.argv
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await _real_data_guard(conn, force)
        for tbl in ("layer_signals", "risk_scores", "confirmed_cases", "alert_reports"):
            await conn.execute(text(f"DELETE FROM {tbl}"))

        ls_rows, rs_rows, cc_rows = [], [], []
        for region in REGIONS:
            for wi in range(WEEKS):
                t = NOW - timedelta(weeks=(WEEKS - 1 - wi))
                sig = compute(region, wi)
                for layer, val in sig.items():
                    ls_rows.append({"time": t, "layer": layer, "region": region,
                                    "value": val, "raw_value": val, "source": "seed_demo",
                                    "pathogen": "influenza"})
                l1, l2, l3 = sig["otc"], sig["wastewater"], sig["search"]
                composite = round(W1 * l1 + W2 * l2 + W3 * l3, 2)
                level = alert_level(composite, l1, l2, l3, region)
                rs_rows.append({"time": t, "region": region, "composite_score": composite,
                                "l1_score": l1, "l2_score": l2, "l3_score": l3,
                                "alert_level": level})
                cases = int(seasonal(wi) * 800 * REGION_GAIN.get(region, 1.0))
                cc_rows.append({"time": t, "region": region, "disease": "influenza",
                                "case_count": cases, "per_100k": round(cases / 50.0, 2)})

        await conn.execute(text("""
            INSERT INTO layer_signals (time, layer, region, value, raw_value, source, pathogen)
            VALUES (:time, :layer, :region, :value, :raw_value, :source, :pathogen)
        """), ls_rows)
        await conn.execute(text("""
            INSERT INTO risk_scores (time, region, composite_score, l1_score, l2_score, l3_score, alert_level)
            VALUES (:time, :region, :composite_score, :l1_score, :l2_score, :l3_score, :alert_level)
        """), rs_rows)
        await conn.execute(text("""
            INSERT INTO confirmed_cases (time, region, disease, case_count, per_100k)
            VALUES (:time, :region, :disease, :case_count, :per_100k)
        """), cc_rows)

        top = max(REGIONS, key=lambda r: compute(r, WEEKS - 1)["wastewater"])
        sig = compute(top, WEEKS - 1)
        comp = round(W1 * sig["otc"] + W2 * sig["wastewater"] + W3 * sig["search"], 2)
        lvl = alert_level(comp, sig["otc"], sig["wastewater"], sig["search"], top)
        await conn.execute(text("""
            INSERT INTO alert_reports (time, region, alert_level, summary, recommendations,
                model_used, triggered_by, trigger_source, feature_values, rag_sources, model_metadata)
            VALUES (:time, :region, :alert_level, :summary, :recommendations,
                :model_used, :triggered_by, :trigger_source,
                CAST(:feature_values AS JSONB), CAST(:rag_sources AS JSONB), CAST(:model_metadata AS JSONB))
        """), {
            "time": NOW, "region": top, "alert_level": lvl,
            "summary": f"{top} 3계층 융합 결과 composite={comp} ({lvl}). OTC·검색 신호 동반 상승으로 교차검증 충족.",
            "recommendations": "지자체 역학조사과 모니터링 강화 권고. 약국 OTC 및 검색 트렌드 주간 추적.",
            "model_used": "seed-demo", "triggered_by": "manual_cli", "trigger_source": "seed_demo_db.py",
            "feature_values": json.dumps({"l1": sig["otc"], "l2": sig["wastewater"], "l3": sig["search"], "composite": comp}, ensure_ascii=False),
            "rag_sources": json.dumps([{"topic": "influenza_surveillance", "score": 0.91, "source": "KDCA guideline"}], ensure_ascii=False),
            "model_metadata": json.dumps({"model": "seed-demo", "prompt_version": "v1"}, ensure_ascii=False),
        })

        cnt = (await conn.execute(text("SELECT count(*) FROM layer_signals"))).scalar()
        rcnt = (await conn.execute(text("SELECT count(*) FROM risk_scores"))).scalar()
        levels = (await conn.execute(text(
            "SELECT alert_level, count(*) FROM risk_scores WHERE time = :t GROUP BY alert_level"
        ), {"t": NOW})).all()
    await engine.dispose()
    print(f"seeded layer_signals={cnt} risk_scores={rcnt}")
    print("latest-week levels:", dict(levels))


if __name__ == "__main__":
    asyncio.run(main())
