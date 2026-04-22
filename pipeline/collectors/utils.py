"""공용 유틸리티 — collectors 공유.

3개 수집기(otc/search/wastewater) 에 중복 정의되어 있던 `_normalize` 를
단일 모듈로 통합. 신규 수집기도 여기서 import 해서 쓸 것.
"""

from __future__ import annotations


def normalize_minmax(values: list[float]) -> list[float]:
    """Min-Max 정규화 (0~100).

    - 빈 리스트: 그대로 반환
    - hi == lo (모든 값 동일): 50.0 으로 flat (나눗셈 0 방지 + 중립 마커)
    - 그 외: (v - lo) / (hi - lo) * 100, 소수 둘째자리 반올림
    """
    if not values:
        return values
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    return [round((v - lo) / (hi - lo) * 100, 2) for v in values]
