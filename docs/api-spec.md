# API 명세 (v1)

Swagger UI: `http://localhost:8000/docs`

## 기본 정보

| 항목 | 값 |
|------|-----|
| Base URL | `/api/v1` |
| 인증 | 없음 (MVP) |
| 응답 형식 | JSON |

---

## 신호 API (`/signals`)

### `GET /signals/latest`
각 Layer 최신 정규화 신호값 반환.

**파라미터**
| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| region | string | 서울특별시 | 지역명 |
| layer | enum | ALL | L1 / L2 / L3 / ALL |

**응답**
```json
{
  "region": "서울특별시",
  "layer": "ALL",
  "data": [
    { "layer": "L1", "value": 62.4, "time": "2025-01-07T00:00:00Z" },
    { "layer": "L2", "value": 78.1, "time": "2025-01-07T00:00:00Z" },
    { "layer": "L3", "value": 55.3, "time": "2025-01-07T00:00:00Z" }
  ],
  "updated_at": "2025-01-07T09:00:00Z"
}
```

### `GET /signals/timeseries`
주간 시계열 데이터 반환 (차트용).

**파라미터**: `region`, `layer`, `weeks` (1~52, 기본 12)

---

## 예측 API (`/predictions`)

### `GET /predictions/forecast`
TFT 7/14/21일 위험도 예측.

**응답**
```json
{
  "region": "서울특별시",
  "forecasts": {
    "7":  { "value": 68.2, "lower": 55.1, "upper": 81.3 },
    "14": { "value": 72.5, "lower": 58.0, "upper": 87.0 },
    "21": { "value": 65.1, "lower": 49.2, "upper": 81.0 }
  },
  "attention_weights": []
}
```

---

## 경보 API (`/alerts`)

### `GET /alerts/current`
현재 경보 레벨 + LLM 요약.

**응답**
```json
{
  "region": "서울특별시",
  "alert_level": "YELLOW",
  "composite_score": 64.3,
  "summary": "...",
  "recommendations": "...",
  "generated_at": "2025-01-07T08:30:00Z"
}
```

### `POST /alerts/generate`
RAG-LLM 리포트 비동기 생성 요청.

### `GET /alerts/explain/{report_id}`
특정 경보 리포트의 XAI 설명 반환. feature_values, rag_sources, model_metadata JSONB 컬럼을 펼쳐 반환하며, NULL 컬럼은 빈 객체/배열로 응답 (404 아님).

**파라미터**
| 이름 | 타입 | 위치 | 설명 |
|------|------|------|------|
| report_id | integer | path | alert_reports.id |

**응답 (200)**
```json
{
  "report_id": 42,
  "region": "서울특별시",
  "alert_level": "YELLOW",
  "summary": "독감 지수 상승 감지",
  "decision_factors": {
    "l1_otc": 35.2,
    "l2_wastewater": 42.1,
    "l3_search": 28.9,
    "composite": 36.7
  },
  "feature_values": { "l1_otc": 35.2, "l2_wastewater": 42.1, "l3_search": 28.9, "composite": 36.7 },
  "rag_citations": [
    { "topic": "multi_signal_cross_validation", "score": 0.45, "source": "ECDC 2024" }
  ],
  "model_metadata": { "model": "TFT", "version": "tft_synth_v2" },
  "audit": {
    "triggered_by": "system_scheduler",
    "trigger_source": "apscheduler_weekly",
    "created_at": "2026-04-26T12:00:00+00:00"
  }
}
```

**오류 응답**
| 코드 | 설명 |
|------|------|
| 404 | report_id 없음 |

---

## XAI 설명 API (`/predictions/explain`, `/alerts/explain`)

### `GET /predictions/explain`
TFT attention 기반 전역 예측 설명 (XAI). ml/outputs/tft_metrics.json 을 읽어 변수 중요도와 encoder step별 attention 가중치를 반환한다.

**파라미터**
| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| region | string | 서울특별시 | 지역명 (현재 전역 모델 기준; 향후 지역별 분리 예정) |

**응답 (200)**
```json
{
  "region": "서울특별시",
  "model": "TFT-temporal_fusion_transformer",
  "model_version": "tft_synth_v2",
  "best_val_loss": 1.882,
  "feature_importance": [
    { "variable": "confirmed_future_center", "importance": 0.269, "rank": 1 },
    { "variable": "l2_wastewater",           "importance": 0.224, "rank": 2 },
    { "variable": "encoder_length",          "importance": 0.152, "rank": 3 }
  ],
  "attention_per_encoder_step": [0.0417, 0.0416, 0.0416],
  "encoder_variable_names": ["encoder_length", "confirmed_future_center", "..."],
  "config": {
    "max_encoder_length": 24,
    "max_prediction_length": 3,
    "feature_cols": ["l1_otc", "l2_wastewater", "l3_search", "temperature", "humidity"],
    "target_col": "confirmed_future"
  },
  "interpretation": "confirmed_future_center와 l2_wastewater가 가장 중요한 결정 요인"
}
```
