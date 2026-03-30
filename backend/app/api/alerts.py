"""경보 리포트 API."""
from fastapi import APIRouter, BackgroundTasks, Query

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("/current")
async def get_current_alert(
    region: str = Query("서울특별시", min_length=2, max_length=100),
) -> dict:
    """현재 경보 레벨 및 최신 LLM 리포트 반환."""
    # TODO: alert_reports 테이블 최신 조회
    return {
        "region": region,
        "alert_level": "GREEN",
        "composite_score": None,
        "summary": None,
        "recommendations": None,
        "generated_at": None,
    }


@router.post("/generate")
async def generate_alert_report(
    background_tasks: BackgroundTasks,
    region: str = Query("서울특별시", min_length=2, max_length=100),
) -> dict:
    """RAG-LLM 경보 리포트 비동기 생성 요청."""
    # TODO: background_tasks.add_task(report_generator.generate, region)
    return {"status": "queued", "region": region}
