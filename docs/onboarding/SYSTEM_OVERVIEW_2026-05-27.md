# Urban Immune System — 시스템 구성 보고서 (확장·온보딩용)

> 작성일: 2026-05-27 · 작성: 박진영 (PM/ML Lead) · 대상: 신규 합류 팀/협업 파트너
> 목적: 다른 팀과 시스템을 함께 확장하기 위한 **전체 구조 설명서 + 온보딩 가이드**
> 본 문서는 운영 스냅샷 기준이며, 코드의 SSOT는 각 모듈 `CLAUDE.md`와 `docs/architecture.md`다.

---

## 0. 한 장 요약

**비의료(non-clinical) 신호 3계층을 융합해 감염병을 임상 신고보다 평균 6.47주 선행 탐지하는 B2G 조기경보 SaaS 프로토타입.**

- 약국 OTC 구매(L1) · 하수 바이오마커(L2) · 검색 트렌드(L3) → 가중 융합 → 위험도 점수 → 경보 게이트
- 주모델 **XGBoost**(프로덕션) + **TFT**(해석성 보조 PoC) + **Autoencoder**(이상탐지)
- 핵심 안전장치: **단일 계층 단독 경보 금지** — 최소 2개 계층 교차검증을 게이트 로직으로 강제 (Google Flu Trends 과대예측 실패 교훈)
- 검증: 17개 시·도 walk-forward 백테스트, **F1 0.907 / Recall 0.882 / FAR 0.250(gate ON) / Lead 6.47주**
- 운영: GCP e2-standard-2 (34.47.113.176), systemd 5개 + Docker 4개 컨테이너 상시 구동

---

## 1. 접속 정보 (대시보드 / API)

### 1.1 현재 바인딩 상태 (중요)

보안 정책(ISMS-P)상 **애플리케이션 포트는 전부 loopback(127.0.0.1)에만 바인딩**돼 있다.
즉, `http://34.47.113.176:3000` 같은 직접 외부 접속은 **막혀 있다** (의도된 설계).

| 서비스 | 내부 주소 | 외부 직접 접속 |
|---|---|---|
| 🖥️ 대시보드 (Next.js) | `127.0.0.1:3000` | ❌ (loopback) |
| ⚙️ Backend API (FastAPI) | `127.0.0.1:8001` | ❌ (loopback) |
| 🧠 ML 추론 (FastAPI) | `127.0.0.1:8002` | ❌ (loopback) |
| 🗄️ TimescaleDB | `0.0.0.0:5432` | ⚠️ 노출됨 (방화벽으로 차단 필요) |
| 🔎 Qdrant | `0.0.0.0:6333` | ⚠️ 노출됨 |
| 📨 Kafka | `0.0.0.0:9092` | ⚠️ 노출됨 |
| 📊 kafka-ui | `0.0.0.0:8080` | ⚠️ 노출됨 |

> ⚠️ DB/Qdrant/Kafka가 `0.0.0.0`으로 열려 있는 건 보안 결함 후보다. GCP 방화벽 인바운드에서 5432/6333/9092/8080을 사내 IP로 제한할 것 (확장 시 1순위 조치, §8 참고).

### 1.2 대시보드 접속 방법 — SSH 포트 포워딩 (현재 권장)

본인 PC에서:

```bash
# 대시보드 + API + ML을 한 번에 터널링
ssh -L 3000:127.0.0.1:3000 \
    -L 8001:127.0.0.1:8001 \
    -L 8002:127.0.0.1:8002 \
    wlsdud5035@34.47.113.176

# 터널 연결된 상태에서 브라우저 접속:
#   대시보드   → http://localhost:3000
#   API 문서   → http://localhost:8001/docs   (Swagger UI)
#   ML 헬스    → http://localhost:8002/health
```

### 1.3 외부 팀에게 열어줄 때 (확장 시 절차)

직접 `0.0.0.0` 바인딩은 금지. 다음 중 하나로 인증 게이트를 두고 노출한다.

1. **nginx 리버스 프록시 + Basic Auth/OIDC** (단기) — 현재 nginx는 설치돼 있으나 inactive
2. **GCP IAP (Identity-Aware Proxy)** (권장, B2G 친화) — 구글 계정 기반 접근 통제
3. **Cloudflare Tunnel + Access** (도메인 필요 시)

