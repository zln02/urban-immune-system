# V11 Presentation — Metric Notes (2026-05-14)

## KPI Update — Round 5 (composite-level Regional threshold)

| Metric | V10 | V11 | Delta |
|--------|-----|-----|-------|
| Recall (Gate ON) | 0.837 | **0.882** | +0.045 |
| FAR (Gate ON) | 0.206 | **0.250** | +0.044 |
| F1 | 0.882 | **0.907** | +0.025 |
| Precision | 0.949 | **0.940** | −0.009 |
| MCC | 0.595 | **0.610** | +0.015 |
| AUPRC | 0.973 | **0.973** | 0 |
| Coverage | 64% | **76%** | +12pp |
| Tests | 354 | **544** | +190 |

## Honesty Notes

- L1/L3 신선도: T-2 lag (Naver API 공개 정책)
- L2 신선도: T-7~10 lag (KOWAS 주간 PDF, 화요일 발행)
- 실시간 데모 시 lag 안내 필요

## Canonical Source

- `analysis/outputs/backtest_17regions.json` (frozen, 2026-05 보전)
- 모든 발표 수치는 이 파일 기준. 추후 검증·갱신은 별도 PR.

## Gate B 정책 (Region-tiered)

- 충청북도: composite ≥ 20 (was 30)
- 대구·경북: composite ≥ 25 (was 30)
- 그 외 14지역: composite ≥ 30 (unchanged)
- Layer threshold: 약신호 3지역 12, 그 외 30
- 알고리즘 보존, calibration parameter only (특허 청구범위 유지)

## Recall Distribution (17개 지역)

- 충청북도: 0.941 (was 0.529, +0.412)
- 대구광역시: 0.823 (was 0.647, +0.176)
- 경상북도: 0.823 (was 0.647, +0.176)
- 강한 지역 14개: 변화 없음 (verification 통과)
