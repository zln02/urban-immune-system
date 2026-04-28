"""APScheduler 기반 수집 스케줄러.

주간 수집 주기:
- Layer 1 (OTC)   : 매주 월요일 09:00
- Layer 2 (하수)  : 매주 화요일 10:00 (KOWAS 주간 보고서 발행 후)
- Layer 3 (검색)  : 매주 월요일 09:05
- 보조 (기상)     : 매시간

각 수집기는 Kafka 대신 db_writer.insert_signal_sync()로
TimescaleDB layer_signals 테이블에 직접 INSERT한다.
(발표 데모 단순화 옵션: cron + DB INSERT, Kafka Consumer 불필요)
"""
import logging

from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import asyncio

from pipeline.collectors.otc_collector import collect_otc_weekly
from pipeline.collectors.naver_backfill import run_backfill
from pipeline.collectors.wastewater import collect_wastewater_from_pdfs
from pipeline.collectors.weather_collector import collect_weather
from pipeline.collectors.kcdc_collector import collect_and_insert_weekly
from pipeline.collectors.kowas_downloader import download_latest
from pipeline.report_trigger import run_nightly_reports
from pipeline.scorer import run_weekly_scoring

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler(timezone="Asia/Seoul")

scheduler.add_job(collect_otc_weekly, CronTrigger(day_of_week="mon", hour=9, minute=0), id="otc")


# L3 검색은 DataLab API가 지역 분리를 미지원하므로 backfill 패턴(전국 56주 → 17지역 복제)으로
# weekly 호출. backfill_layer 내부 멱등성 DELETE로 중복 누적 방지.
def _run_search_backfill_sync() -> None:
    asyncio.run(run_backfill(weeks=56, layers="search", regions="all"))


scheduler.add_job(
    _run_search_backfill_sync,
    CronTrigger(day_of_week="mon", hour=9, minute=5),
    id="search",
    name="L3 검색 트렌드 56주 백필 (17지역 복제)",
)
scheduler.add_job(collect_wastewater_from_pdfs, CronTrigger(day_of_week="tue", hour=10, minute=0), id="wastewater")

# 매주 화요일 09:30 — KOWAS 주간 PDF 자동 다운로드 (파싱 10:00 이전에 선행 실행)
scheduler.add_job(
    download_latest,
    CronTrigger(day_of_week="tue", hour=9, minute=30),
    id="weekly_kowas_download",
    name="KOWAS 주간보고 PDF 자동 다운로드",
    kwargs={"weeks": 4},
)
scheduler.add_job(collect_weather, CronTrigger(minute=0), id="weather")

# 매주 수요일 11:00 — L1(월09:00)·L2(화10:00)·L3(월09:05) 수집 완료 이후
# 3계층 앙상블 점수 계산 → risk_scores INSERT
def _run_weekly_scoring_sync() -> None:
    """BlockingScheduler에서 asyncio 코루틴을 실행하는 동기 래퍼."""
    asyncio.run(run_weekly_scoring())

scheduler.add_job(
    _run_weekly_scoring_sync,
    CronTrigger(day_of_week="wed", hour=11, minute=0),
    id="weekly_scoring",
    name="3계층 앙상블 점수 계산",
)

# 매일 12:00 — risk_scores 기반 Claude 경보 리포트 배치 생성
# YELLOW/ORANGE/RED 경보 지역만 처리 (GREEN 스킵, 비용 절감)
def _run_nightly_reports_sync() -> None:
    """BlockingScheduler에서 asyncio 코루틴을 실행하는 동기 래퍼."""
    asyncio.run(run_nightly_reports())

scheduler.add_job(
    _run_nightly_reports_sync,
    CronTrigger(hour=12, minute=0),
    id="nightly_reports",
    name="Claude 경보 리포트 배치 생성",
)


# 매주 금요일 09:30 — KCDC 주간 감염병 통계 적재
# (KCDC 주간 발표 통상 목요일 → 익일 금요일 수집)
scheduler.add_job(
    collect_and_insert_weekly,
    CronTrigger(day_of_week="fri", hour=9, minute=30),
    id="kcdc_confirmed",
    name="KCDC 감염병 주간 확진자 통계 적재",
    kwargs={"disease": "influenza"},
)


if __name__ == "__main__":
    logger.info("Urban Immune System 데이터 수집 스케줄러 시작")
    scheduler.start()
