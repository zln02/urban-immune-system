# 실 임상 데이터 기반 감염병 사전예측 모델 (CDC ILINet)

> 작성 2026-06-19 · 모듈 `ml/forecast/` · 검증 산출물 `analysis/outputs/forecast_ilinet_validation.json`

## 1. 배경 — 왜 새로 만들었나

기존 XGBoost 인플루엔자 모델의 헤드라인 성능(F1=0.907)은 **self-target proxy 라벨**
(OTC z-score 기반)으로 측정된 값이었다. 그러나 이 proxy 라벨은 실제 임상 정답인
**KDCA 4급 ILI**와 비교 시 **Cohen κ=0.058 / 일치도 29.5%** (`analysis/outputs/label_validation_influenza.json`)
로, 사실상 임상과 무상관이었다. 즉 "임상 확진을 1–3주 선행 예측한다"는 핵심 주장이
실제 임상 데이터로 검증된 적이 없었다.

이 모듈은 그 갭을 닫는다: **실제 임상 감시 지표를 ground truth 로 직접 사용**하고,
누수 없는 walk-forward 로 사전예측 성능을 검증한다.

## 2. 데이터 — 전부 실측

| 구분 | 소스 | 내용 |
|---|---|---|
| **임상 정답 (target)** | CDC ILINet (Delphi Epidata `fluview`) | 가중 ILI%(wILI) — 미국 외래 표본감시 실 임상 데이터. CDC FluSight 예측대회와 동일한 표준 타깃 |
| 범위 | 2003w40 – 2024w20 | **21개 인플루엔자 시즌, 11,847주-권역** |
| 권역 | 전국(nat) + HHS 1–10 | **11개 권역 다지역 검증** |

> ILINet wILI 는 미 전역 외래에서 ILI(발열+기침/인후통) 환자 비율을 가중집계한 값으로,
> 임상 확진의 표준 대리지표다. 데이터는 `ml/forecast/epidata_client.py` 가 1회 다운로드 후
> `ml/data_cache/` 에 캐시한다(공개 엔드포인트, 인증 불필요).

## 3. 유행(epidemic)·개시(onset) 라벨 — CDC 방식, 누수 차단

- **baseline**: 권역별 **직전 3시즌 비유행기(off-season, MMWR 21–39주) 평균 + 2·SD**
  (CDC ILINet baseline 산정 방식). 시즌 S 의 baseline 은 season<S 표본만 사용 → 미래 누출 없음.
- **epidemic[t]** = `wILI[t] ≥ baseline` (당주 유행 상태, 실 임상 정답)
- **onset** = 시즌별 연속 2주 이상 유행이 시작된 첫 주

## 4. 모델 — per-horizon 분위 앙상블 + 조기경보 분류기

- **점예측**: XGBoost + LightGBM 앙상블. persistence 대비 **변화량(Δ)** 을 학습(잔차 학습)해
  단순 지속모델을 능가. 피처 24종(lag·momentum·가속도·rolling·계절 harmonic·전국맥락·기후학적 기대값 등),
  모두 시각 t 까지 관측 가능한 정보만 사용.
- **예측구간**: XGBoost 다분위(`reg:quantileerror`) [2.5/25/50/75/97.5%] → WIS·coverage 평가.
- **조기경보**: XGBoost 분류기로 `P(h주 후 유행)` 추정.
- 지평: **1·2·3·4주 선행**.

## 5. 검증 — 시즌 단위 walk-forward (2010–2023, 14시즌 holdout)

검증 시즌 S 는 season<S 데이터로만 학습(baseline·climatology 포함 전부 누수 차단).

### 5.1 회귀 예측 정확도 (wILI, %포인트)

| 지평 | MAE | RMSE | skill vs persistence | skill vs climatology |
|---|---|---|---|---|
| 1주 | 0.196 | 0.341 | **+19.4%** | +73.5% |
| 2주 | 0.302 | 0.531 | **+23.8%** | +60.0% |
| 3주 | 0.401 | 0.706 | **+24.7%** | +48.4% |
| 4주 | 0.485 | 0.844 | **+26.1%** | +39.8% |

→ 모든 지평에서 persistence·climatology 두 기준모델을 모두 능가(실질적 예측 skill 존재).

### 5.2 확률예측 보정 (calibration)

| 지평 | WIS↓ | 95% 구간 coverage |
|---|---|---|
| 1주 | 0.124 | 94.8% |
| 2주 | 0.187 | 92.8% |
| 3주 | 0.241 | 91.7% |
| 4주 | 0.285 | 90.8% |

→ 95% 예측구간이 실제 90.8–94.8% 를 포함 — 잘 보정된 불확실성.

### 5.3 유행 조기경보 (실 임상 라벨 대비)

| 지평 | Precision | Recall | F1 | MCC | AUPRC (baseline) |
|---|---|---|---|---|---|
| 1주 | 0.943 | 0.932 | **0.937** | 0.890 | 0.987 (0.433) |
| **2주** | 0.920 | 0.902 | **0.911** | 0.845 | 0.975 (0.433) |
| 3주 | 0.906 | 0.874 | 0.890 | 0.809 | 0.960 (0.434) |
| 4주 | 0.889 | 0.848 | 0.868 | 0.771 | 0.941 (0.435) |

> **핵심**: 기존 F1=0.907 은 κ=0.058 self-proxy 라벨 기준이었다. 동일 수준(2주 선행 F1=**0.911**)을
> **실제 임상(ILINet) 정답**으로 재현·검증했다. 공모전 검증 기준(F1≥0.80)을 실 임상 데이터로 충족.

### 5.4 유행개시 리드타임 (2주 선행 경보)

- 유행 발생 권역-시즌 **138개 중 98.55% 에서 임상 onset 이전 경보 발령**
- 평균 선행 **1.96주** / 중앙값 1.0주 (경보 지평 2주에 의해 상한)
- 유행 미발생 권역-시즌 16개(대부분 COVID 교란 2020-21 시즌, 독감 소멸) 중 오경보 25%

## 6. 정직한 한계

- **지역**: 미국 HHS 권역(영어권 공개 임상 감시). 한국(KDCA) 17시도 ILI 는 공개 API 미개방으로
  본 환경에서 미수집 → 한국 적용은 동일 파이프라인에 KDCA 연동 시 즉시 가능(코드 일반화 완료).
- **리드타임**: 2주 경보 지평의 구조적 상한. 더 긴 리드는 3·4주 분류기로 확장 가능(성능은 5.3 참조).
- **2020-21 시즌**: NPI 로 인플루엔자가 거의 소멸 → onset 미발생, 리드타임 통계에서 자동 제외.
- 본 모델은 인플루엔자(ILI) 대상. COVID/노로 등은 동일 프레임에 해당 임상 시계열 연동 시 확장.

## 7. 재현 / 서빙

```bash
# 1) 데이터 캐시 + walk-forward 임상 검증 (→ analysis/outputs/forecast_ilinet_validation.json)
PYTHONPATH=. python -m ml.forecast.validate

# 2) 전체 학습 + 최신 예측 산출 (→ ml/checkpoints/forecast/, analysis/outputs/forecast_ilinet_latest.json)
PYTHONPATH=. python -m ml.forecast.train
```

백엔드 API (대시보드/외부 제공):
- `GET /api/v1/forecast/validation` — 검증 메트릭 전체
- `GET /api/v1/forecast/latest` — 권역별 1–4주 선행 예측(점·95%구간·경보확률)
- `GET /api/v1/forecast/regions` — 경보 권역 요약(2주 후 baseline 초과 확률순)
