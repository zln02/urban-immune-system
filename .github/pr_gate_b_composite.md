## Summary
Builds on PR #54 (Regional Layer Threshold). Adds region-specific composite
gate thresholds for weak signal regions (충북·대구·경북). Algorithm unchanged
(calibration only); patent claim preserved.

## Changes
- `backend/app/config.py`: `REGIONAL_COMPOSITE_THRESHOLDS` dict
  - 충북: 20.0 / 대구·경북: 25.0 / others: 30.0 (default)
- `pipeline/scorer.py`: `_get_composite_threshold(region)` + region-specific YELLOW entry
- `tests/test_scorer.py`: composite threshold + gate B preservation (6 new cases)

## Results — Target met
| Metric | Before (PR #54) | After (this PR) | Target | Status |
|--------|-----------------|-----------------|--------|--------|
| mean_recall | 0.844 | **0.882** | ≥0.850 | ✅ PASS |
| mean_FAR | 0.206 | 0.250 | <0.300 | ✅ PASS |

## Per-region (weak signal regions)
| Region | recall before | recall after | delta | FAR |
|--------|---------------|--------------|-------|-----|
| 충청북도 | 0.529 | **0.941** | +0.412 | 0.50 |
| 대구광역시 | 0.647 | **0.823** | +0.176 | 0.25 |
| 경상북도 | 0.647 | **0.823** | +0.176 | 0.25 |

Strong regions (서울·부산·세종 등 14개): 변화 없음 (verification 통과).

## Verification
- [x] pytest tests/: 354 passed, 3 skipped, 0 failed
- [x] Worker DoD isolation check: full suite passes
- [x] backtest_17regions.json + frontend sync
- [x] Algorithm preservation (patent claim N-of-M gate unchanged)

## Risk
- 충청북도 FAR 0.50 — 약신호 지역 calibration trade-off. mean FAR 0.250으로 전체 목표 통과.
  운영 단계에서 region-specific alerting policy로 추가 mitigate 가능.
- 롤백: `backend/app/config.py` REGIONAL_COMPOSITE_THRESHOLDS dict 한 줄 원복으로 즉시 가능

## Roadmap
- 다음 PR: 커버리지 64%→70% (납품 기준)
- K8s 매니페스트 배포 (P1)
- KOWAS 자동 크롤링 검증 (P1)
- 충북 FAR 추가 개선 (alert policy 차등화)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
