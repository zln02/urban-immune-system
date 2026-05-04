# Urban Immune System — 시스템 구조 요약

## 6단계 데이터 흐름 (좌→우)

```
┌──────────────┐   ┌────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────┐   ┌──────────────┐
│ 입력 · 3계층 │ → │ Kafka  │ → │ TimescaleDB  │ → │ 앙상블 + 게이트 B │ → │ AI 추론  │ → │ Dashboard   │
│ 약국·하수    │   │ 토픽 4 │   │ 주간 파티션  │   │ w1·L1+w2·L2+w3·L3│   │ TFT·AE   │   │ Next.js·SSE  │
│ ·검색       │   │ 7일 보관│   │ 시계열 DB    │   │ (단일신호 차단)  │   │ ·RAG     │   │ 4단계 경보   │
└──────────────┘   └────────┘   └──────────────┘   └──────────────────┘   └──────────┘   └──────────────┘
```

## 핵심 코드 위치

| 모듈 | 책임 | 파일 |
|---|---|---|
| 약국 OTC 수집 | 네이버 쇼핑인사이트 (감기약·해열제 등 5 키워드) | `pipeline/collectors/otc_collector.py` |
| 하수 KOWAS 파싱 | PDF 픽셀 RGB → 농도 추출 (자체 개발) | `pipeline/collectors/kowas_parser.py` |
| 검색 트렌드 | 네이버 DataLab (독감 증상·고열 원인 등 4 키워드) | `pipeline/collectors/search_collector.py` |
| 정규화 | Min-Max 0~100 (계층 독립) | `pipeline/collectors/normalization.py` |
| 앙상블 + 게이트 B | composite = 0.35·L1 + 0.40·L2 + 0.25·L3 + 2계층 30+ 강제 | `pipeline/scorer.py` |
| XGBoost 회귀 | walk-forward 5-fold gap=4주 | `ml/xgboost/model.py` |
| TFT 시계열 | 24주 → 7·14·21d 예측 + Attention top-3 | `ml/tft/train_real.py` |
| Autoencoder 이상탐지 | 재구성 오차 95% 분위 | `ml/anomaly/autoencoder.py` |
| RAG 리포트 | Claude + Qdrant top-5 + KDCA 9섹션 강제 | `ml/rag/report_generator.py` |

## DB 스키마 (TimescaleDB 3 hypertable)

```sql
-- 원시 신호 (계층별)
layer_signals (time, region, layer, value, pathogen)
  └ HYPERTABLE: time 기준 주간 자동 분할
  └ INDEX: (layer, region, time DESC)

-- 종합 위험점수
risk_scores (time, region, composite_score, l1·l2·l3_score, alert_level)
  └ HYPERTABLE
  └ DELETE+INSERT 멱등 패턴 (같은 명령 두 번 돌려도 동일)

-- AI 경보 리포트
alert_reports (time, region, alert_level, summary, recommendations,
               feature_values, rag_sources, model_metadata,
               triggered_by, trigger_source)
  └ JSONB 컬럼으로 XAI 메타데이터 저장 (ISMS-P 2.9 감사 대응)
```

## 게이트 B 핵심 로직 (코드 4줄)

```python
# pipeline/scorer.py
_CROSS_VALIDATION_MIN_LAYERS = 2          # 2개 이상 계층 동시 발화
_CROSS_VALIDATION_LAYER_THRESHOLD = 30.0  # 각 계층 30점 이상

def determine_alert_level(composite, l1, l2, l3):
    raw = "RED" if composite >= 75 else \
          "ORANGE" if composite >= 55 else \
          "YELLOW" if composite >= 30 else "GREEN"
    if raw == "GREEN": return "GREEN"
    above = sum(1 for v in (l1,l2,l3) if v and v >= 30)
    if above < 2: return "GREEN"   # 단일신호 차단
    return raw
```

## Walk-forward 검증 (시간 누출 차단)

```python
# ml/xgboost/model.py
tscv = TimeSeriesSplit(n_splits=5, gap=4)   # 4주 갭 = 한 달치 미래 차단

for train_idx, val_idx in tscv.split(X):
    model.fit(X[train_idx], y[train_idx])
    pred = model.predict(X[val_idx]) > 55
    f1_scores.append(f1_score(y[val_idx], pred))
```

## 수치 (17지역 백테스트)

- F1 0.841 / Precision 0.960 / Recall 0.768 / AUC 0.931
- 가짜경보율 0.162 (게이트 OFF 0.538에서 76% 감소)
- 평균 5.9주 선행 (세종 9주·부산·제주 8주·서울 7주·경기 6주)
- Granger 인과검정 composite p=0.021 / L3 p=0.007

## 기술 스택

| 계층 | 기술 |
|---|---|
| 수집 | Python 3.11 · httpx · APScheduler · Selenium (KOWAS) · pdfplumber |
| 메시지 | Apache Kafka (토픽 4개 · acks=all retries=3 · 7일 보관) |
| DB | TimescaleDB (PostgreSQL 14 + timescaledb extension) |
| ML | scikit-learn (XGBoost) · PyTorch Forecasting (TFT) · PyTorch (AE) |
| RAG | Qdrant · Anthropic Claude Sonnet 4.6 · sentence-transformers |
| 백엔드 | FastAPI · asyncpg · Pydantic v2 |
| 프론트 | Next.js 14 App Router · Deck.gl v9 · Recharts · SWR · Tailwind |
| 인프라 | Docker Compose · Kubernetes (보안 컨텍스트) · GitHub Actions CI |
| 테스트 | pytest 128 케이스 (정규화·DB·API·보안) |
