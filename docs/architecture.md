# Architecture Overview

> 마지막 갱신: 2026-06-08 · **최종발표 D-9 시점 (2026-06-17)** · PPT freeze 6/15
> Canonical 다이어그램: README.md Mermaid + 노션 PM Hub
> 중간발표 (2026-05-07 ✅) 산출물 아카이브: `analysis/outputs/archive/midterm-2026-05-07/`

## Purpose

Urban Immune System (UIS) 은 시민 비의료 신호 3개(약국 OTC · 하수 바이오마커 · 검색 트렌드)를 융합해 임상 확진보다 **1–3주 선행하는 감염병 조기경보**를 한국 보건당국(KDCA·지자체)에 SaaS/PoC 로 공급하는 B2G 시스템이다.

## 3-Layer 데이터 모델

| Layer | 소스 | 주기 | 정규화 | 선행성(중앙값) |
|---|---|---|---|---|
| L1 OTC | 네이버 쇼핑인사이트 (감기약·해열제·종합감기약·타이레놀·판콜) | 주1 (월 09:00) | Min-Max 0–100 | 1–2주 |
| L2 Wastewater | KOWAS PDF (인플루엔자 RT-PCR copies/mL) | 주1 (화 10:00) | Min-Max 0–100 | 2–3주 |
| L3 Search | 네이버 DataLab (독감 증상·인플루엔자·타미플루 등) | 주1 (월 09:05) | Min-Max 0–100 | 1–2주 |
| AUX | 기상청 KMA (기온·습도·강수) | 시간단위 | -20~40°C → 0–100 | (피처 only) |

> L3 단독 경보 절대 금지 (Google Flu Trends 과대예측 교훈). 2개 이상 계층 동시 임계 초과 게이트.

## 컴포넌트 토폴로지

```
[수집]                 [스트리밍/저장]            [추론]              [전달]
pipeline/collectors/   docker-compose:           ml/                 frontend/
 ├ otc_collector  ─┐    ├ Kafka KRaft             ├ xgboost          (Next.js 14.2.3
 ├ wastewater     ─┼─→  │   uis.layer{1,2,3}      │   F1=0.907        App Router)
 ├ search         ─┘    │   uis.aux.weather       ├ tft (real/synth)   ↑
 └ weather              ├ TimescaleDB             │   Lightning ckpt   │
                        │   layer_signals         ├ anomaly             SSE
                        │     hypertable          │   autoencoder       ↑
                        └ Qdrant                  └ rag                backend/
                          epidemiology_docs           Claude Haiku ─→  FastAPI :8001
                                                      Qdrant top_k=5     ├ /api/v1/signals/*
                                                                          ├ /api/v1/predictions/*
                                                                          ├ /api/v1/alerts/* (SSE)
                                                                          ├ /api/v1/chat/* (SSE)
                                                                          └ /api/v1/health
```

## ML 모델 현황 (2026-06-08)

