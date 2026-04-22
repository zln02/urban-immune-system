"""공통 정규화 유틸리티."""

from __future__ import annotations


def min_max_normalize(values: list[float], *, fallback: float = 50.0) -> list[float]:
    """비어 있는 입력과 상수열을 안전하게 처리하는 Min-Max 정규화."""
    if not values:
        return []

    lo, hi = min(values), max(values)
    if hi == lo:
        return [fallback] * len(values)

    return [round((value - lo) / (hi - lo) * 100, 2) for value in values]
