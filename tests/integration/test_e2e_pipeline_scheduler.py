"""통합 테스트: APScheduler 인스턴스에 jobs >= 3, cron trigger 검증.

scheduler 모듈을 import해서 실제 실행 없이 job 등록 상태만 확인.
"""
from __future__ import annotations

import pytest
from apscheduler.triggers.cron import CronTrigger


def test_scheduler_has_enough_jobs():
    """scheduler 모듈 상단에 add_job으로 등록된 job이 3개 이상인지 확인."""
    # scheduler.py의 BlockingScheduler 인스턴스를 직접 참조
    from pipeline.collectors import scheduler as sched_mod

    jobs = sched_mod.scheduler.get_jobs()
    assert len(jobs) >= 3, (
        f"APScheduler에 등록된 job이 {len(jobs)}개 — 최소 3개 필요"
    )


def test_scheduler_jobs_have_cron_triggers():
    """등록된 모든 job이 CronTrigger를 사용하는지 확인."""
    from pipeline.collectors import scheduler as sched_mod

    jobs = sched_mod.scheduler.get_jobs()
    non_cron = [j.id for j in jobs if not isinstance(j.trigger, CronTrigger)]
    assert not non_cron, f"CronTrigger 아닌 job 발견: {non_cron}"


def test_scheduler_known_job_ids_present():
    """핵심 job ID (otc, wastewater, weather) 가 등록되어 있는지 확인."""
    from pipeline.collectors import scheduler as sched_mod

    job_ids = {j.id for j in sched_mod.scheduler.get_jobs()}
    required = {"otc", "wastewater", "weather"}
    missing = required - job_ids
    assert not missing, f"누락된 job ID: {missing} (등록된 IDs: {job_ids})"


def test_otc_job_cron_day_of_week():
    """OTC job이 월요일(mon) cron으로 설정되어 있는지 확인."""
    from pipeline.collectors import scheduler as sched_mod

    job = sched_mod.scheduler.get_job("otc")
    assert job is not None, "otc job이 등록되어 있지 않음"
    trigger = job.trigger
    assert isinstance(trigger, CronTrigger)
    # CronTrigger 필드에서 day_of_week 확인
    fields = {f.name: str(f) for f in trigger.fields}
    assert "mon" in fields.get("day_of_week", ""), (
        f"otc job day_of_week 이 'mon' 아님: {fields.get('day_of_week')}"
    )
