## Summary
약한 신호 지역(충북·대구·경북)에 차등 임계값 적용. 알고리즘 자체 변경 없음,
calibration parameter only. 특허 청구범위 (N개 동시 임계 초과) 유지.

## Changes
- `backend/app/config.py`: `REGIONAL_LAYER_THRESHOLDS` dict 신설 (default 30, weak regions 12)
- `pipeline/scorer.py`: `_get_layer_threshold(region)` 추가, Gate B에서 지역별 threshold 적용
- `tests/test_scorer.py`: regional threshold + algorithm preservation 검증 (7개 케이스)

## Results (실측)
| 지표 | Before (uniform 30) | After (regional 12) | Delta |
|---|---|---|---|
| mean_recall | 0.837 | 0.844 | +0.007 |
| mean_FAR | 0.206 | 0.206 | 0 |
| 충북 recall | 0.529 | 0.588 | +0.059 |
| 대구 recall | 0.647 | 0.706 | +0.059 |
| 경북 recall | 0.647 | 0.647 | ≈0 |
| 강한 지역 14개 | (변화 없음 — 의도된 결과) | | |

## Limitation (정직)
- **목표 recall ≥ 0.85 미달** (실측 0.844)
- threshold sweep 15→12→10 동일 결과 확인
- 진단: 충북 FN이 composite < 30 구간에 집중 → gate B 도달 전 GREEN 차단
- threshold 차등의 본질적 한계 확인

## Roadmap (이번 PR 후속)
- 다음 PR: composite-level 차등화 (충북·경북 composite 임계값 자체 차등)
- 또는: 지역 가중치 재보정 (충북 L1·L2·L3 가중치 조정)
- 두 옵션 백테스트로 비교 후 선택

## Verification
- [x] pytest tests/ → 348 passed, 0 failed
- [x] 격리 검증 (Worker DoD 의무): 전체 통합 통과
- [x] backtest_17regions.json: 업데이트됨
- [x] frontend/public/data/backtest_17regions.json: 동기화

## Risk
- 알고리즘 청구범위 영향 X (parameter calibration only)
- 강한 지역 14개 변화 0 (verification 통과)
- 롤백: `backend/app/config.py` 한 dict만 원복하면 즉시 가능

🤖 Generated with [Claude Code](https://claude.com/claude-code)
