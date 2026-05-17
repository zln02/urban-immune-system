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

## V11.1 Statistical Rigor Addendum (2026-05-17)

### Bootstrap 95% Confidence Intervals

Non-parametric percentile bootstrap, n=1000 resamples, seed=42, per-region n=17.

| Metric    | Mean   | 95% CI                | Threshold       | Status     |
|-----------|--------|-----------------------|-----------------|------------|
| Recall    | 0.8824 | [0.8339, 0.9240]      | ≥ 0.85          | borderline |
| Precision | 0.9401 | [0.9251, 0.9558]      | —               | —          |
| F1        | 0.9068 | [0.8840, 0.9255]      | ≥ 0.80          | pass       |
| FAR (gate)| 0.2500 | [0.1765, 0.3088]      | < 0.30          | borderline |
| MCC       | 0.6097 | [0.5578, 0.6665]      | —               | —          |

**Honesty note**: Recall CI lower bound (0.834) is just below the 0.85 KPI, and FAR CI upper bound (0.309) is just above the 0.30 KPI. Both are within sampling variability of the threshold — point estimates pass, interval bounds are borderline. Reported here without rounding-up.

### Granger Causality — Multiple Testing Correction

Tested family: 3 signal layers (L1 OTC / L2 wastewater / L3 search) for 서울특별시. Composite p reported separately (single national-aggregate test, not part of the family).

| Test             | Raw p   | Bonferroni | BH-FDR  | Significant (raw / bonf / bh) |
|------------------|---------|------------|---------|-------------------------------|
| L1 OTC           | 0.1031  | 0.3093     | 0.1547  | ✗ / ✗ / ✗                     |
| L2 wastewater    | 0.2670  | 0.8010     | 0.2670  | ✗ / ✗ / ✗                     |
| L3 search        | 0.0073  | 0.0219     | 0.0219  | ✓ / ✓ / ✓                     |
| Composite (national) | 0.0209 | —      | —       | ✓ (standalone)                |

**Honesty note**: L3 search trend survives both Bonferroni and BH-FDR corrections. L1 (OTC) and L2 (wastewater) do not reach significance after correction — L2's small sample (12 weeks) is the dominant cause, consistent with the L2 data-coverage limitation already noted. The composite national-aggregate test (p=0.0209) is significant on its own but is not subject to multi-test correction because it is one derived test, not many.

**Data gap (explicit)**: Per-region (17-region) Granger p-values are **not** computed in the current canonical artifacts. `analysis/lead_time_2025w48.py` runs Granger only for the Seoul case study. Extending to all 17 regions is the next step if reviewers require a 17-test family.

### Reproduction

```
.venv/bin/python analysis/bootstrap_ci.py
.venv/bin/python analysis/multiple_testing.py
```

Output:
- `analysis/outputs/bootstrap_ci_results.json`
- `analysis/outputs/multiple_testing_results.json`

Source: `analysis/bootstrap_ci.py`, `analysis/multiple_testing.py`. Canonical data unchanged (`analysis/outputs/backtest_17regions.json`, `analysis/outputs/lead_time_summary.json`).