어느 경우든 ISMS-P 관점에서 **접근 로그 + 인증**이 필수. loopback 바인딩 자체는 유지하고 프록시만 외부에 노출.

---

## 2. 아키텍처 개요

```
                       ┌─────────────────────────────────────────┐
                       │            외부 데이터 소스               │
                       │  네이버 쇼핑인사이트 / 데이터랩 / KDCA    │
                       └──────────────────┬──────────────────────┘
                                          │ (수집)
                  ┌───────────────────────▼───────────────────────┐
                  │   pipeline/  — APScheduler (uis-scheduler)     │
                  │   3계층 수집 → 정규화 → 가중 융합 → 게이트     │
                  └───────────────────────┬───────────────────────┘
                                          │ (적재)
        ┌─────────────────────────────────▼─────────────────────────────────┐
        │  TimescaleDB :5432   layer_signals · confirmed_cases · risk_scores │
        │  Qdrant :6333  (RAG 임베딩)   ·   Kafka :9092 (이벤트 스트림)      │
        └───────────────┬───────────────────────────────┬───────────────────┘
                        │                                │
        ┌───────────────▼────────────┐     ┌─────────────▼──────────────┐
        │  backend/ FastAPI :8001     │◄───►│  ml/ FastAPI :8002          │
        │  signals·alerts·predict·chat│     │  XGBoost · TFT · Autoencoder│
        └───────────────┬─────────────┘     └─────────────────────────────┘
                        │ (REST + SSE)
        ┌───────────────▼─────────────┐
        │  frontend/ Next.js 14 :3000 │  실시간 대시보드 (SSE 스트림)
        └─────────────────────────────┘
```

### 데이터 흐름 (한 사이클)

1. **수집**: `pipeline/`의 스케줄러가 L1(네이버 쇼핑인사이트)·L2(KDCA 하수)·L3(네이버 데이터랩) 신호 수집
2. **정규화 + 융합**: 계층별 점수화 → 가중치 `W={otc:0.35, wastewater:0.40, search:0.25}` 로 composite score 산출
3. **게이트 판정**: `pipeline/scorer.py` `determine_alert_level()` — 2개 계층 이상 임계 초과 시에만 경보 승급 (§4)
4. **적재**: TimescaleDB hypertable에 시계열 저장
5. **추론**: `ml/serve.py`가 XGBoost 위험도 + TFT 7/14/21일 예측 + AE 이상탐지 제공
6. **노출**: `backend/`가 REST/SSE로 집계, `frontend/`가 실시간 대시보드 렌더

---

## 3. 컴포넌트 상세 (모듈별)

| 모듈 | 기술 | 포트 | 책임 | 소유 (팀) |
|---|---|---|---|---|
| `pipeline/` | Python, APScheduler, Kafka | — | 3계층 수집·정규화·융합·게이트·적재 | 이우형 (Data Eng) |
| `ml/` | XGBoost, PyTorch(TFT), FastAPI | 8002 | 모델 학습·체크포인트·추론 서빙 | 박진영 (ML Lead) |
| `backend/` | FastAPI, Pydantic Settings, SQLAlchemy | 8001 | API·인증·집계·SSE·LLM 리포트·챗봇 | 이경준 (Backend) |
| `frontend/` | Next.js 14, React, TS, Tailwind | 3000 | 실시간 대시보드 (Phase2) | 김나영 (Frontend) |
| `src/` | Streamlit | — | Phase1 프로토타입 대시보드 (레거시) | 김나영 |
| `analysis/` | statsmodels, scikit-learn | — | 백테스트·Granger·부트스트랩 CI·검증 | 박진영 |
| `infra/` | systemd, Docker Compose | — | 배포·서비스 유닛·운영 | 박정빈 (DevOps/QA) |
| `tests/` | pytest (552 tests) | — | 단위·통합·회귀 테스트 | 박정빈 |
| `docs/` | Markdown, docx | — | 문서·사업·발표 자료 | 박진영 |

### 서비스 구동 (systemd, 상시)

