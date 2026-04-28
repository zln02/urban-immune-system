"""[DEPRECATED] L3 검색 트렌드 단일 지역 수집기.

이 모듈은 더 이상 scheduler에서 호출하지 않는다.

이유:
  - 네이버 DataLab 검색 API가 region 파라미터를 미지원해 단일 지역(서울)만 적재 가능
  - 12주 슬라이딩 min-max 정규화가 비수기에 마지막 주 = 0 으로 박힘
  - 결과적으로 scorer.py 게이트 B(2계층 이상 30+) 통과 불가

대체:
  - pipeline.collectors.naver_backfill.run_backfill(layers="search", regions="all")
  - 전국 56주 시계열을 17지역에 복제, backfill_layer 내부 멱등성 DELETE 적용
  - scheduler.py 의 weekly job 으로 통합됨 (매주 월 09:05)
"""
from __future__ import annotations

# 후방 호환을 위한 export 보존 — 외부에서 import하면 즉시 안내 예외 발생
def collect_search_weekly(*args, **kwargs):  # noqa: D401, ANN001, ANN002, ANN003
    raise RuntimeError(
        "collect_search_weekly 는 deprecated. "
        "pipeline.collectors.naver_backfill.run_backfill(layers='search') 를 사용하세요.",
    )
