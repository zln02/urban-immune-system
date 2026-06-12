"""공통 입력 검증 헬퍼 (ISMS-P 2.10.2 — 입력 데이터 검증).

FastAPI Depends() 로 주입하거나 직접 호출해 사용한다.
"""

from __future__ import annotations

from fastapi import HTTPException, Query

# 전국 17개 시·도 정규 명칭 — 이 목록 외 입력은 422 반환
# korea-regions.ts 와 동일 순서 유지
VALID_REGIONS: frozenset[str] = frozenset(
    [
        "서울특별시",
        "경기도",
        "인천광역시",
        "강원특별자치도",
        "충청북도",
        "충청남도",
        "대전광역시",
        "세종특별자치시",
        "전라북도",
        "전라남도",
        "광주광역시",
        "경상북도",
        "경상남도",
        "대구광역시",
        "울산광역시",
        "부산광역시",
        "제주특별자치도",
    ]
)


def validate_region(
    region: str = Query("서울특별시", min_length=2, max_length=20),
) -> str:
    """region 쿼리 파라미터를 17개 시·도로 제한.

    유효하지 않은 지역명이 오면 422 Unprocessable Entity 를 반환한다.
    min_length=2 / max_length=20 은 쿼리 레벨 pre-check (SQL 도달 전 차단).
    """
    if region not in VALID_REGIONS:
        raise HTTPException(
            status_code=422,
            detail=f"유효하지 않은 지역: '{region}'. 17개 시·도 중 하나를 입력하세요.",
        )
    return region