```
uis-docker.service     (oneshot)  → TimescaleDB + Qdrant + Kafka + kafka-ui 컨테이너 기동
uis-backend.service    (running)  → FastAPI :8001
uis-ml.service         (running)  → ML 추론 :8002
uis-scheduler.service  (running)  → APScheduler (수집·융합·야간 RAG)
uis-frontend.service   (running)  → Next.js :3000
```

관리 명령: `systemctl status uis-backend` / `journalctl -u uis-ml -f` / `systemctl restart uis-frontend`
상세는 [`docs/operations/systemd_services.md`](../operations/systemd_services.md).

---

## 4. 핵심 알고리즘 — 교차검증 게이트 (특허 청구 대상)

`pipeline/scorer.py` `determine_alert_level()` (L155-222):

- 계층별 점수가 임계(layer_threshold)를 넘는 계층 수를 카운트
- **임계 초과 계층 수 < 2 이면 강제로 GREEN** (단일 계층 단독 경보 차단)
- YELLOW 이상 경보는 **최소 2개 이종(異種) 비의료 신호가 동시에 임계 초과**해야 발효

이 "N≥2 이종 비의료 신호 동시 임계 초과" 강제 로직이 Google Flu Trends(검색 단독)·BioWatch(공기 단독)·BlueDot/HealthMap(뉴스 NLP)과의 차별점이며, **특허 핵심 청구항**이다. 확장 시 이 게이트 로직은 **절대 약화 금지**.

---

## 5. ML 모델 현황

| 모델 | 상태 | 용도 | 산출물 |
|---|---|---|---|
| XGBoost | **프로덕션** | 위험도 점수 (주모델) | `ml/checkpoints/xgb_best.joblib` |
| TFT | PoC (합성 입력) | 7/14/21일 예측 + attention 해석성 | `tft_real` / `tft_synth` |
| Autoencoder | 보조 | 이상탐지 (99분위 임계) | — |

> ⚠️ TFT는 현재 **합성 PoC 입력**(`_make_dataframe(seed=42)`)으로 동작 → 응답에 `mode: "synthetic_demo"`, `caveat`, `data_source` 메타데이터를 명시해 데모 안전성 확보(V11.3). 프로덕션 DB 시계열 연동은 Phase 2 과제.
> ⚠️ `ml/checkpoints/`는 git 커밋 금지 (대용량). 신규 환경은 학습 스크립트로 재생성.

---

## 6. API 요약

### Backend (FastAPI :8001) — prefix `/api/v1`

| 영역 | 메서드 · 경로 | 설명 |
|---|---|---|
| signals | `GET /signals/latest` `GET /signals/timeseries` `GET /signals/regions` | 3계층 신호 조회 |
| alerts | `GET /alerts/current` `GET /alerts/stream` (SSE) | 경보 현황 + 실시간 스트림 |
| predictions | `GET /predictions/anomaly` `GET /predictions/forecast` `GET /predictions/explain/{id}` `GET /predictions/report-pdf` | 예측·이상·리포트 |
| chat | `POST /chat/ask` | RAG 챗봇 (Qdrant 기반) |
| report | `POST /report/generate` | LLM(Claude Haiku) 리포트 생성 |

> 전체 Swagger: 터널 후 `http://localhost:8001/docs`. 상세 스펙은 [`docs/api-spec.md`](../api-spec.md).
> 알려진 minor 이슈: `/chat/ask` 요청 바디 필드명 불일치(`message` vs `question`, 422) — 확장 전 정리 권장.

### ML (FastAPI :8002)

`GET /health` · `GET /predict/risk` · `POST /predict/tft-7d` · `POST /predict/tft-14d` · `POST /predict/tft-21d`

---

## 7. 디렉토리 구조 (확장 시 어디에 코드를 둘지)

