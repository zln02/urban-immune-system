# 부하테스트 — 조달청 공공SW 기준 p95 < 500ms 검증

## 개요

조달청 공공소프트웨어 납품 요건 및 B2G 판매 기준 충족 목적으로 FastAPI 백엔드(:8001)를 대상으로 부하테스트를 수행한다.

- **목표**: 모든 주요 엔드포인트 **p95 < 500ms** (50 동시 사용자 기준)
- **도구**: [Locust](https://locust.io/) v2.24+
- **시나리오**: `tests/load/locustfile.py`

---

## 실행 방법

### 사전 조건

```bash
# 1. uvicorn 가동 확인
curl http://localhost:8001/api/v1/alerts/regions

# 2. locust 설치 (없으면)
.venv/bin/pip install "locust>=2.24"
```

### 부하테스트 실행 (원스텝)

```bash
cd /home/wlsdud5035/urban-immune-system
bash tests/load/run_load_test.sh
```

### 수동 실행

```bash
# Step 1: git 브랜치
git checkout develop
git checkout -b feat/load-testing

# Step 2: 실행
.venv/bin/locust \
  -f tests/load/locustfile.py \
  --host http://localhost:8001 \
  --headless \
  --users 50 \
  --spawn-rate 2 \
  --run-time 6m \
  --csv tests/load/results \
  --html tests/load/results_report.html

# Step 3: 분석
.venv/bin/python tests/load/analyze_results.py
```

---

## 테스트 시나리오

| 엔드포인트 | 가중치 | 설명 |
|---|---|---|
| `GET /api/v1/alerts/regions` | 5 | 전국 17개 시·도 동시 경보 (메인 페이지) |
| `GET /api/v1/alerts/current?region=서울특별시` | 3 | 특정 지역 현재 경보 레벨 |
| `GET /api/v1/predictions/explain` | 1 | TFT XAI 변수 중요도 |
| `GET /api/v1/signals/timeseries?layer=otc&region=서울특별시&days=90` | 2 | OTC 계층 90일 시계열 |

### 부하 프로파일

```
사용자 수:  1 ──ramp up 60s──→ 50 ──유지 300s──→ ramp down 30s──→ 0
총 시간:    약 6분 (--run-time 6m)
spawn-rate: 2 users/s
```

---

## 측정 결과

> 아래 수치는 `analysis/outputs/load_test_results.json` 자동 갱신됨.
> 최초 실행 전에는 `bash tests/load/run_load_test.sh` 로 측정 필요.

### 최신 측정값 (2026-04-27, uvicorn :8001, 50 동시 사용자)

| 엔드포인트 | p50 | p95 | p99 | RPS | 실패율 | p95 목표 충족 |
|---|---|---|---|---|---|---|
| `/api/v1/alerts/regions` | — | — | — | — | — | 측정 필요 |
| `/api/v1/alerts/current` | — | — | — | — | — | 측정 필요 |
| `/api/v1/predictions/explain` | — | — | — | — | — | 측정 필요 |
| `/api/v1/signals/timeseries` | — | — | — | — | — | 측정 필요 |

> `run_load_test.sh` 실행 후 `analysis/outputs/load_test_results.json` 값으로 대체할 것.

---

## 조달청 기준 충족 여부

| 항목 | 기준 | 현황 |
|---|---|---|
| p95 응답시간 | < 500ms | 측정 후 갱신 |
| 에러율 | < 1% | 측정 후 갱신 |
| 동시 사용자 | 50명 기준 | 완료 |

---

## 결과 파일

| 파일 | 설명 |
|---|---|
| `tests/load/locustfile.py` | 부하 시나리오 |
| `tests/load/run_load_test.sh` | 원스텝 실행 스크립트 |
| `tests/load/analyze_results.py` | CSV → JSON + PNG 분석 |
| `tests/load/results_stats.csv` | locust 원본 통계 (실행 후 생성) |
| `tests/load/results_report.html` | locust HTML 리포트 (실행 후 생성) |
| `analysis/outputs/load_test_results.json` | 분석 결과 JSON |
| `analysis/outputs/load_test_summary.png` | 엔드포인트별 p95 bar chart |

---

## CI 연동 (GitHub Actions)

```yaml
# .github/workflows/load-test.yml 예시
- name: 부하테스트
  run: |
    .venv/bin/locust \
      -f tests/load/locustfile.py \
      --host http://localhost:8001 \
      --headless --users 10 --spawn-rate 1 --run-time 60s \
      --csv tests/load/results
    .venv/bin/python tests/load/analyze_results.py
```

> CI에서는 `--users 10`으로 축소 실행 권장 (빌드 시간 절약).

---

## 병목 대응 가이드

| 엔드포인트 | 예상 병목 | 대응 |
|---|---|---|
| `/alerts/regions` | DB DISTINCT ON + 17개 region 쿼리 | PostgreSQL `risk_scores(region, time DESC)` 복합인덱스 확인 |
| `/alerts/current` | `layer_signals` 28일 fallback 집계 | TimescaleDB continuous aggregate 또는 인덱스 추가 |
| `/predictions/explain` | `tft_metrics.json` 파일 I/O | 모듈 로드 시 캐싱 (현재 `_load_tft_metrics()` 매 호출마다 읽음) |
| `/signals/timeseries` | 90일 시계열 풀스캔 | `(layer, region, time)` 인덱스 확인, days 상한 축소 검토 |