| 모델 | 학습일 | 위치 | 상태 |
|---|---|---|---|
| XGBoost — 인플루엔자 (앙상블 주모델) | 2026-06-03 | `ml/checkpoints/xgb_best.joblib` | ✅ F1=0.907 / Recall=0.882 / Precision=0.940 / FAR=0.250 (gate ON) / Lead 6.76주 / MCC=0.610 / AUPRC=0.973 (17지역 walk-forward, gap 4주 5-fold, self-target proxy, `analysis/outputs/backtest_17regions.json`) |
| XGBoost — COVID-19 (다질병 ✅) | 2026-06-03 | `analysis/outputs/backtest_xgboost_covid_17regions.json` | ✅ F1=0.68 (pathogen selector 활성화, PR #71/#72) |
| XGBoost — 노로 (다질병 ✅) | 2026-06-03 | `analysis/outputs/backtest_xgboost_norovirus_17regions.json` | ✅ F1=0.70 (transition 타깃 우위 입증, PR #73) |
| TFT-real (Lightning) | 2026-06-01 | `ml/checkpoints/tft_real/tft_best.ckpt` | ⚠️ epoch5 best val_loss=5.48, 26주 한계로 발산 — PoC 위치, +12주 누적 후 prod |
| TFT-synth (Lightning) | 2026-04-26 | `ml/checkpoints/tft_synth/tft_best-v2.ckpt` | ✅ val_loss=1.88, attention top3 (검색·하수·OTC) 검증용 |
| Autoencoder | 2026-04-29 | `ml/checkpoints/autoencoder/model.pt` | ✅ 99p threshold 적용 후 17지역 inference 1/17 정상화 (`ff17dfa`) |

> **V11.5 라벨 정직성**: XGBoost 인플루엔자 메트릭은 OTC z-score 기반 self-target proxy 라벨. KDCA 4급 ILI ground truth (`analysis/outputs/label_validation_influenza.json`) 대비 Cohen κ=0.058, agreement 29.5% (n=61). Phase 3 #63 라벨 교체 재학습 진행 중.

> 합성 평가 메트릭(`anomaly_metrics.json` 의 `evaluation.precision=0.051`)은 **artificial spike** 실험 결과로, 실제 17지역 inference (`real_data_inference`) 와 무관. 발표 데모는 후자 사용.

## 앙상블 경보 로직

```
composite = w1·L1 + w2·L2 + w3·L3
default w = (0.35, 0.40, 0.25)        # backend/app/config.py 단일 출처

GREEN  : composite < 30
YELLOW : 30 ≤ composite < 55          # 게이트: 2개 이상 계층 ≥ 30
RED    : composite ≥ 75
```

## 프런트 / 발표 경로

- `frontend/src/app/dashboard/page.tsx` — 17개 시도 지도 + KPI + Granger/CCF + SSE 경보 + Claude Haiku RAG 리포트 + 4쪽 PDF 다운로드
- `frontend/src/components/map/korea-map-naver.tsx` — `NEXT_PUBLIC_NAVER_MAPS_KEY_ID` 존재 시 네이버 지도, 없으면 기존 `KoreaMap` SVG fallback
- `src/app.py` (Streamlit) — Phase 1 fallback, 데모 백업용

## 인프라 / 배포

- **개발**: `docker compose up -d` (Kafka KRaft + TimescaleDB + Qdrant + kafka-ui)
- **운영(현재)**: GCP e2-standard-2 단일 노드 `${UIS_HOST}` (예: `REDACTED-HOST`, static IP `uis-capstone-ip` 예약 완료 — 2026-05-04)
- **K8s 매니페스트**: `infra/k8s/` 정의 완료, Phase 4 배포 예정
- **CI**: `.github/workflows/ci.yml` 6잡 (backend-lint·test, pipeline-lint, ml-lint, frontend-lint(tsc), legacy-test) · coverage gate `--cov-fail-under=35`

## 보안 / 컴플라이언스

- API 키 전부 `.env` (Pydantic Settings · `os.getenv` 직접 사용 금지)
- 프로덕션 환경 검증: `database_url` placeholder · `ml_service_url` https 강제 (`backend/app/config.py`)
- K8s SecurityContext: `runAsNonRoot`, `readOnlyRootFilesystem`, drop ALL capabilities
- Phase 4 ISMS-P 풀 점검 + 조달청 혁신제품 신청 예정
- DPIA 초안 `docs/business/advisory/22_dpia_draft.md`

## 한계 (정직)

- **라벨 정직성 (V11.5)**: 인플루엔자 F1=0.907 은 OTC z-score 기반 self-target proxy. KDCA 4급 ILI ground truth 대비 Cohen κ=0.058 — `analysis/outputs/label_validation_influenza.json`. Phase 3 #63 라벨 교체 재학습 진행 중.
- **지역 분리**: L1·L3 는 네이버 API 제약으로 **전국 단일값 → 17지역 broadcast** (`pipeline/collectors/otc_collector.py` 의 zero-collapse 핫픽스 `07c9c5a` 이후). HIRA OpenAPI 교체로 Phase 3 에서 지역 분리.
- **L2 자동화 + carry-forward**: KOWAS PDF httpx 자동 다운로더 + APScheduler 주간 잡 + cron fallback 작동 중 (매주 화 09:30). 그러나 운영 DB audit (`analysis/outputs/kowas_carry_forward_audit.json`, 2026-06-08) 결과 17지역 40주 KOWAS L2 데이터의 **60.7% 가 같은 value 연속** — KOWAS 게시 지연 / PDF 픽셀 분석 일관성 / scheduler silent miss 분리 불가. Phase 3: `layer_signals.meta` JSONB 컬럼 추가 + fallback 마커 운영 적용.
- **TFT-real**: 26주 데이터로 발산 → 12주 추가 누적 후 재학습.
- **다질병 신호 편차**: COVID F1=0.68 / 노로 F1=0.70 — 인플루엔자 대비 OTC·검색 신호 약함 (질병별 행동 패턴 차이).

## Phase 로드맵 (2026-06-08 기준)

| Phase | 상태 | 주요 작업 | 마감 |
|---|---|---|---|
| 1 — Streamlit MVP | ✅ 완료 | 3-Layer 합성 PoC | 2026-03 |
| 2 — Phase 2 통합 | ✅ 완료 | FastAPI + Kafka + TimescaleDB + Qdrant + Next.js + SSE/RAG + XGBoost 17지역 | 2026-04 |
| 3 — 최종발표 (현재) | 🔧 진행중 | KDCA ILI 라벨 검증 ✅, multipath 라벨 교체 재학습 (#63), 다질병 (COVID/노로) ✅, OTC completeness 알람 ✅, KOWAS 자동 크롤링, HIRA OpenAPI | **2026-06-17** |
| 4 — 운영화 | 📋 예정 | ISMS-P 풀 점검, 조달청 혁신제품 신청, 파일럿 기관 (KDCA·서울시·WHO 협력센터), TFT-real prod 전환 | 2026-07~ |
| 5 — R&D | 📋 예정 | TFT → PatchTST/IPatch/TimeMixer 비교, Next.js 14→15.2, FastAPI Pydantic v2.7+, Kafka KRaft consumer 실연결 | 2026-Q3+ |
