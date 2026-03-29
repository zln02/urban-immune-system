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

### `GET /predictions/anomaly`
Deep Autoencoder 이상탐지 결과.

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
