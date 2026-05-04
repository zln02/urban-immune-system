"""FastAPI 부하 테스트 시나리오 — 조달청 공공SW 기준 p95 < 500ms 검증.

대상 엔드포인트 (가중치):
  - GET /api/v1/alerts/regions           (weight=5) — 메인 페이지 최빈 호출
  - GET /api/v1/alerts/current           (weight=3) — 특정 지역 경보 조회
  - GET /api/v1/predictions/explain      (weight=1) — TFT XAI 설명
  - GET /api/v1/signals/timeseries       (weight=2) — 시계열 신호 90일

부하 프로파일:
  --users 50 --spawn-rate 2 --run-time 6m
  (실행 예시 → tests/load/README.md 참조)
"""
from __future__ import annotations

from locust import HttpUser, between, task


class UISApiUser(HttpUser):
    """도시면역시스템 FastAPI 동시 사용자 시뮬레이터."""

    # 각 task 사이 0.5 ~ 2.0초 대기 — 실제 브라우저 클릭 패턴 반영
    wait_time = between(0.5, 2.0)

    # ------------------------------------------------------------------ #
    # 가중치 5: GET /api/v1/alerts/regions — 대시보드 메인 카드(전국 17개 시도)
    # ------------------------------------------------------------------ #
    @task(5)
    def get_alert_regions(self) -> None:
        """전국 경보 현황 목록 조회."""
        with self.client.get(
            "/api/v1/alerts/regions",
            name="/api/v1/alerts/regions",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"status={resp.status_code}")

    # ------------------------------------------------------------------ #
    # 가중치 3: GET /api/v1/alerts/current?region=서울특별시
    # ------------------------------------------------------------------ #
    @task(3)
    def get_current_alert(self) -> None:
        """서울특별시 현재 경보 레벨 조회."""
        with self.client.get(
            "/api/v1/alerts/current",
            params={"region": "서울특별시"},
            name="/api/v1/alerts/current",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                # 404 = DB에 해당 region 데이터 없음 — 서버 오류 아님
                resp.success()
            else:
                resp.failure(f"status={resp.status_code}")

    # ------------------------------------------------------------------ #
    # 가중치 1: GET /api/v1/predictions/explain
    # ------------------------------------------------------------------ #
    @task(1)
    def get_predictions_explain(self) -> None:
        """TFT attention 기반 XAI 예측 설명 조회."""
        with self.client.get(
            "/api/v1/predictions/explain",
            params={"region": "서울특별시"},
            name="/api/v1/predictions/explain",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"status={resp.status_code}")

    # ------------------------------------------------------------------ #
    # 가중치 2: GET /api/v1/signals/timeseries?layer=otc&region=서울특별시&days=90
    # ------------------------------------------------------------------ #
    @task(2)
    def get_timeseries(self) -> None:
        """OTC 계층 서울 90일 시계열 신호 조회."""
        with self.client.get(
            "/api/v1/signals/timeseries",
            params={"layer": "otc", "region": "서울특별시", "days": 90},
            name="/api/v1/signals/timeseries",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"status={resp.status_code}")
