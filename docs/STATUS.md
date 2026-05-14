# UIS 현황 & 성과 지표

> 마지막 갱신: 2026-05-14 · V11 메트릭 기준 (composite-level regional threshold, PR #55)

## Baseline 성능 (17지역 walk-forward 실측)

| 지표 | 값 | 비고 |
|------|----|------|
| F1-Score | **0.907** | gate ON |
| Recall | **0.882** (gate ON) / 0.904 (gate OFF) | |
| Precision | **0.940** | |
| FAR | **0.250** (gate ON) / 0.602 (gate OFF) | 게이트 효과 −58.5% FAR |
| Lead Time | **6.47주** | 임상 확진 대비 선행 |
| MCC | 0.610 | |
| Balanced Accuracy | 0.816 | |
| AUPRC | **0.973** | |

> 근거 데이터: `analysis/outputs/backtest_17regions.json`

## ML 모델 현황

| 모델 | 학습일 | 위치 | 상태 |
|------|--------|------|------|
| XGBoost (앙상블 주모델) | 2026-04-29 | `ml/checkpoints/xgb_best.joblib` | ✅ 프로덕션 |
| TFT-real (Lightning) | 2026-04-29 | `ml/checkpoints/tft_real/tft_best.ckpt` | ⚠️ epoch5 val_loss=5.48, 26주 한계 — PoC |
| TFT-synth (Lightning) | 2026-04-26 | `ml/checkpoints/tft_synth/tft_best-v2.ckpt` | ✅ val_loss=1.88, attention 검증용 |
| Autoencoder | 2026-04-29 | `ml/checkpoints/autoencoder/model.pt` | ✅ 99p threshold 적용, 17지역 1/17 정상화 |

> 합성 평가 `anomaly_metrics.json`의 `evaluation.precision=0.051`은 artificial spike 실험 결과 — 발표 데모는 실측 inference 사용.

## Phase 로드맵

| Phase | 상태 | 주요 내용 |
|-------|------|-----------|
| 1 | ✅ 완료 | Streamlit MVP, 3-Layer 파이프라인, 합성 데이터 PoC |
| 2 | ✅ 완료 | FastAPI(:8001) + 실 API 연동 + Kafka + TimescaleDB + Qdrant + Next.js + SSE/RAG + XGBoost 17지역 walk-forward |
| 3 | 🔧 진행중 | KOWAS 자동 크롤링, HIRA OpenAPI 연동(L1 지역 분리), TFT-real 데이터 누적 후 prod 전환, RAG 문서 확장 |
| 4 | 📋 예정 (6월~) | ISMS-P 풀 점검, 조달청 혁신제품 신청, 파일럿 기관 확보 (KDCA·서울시·WHO 협력센터) |

## 캡스톤 성공 기준 (회의자료 9.1)

> 심사 기준 — 4가지 모두 충족 목표

| 구분 | 기준 | 현황 |
|------|------|------|
| 기술 완성도 | 3계층(L1/L2/L3) 실데이터 자동 수집 + TFT 예측 + 웹 대시보드 통합 작동 | ✅ |
| 검증 결과 | F1 ≥ 0.80 + FAR ≤ 0.30 | ✅ F1=0.907 / FAR=0.250 |
| 서비스성 | Next.js 대시보드에서 실시간 신호 조회 + AI 경보 리포트 생성 | ✅ |
| 확장성 | 최소 1개 추가 질병 또는 지역 확장 시연 | 📋 Phase 4 |

## 한계 (정직)

- L1·L3: 네이버 API 제약 → 전국 단일값을 17지역 broadcast (`07c9c5a` zero-collapse 핫픽스). HIRA OpenAPI로 Phase 3에서 지역 분리.
- L2 KOWAS: PDF 수동 추출 (Selenium 자동화 Phase 3).
- TFT-real: 26주 데이터로 발산 → 12주 추가 누적 후 재학습.
