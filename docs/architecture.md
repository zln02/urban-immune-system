# Architecture Overview

> 마지막 갱신: 2026-05-02 · 발표 D-5 시점 기준
> Canonical 다이어그램: README.md Mermaid + 노션 PM Hub

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
 ├ wastewater     ─┼─→  │   uis.layer{1,2,3}      │   F1=0.882        App Router)
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

## ML 모델 현황 (2026-05-02)

| 모델 | 학습일 | 위치 | 상태 |
|---|---|---|---|
| XGBoost (앙상블 주모델) | 2026-04-29 | `ml/checkpoints/xgb_best.joblib` | ✅ F1=0.882 / Recall=0.837 / Precision=0.949 / FAR=0.206 (gate ON) / Lead 6.47주 / MCC=0.595 / AUPRC=0.973 (17지역 walk-forward, gap 4주 5-fold, `analysis/outputs/backtest_17regions.json`) |
| TFT-real (Lightning) | 2026-04-29 | `ml/checkpoints/tft_real/tft_best.ckpt` | ⚠️ epoch5 best val_loss=5.48, 26주 한계로 발산 — PoC 위치, 데이터 누적 후 prod |
| TFT-synth (Lightning) | 2026-04-26 | `ml/checkpoints/tft_synth/tft_best-v2.ckpt` | ✅ val_loss=1.88, attention top3 (검색·하수·OTC) 검증용 |
| Autoencoder | 2026-04-29 | `ml/checkpoints/autoencoder/model.pt` | ✅ 99p threshold 적용 후 17지역 inference 1/17 정상화 (`ff17dfa`) |

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
- **운영(현재)**: GCP e2-standard-2 단일 노드 `${UIS_HOST}` (예: `34.47.113.176`, static IP `uis-capstone-ip` 예약 완료 — 2026-05-04)
- **K8s 매니페스트**: `infra/k8s/` 정의 완료, Phase 4 배포 예정
- **CI**: `.github/workflows/ci.yml` 6잡 (backend-lint·test, pipeline-lint, ml-lint, frontend-lint(tsc), legacy-test) · coverage gate `--cov-fail-under=35`

## 보안 / 컴플라이언스

- API 키 전부 `.env` (Pydantic Settings · `os.getenv` 직접 사용 금지)
- 프로덕션 환경 검증: `database_url` placeholder · `ml_service_url` https 강제 (`backend/app/config.py`)
- K8s SecurityContext: `runAsNonRoot`, `readOnlyRootFilesystem`, drop ALL capabilities
- Phase 4 ISMS-P 풀 점검 + 조달청 혁신제품 신청 예정
- DPIA 초안 `docs/business/advisory/22_dpia_draft.md`

## 한계 (정직)

- L1·L3 는 네이버 API 제약으로 **전국 단일값 → 17지역 broadcast** (`pipeline/collectors/otc_collector.py` 의 zero-collapse 핫픽스 `07c9c5a` 이후). HIRA OpenAPI 교체로 Phase 3 에서 지역 분리.
- L2 KOWAS 는 PDF 수동 추출 (Selenium 자동화 Phase 3).
- TFT-real 26주 데이터로 발산 → 12주 추가 누적 후 재학습.

## Future (Phase 4+)

- TFT → PatchTST/IPatch/TimeMixer 비교 R&D (TFT 대비 24% MSE 개선 보고, 데이터 누적 전제)
- Next.js 14.2.3 → 15.2 마이그레이션 (Turbopack HMR 5–10× · React 19 강제)
- FastAPI 마이너 동기화 (Pydantic v2.7+ 50× validation)
- 1개 추가 질병/국가 확장 데모 (캡스톤 평가 4번째 항목)