```
urban-immune-system/
├── backend/      FastAPI 앱 (app/api/, app/config.py=Pydantic Settings, app/middleware/)
├── ml/           모델 학습·체크포인트·serve.py (추론 API)
├── pipeline/     수집기·scorer.py(게이트)·Kafka 연동
├── frontend/     Next.js 14 대시보드 (src/app/page.tsx 단일 페이지 + 컴포넌트)
├── src/          Phase1 Streamlit (레거시, 유지보수만)
├── analysis/     백테스트·Granger·부트스트랩 CI 스크립트 + outputs/
├── infra/        systemd/ 유닛 파일, Docker 관련
├── tests/        pytest 552개 (모듈별 test_*.py)
├── docs/         문서 (architecture·api-spec·business·operations·onboarding)
├── docker-compose.yml   인프라 4종 (TimescaleDB·Qdrant·Kafka·kafka-ui)
└── pyproject.toml       의존성·ruff·mypy 설정
```

### 모듈별 진입 규칙 (팀 확장)

- 팀원은 **자기 담당 디렉토리에서 `claude` 세션**을 열면 해당 모듈 `CLAUDE.md`가 자동 로드돼 역할 특화 컨텍스트를 받는다.
- 신규 팀이 새 도메인을 붙일 때는 **새 최상위 모듈 디렉토리 + 해당 모듈 `CLAUDE.md`**를 만들고 README 소유권 표에 등록.
- 데이터 계층 추가(예: L4)는 `pipeline/`에 수집기 + scorer 가중치 갱신 + 게이트 카운트 로직 검토가 세트.

---

## 8. 확장 로드맵 & 협업 시 우선 조치

### 8.1 보안 (착수 1순위)
- [ ] GCP 방화벽: 5432/6333/9092/8080 인바운드를 사내 IP로 제한 (현재 `0.0.0.0` 노출)
- [ ] 대시보드 외부 노출은 IAP 또는 nginx+인증 경유 (loopback 바인딩 유지)
- [ ] `.env` 시크릿은 절대 커밋 금지 — Secret Manager 이관 검토

### 8.2 데이터/모델
- [ ] TFT 합성 입력 → 프로덕션 DB 시계열 연동 (Phase 2)
- [ ] L1·L3 전국 broadcast 한계 → HIRA OpenAPI 등으로 시·도별 신호 분리 (Phase 3)
- [ ] 단일 시즌(26주) 검증 → 추가 시즌 데이터로 일반화 검증

### 8.3 협업 규칙 (필수 준수)
- main 직접 push 금지 → `feature/*` → `develop` → `main` PR
- 커밋 전 `pytest tests/` 전체 통과 (Worker DoD), 커버리지 게이트 현재 **74%** (B2G 70% 기준 충족)
- 외부 LLM API는 테스트에서 반드시 Mock
- 게이트 B 로직(scorer.py L155-222) 약화 금지 (특허·안전 핵심)

---

## 9. 정직성 / 알려진 한계 (외부 검증 대비)

- **Recall 95% CI [0.834, 0.924]** — 하한이 KPI 0.85 미달 (점추정은 통과, borderline)
- **FAR 95% CI [0.176, 0.309]** — 상한이 KPI 0.30 초과 (borderline)
- L1·L3 전국 broadcast로 Granger 유효 검정군이 nominal 51 → effective 18
- TFT는 합성 입력 PoC 단계
- 단일 인플루엔자 시즌(26주) 기반 — 다년 일반화 미검증

> 위 한계는 발표 슬라이드·전문가 advisory 자료에 **명시 필수**. 숨기면 검증 결격.

---

## 10. 참고 문서

- 아키텍처 상세: [`docs/architecture.md`](../architecture.md)
- API 스펙: [`docs/api-spec.md`](../api-spec.md)
- 계층 명세: [`docs/layer_specs.md`](../layer_specs.md)
- 데이터 소스: [`docs/data-sources.md`](../data-sources.md)
- systemd 운영: [`docs/operations/systemd_services.md`](../operations/systemd_services.md)
- 게이트 B 지역 v2: [`docs/architecture/gate_b_regional_v2.md`](../architecture/gate_b_regional_v2.md)
- 교차검증 한계: [`docs/architecture/cv_limitations.md`](../architecture/cv_limitations.md)
- 사업/가격: [`docs/business/pricing-model.md`](../business/pricing-model.md)
- 특허 액션: [`docs/business/ip_action_guide.md`](../business/ip_action_guide.md)
</content>
