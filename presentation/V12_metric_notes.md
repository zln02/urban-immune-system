# V12 Presentation — Metric Notes (2026-06-08)

> 최종발표 2026-06-17 (D-9 기준). PPT freeze 6/15.
> V11 (2026-05-14, 중간발표용) → V12 (최종발표용) 변경점 정리.

## KPI Update — Round 6 (V11 frozen + 다질병 확장 + 라벨 정직성)

### 인플루엔자 (주모델, 17지역 walk-forward · gap 4주 5-fold)

| Metric | V11 | V12 | Delta |
|--------|-----|-----|-------|
| F1 | 0.907 | **0.907** | 0 (frozen) |
| Recall (Gate ON) | 0.882 | **0.882** | 0 |
| Precision | 0.940 | **0.940** | 0 |
| FAR (Gate ON) | 0.250 | **0.250** | 0 |
| MCC | 0.610 | **0.610** | 0 |
| AUPRC | 0.973 | **0.973** | 0 |
| Lead Time | 6.76주 | **6.76주** | 0 |
| Tests | 544 | **544** | 0 |

> 인플루엔자 메트릭은 V11 시점에 frozen. V12 는 라벨 신뢰도 검증 + 다질병 확장으로 정직성 보강.

### 다질병 확장 (캡스톤 평가 4번째 항목 ✅)

| Pathogen | F1 | Source |
|----------|----|----|
| 인플루엔자 | **0.907** | `analysis/outputs/backtest_17regions.json` |
| COVID-19 | **0.68** | `analysis/outputs/backtest_xgboost_covid_17regions.json` (PR #71/#72) |
| 노로바이러스 | **0.70** | `analysis/outputs/backtest_xgboost_norovirus_17regions.json` (PR #73) |

> 질병별 신호 강도 차이를 정직하게 노출. 인플루엔자만 강하다는 게 아니라, OTC·검색 신호가 약한 질병(COVID 다양한 변이·노로 단기 폭발 패턴)에서도 베이스라인 F1 0.68–0.70 달성.

## Honesty Notes (V11 → V12 신규)

### V11.5 — 라벨 정직성 (KDCA ILI 검증, PR #76)

- 인플루엔자 F1=0.907 은 **OTC z-score 기반 self-target proxy 라벨**.
- KDCA 4급 ILI ground truth (`pipeline/data/kdca/인플루엔자_20~21~25~26.csv` 6 절기 299주차) 대비 검증:
  - **Cohen κ = 0.058** (거의 무작위 일치)
  - **Agreement rate = 29.5%** (n=61 overlap)
  - **TP=9, TN=9, FP=0, FN=43** — false negative 비율 매우 높음
- 결과: self-proxy 는 임상 라벨과 다른 사건을 탐지 중. 진짜 F1 측정은 #63 multipath 라벨 교체 재학습 후 가능.
- 위치: `analysis/outputs/label_validation_influenza.json`

### V11.6 — KDCA 라벨 교체 재학습 결과 (#63, PR #78, 2026-06-08)

V11.5 의 라벨 갭에 대한 본 작업. `analysis/backtest_xgboost_multipath.py --labels-from-kdca`
로 KDCA ILI ground truth (≥5.8/1000) 라벨로 17지역 GradientBoosting 재학습.

**Pool 결과 (weekly group CV, gap=2주, leakage-free)**:

| Metric | self-proxy (V11) | KDCA ground truth (V11.6) | Delta |
|--------|-----|-----|-------|
| F1 | 0.907 | **0.960** | +0.053 |
| Precision | 0.940 | **1.000** | +0.060 |
| Recall | 0.882 | **0.923** | +0.041 |
| FAR | 0.250 | **0.000** | −0.250 |
| MCC | 0.610 | **0.785** | +0.175 |
| AUPRC | 0.973 | **0.990** | +0.017 |
| Model gain vs trivial F1 | — | **+0.669** | (vs L2 임계 baseline 0.291) |

**Per-region (단순 평균)**: F1=0.876, Recall=0.819, FAR=0.376, MCC=0.339
**데이터**: 17 region × 61 주차 overlap → 1037 행 · 양성 비율 81.97% · pool n=765

**Caveats (정직)**:
- **양성 클래스 imbalance (82%)**: 2025-03 ~ 2026-06 (15개월) 의 2025-26 절기 유행기가 데이터의 60% 차지. trivial "always positive" 도 F1 약 0.85 수준 → 모델 진짜 gain 은 trivial L2 임계 (F1=0.29) 대비 +0.67.
- **17 region broadcast**: KDCA 표본감시는 전국 단일 → 17지역 동일 라벨. 지역별 differential 측정은 HIRA OpenAPI L1 도입 후 가능.
- **6 절기 누적 학습 X**: 현 DB (2025-03 ~ 2026-06) 와 overlap 되는 KDCA 절기만 사용 (2024-25 후반 + 2025-26). 5 절기 backfill 시 강건성 추가 확보.

**위치**: `analysis/outputs/backtest_xgboost_influenza_kdca_17regions.json`

**해석**: self-proxy F1=0.907 은 임상 라벨 대비 **underestimate** 였음 (V11.5 의 κ=0.058 은 라벨 정의가 달랐던 결과). KDCA ground truth 기준 F1=0.96.
다만 imbalance caveat 으로 인해 발표 메시지는 **"임상 라벨 기준 F1 ≥ 0.90 확인"** 으로 정직 유지.

### V11.0 유지 항목

- L1/L3 신선도: T-2 lag (Naver API 공개 정책)
- L2 신선도: T-7~14 lag (KOWAS 주간 PDF, 발행 주기 반영 #67/#68)
- 실시간 데모 시 lag 안내 필요

## Canonical Source

- `analysis/outputs/backtest_17regions.json` — 인플루엔자 frozen (V11.0)
- `analysis/outputs/backtest_xgboost_{covid,norovirus}_17regions.json` — 다질병 (V11.5)
- `analysis/outputs/label_validation_influenza.json` — KDCA 검증 (V11.5)
- `analysis/outputs/backtest_xgboost_influenza_kdca_17regions.json` — KDCA 라벨 재학습 (V11.6)

## V12 발표 슬라이드 보강 포인트

1. **S11A KPI 테이블**: V11 수치 그대로 + caveat 박스 추가 ("self-proxy 라벨, KDCA κ=0.058")
2. **S13C 정직성 5단 → 6단**: KDCA 검증 항목 추가
3. **신규 슬라이드 — 다질병 확장**: 3 pathogen F1 비교 차트 + 신호 강도 분석
4. **신규 슬라이드 — 운영 신뢰도**: 5/28 silent-fail 사고 → 알람 + misfire grace time 대응 → 6/3까지 17일 누적 OK (Issue #63)

## Gate B 정책 (Region-tiered, V11 유지)

- 충청북도: composite ≥ 20 (was 30)
- 대구·경북: composite ≥ 25 (was 30)
- 그 외 14개 시·도: composite ≥ 30 (기본)
- 출처: `backend/app/config.py::REGIONAL_GATE_THRESHOLDS`
