"""backend/app/tasks.py 단위 테스트."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_generate_report_task_success() -> None:
    """generate_report_task 정상 경로: save_alert_report 호출 확인."""
    mock_report = {
        "region": "서울특별시",
        "alert_level": "YELLOW",
        "summary": "테스트 요약",
    }
    mock_session = AsyncMock()
    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx_mgr.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "backend.app.services.prediction_service.generate_alert_report_http",
        new_callable=AsyncMock,
        return_value=mock_report,
    ) as mock_gen, patch(
        "backend.app.database.async_session",
        return_value=mock_ctx_mgr,
    ), patch(
        "backend.app.services.alert_service.save_alert_report",
        new_callable=AsyncMock,
    ) as mock_save:
        from backend.app.tasks import generate_report_task

        # taskiq 브로커 kicker wrapper를 우회하여 내부 함수 직접 호출
        inner_fn = generate_report_task.original_func
        await inner_fn("서울특별시", {"l1": 50, "l2": 60, "l3": 40})

        mock_gen.assert_called_once_with("서울특별시", {"l1": 50, "l2": 60, "l3": 40})
        mock_save.assert_called_once_with(mock_report, mock_session)


@pytest.mark.asyncio
async def test_generate_report_task_exception_logged() -> None:
    """generate_report_task 예외 발생 시 로그만 남기고 전파 안함."""
    with patch(
        "backend.app.services.prediction_service.generate_alert_report_http",
        new_callable=AsyncMock,
        side_effect=RuntimeError("ML 서비스 다운"),
    ), patch("backend.app.tasks.logger") as mock_logger:
        from backend.app.tasks import generate_report_task

        inner_fn = generate_report_task.original_func
        # 예외가 전파되지 않아야 함
        await inner_fn("부산광역시", {})

        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args[0]
        assert "부산광역시" in str(call_args)
