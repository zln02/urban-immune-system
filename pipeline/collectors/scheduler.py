"""APScheduler 기반 수집 스케줄러.

주간 수집 주기:
- Layer 1 (OTC)   : 매주 월요일 09:00
- Layer 2 (하수)  : 매주 화요일 10:00 (KOWAS 주간 보고서 발행 후)
- Layer 3 (검색)  : 매주 월요일 09:05
- 보조 (기상)     : 매시간
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from collectors.otc_collector import collect_otc_weekly
from collectors.search_collector import collect_search_weekly
from collectors.wastewater import collect_wastewater_from_pdfs
from collectors.weather_collector import collect_weather

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler(timezone="Asia/Seoul")

scheduler.add_job(collect_otc_weekly, CronTrigger(day_of_week="mon", hour=9, minute=0), id="otc")
scheduler.add_job(collect_search_weekly, CronTrigger(day_of_week="mon", hour=9, minute=5), id="search")
scheduler.add_job(collect_wastewater_from_pdfs, CronTrigger(day_of_week="tue", hour=10, minute=0), id="wastewater")
scheduler.add_job(collect_weather, CronTrigger(minute=0), id="weather")


if __name__ == "__main__":
    logger.info("Urban Immune System 데이터 수집 스케줄러 시작")
    scheduler.start()
