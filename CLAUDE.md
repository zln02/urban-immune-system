# urban-immune-system — 팀 프로젝트

AI 기반 감염병 조기경보 시스템. 3계층 비의료 신호(약국 OTC·하수도 바이오마커·검색 트렌드) 교차검증으로 임상 확진 1–3주 선행 탐지.

## 팀 구성 & 역할

| 이름 | 역할 | 담당 모듈 |
|------|------|----------|
| 박진영 (PM) | 역할 B+C — 데이터 파이프라인 + ML/AI 엔진, 총괄 | `pipeline/`, `ml/` |
| 이경준 | 역할 B — 데이터 파이프라인 (수집·스케줄러) | `pipeline/` |
| 이우형 | 역할 A — Backend + API (FastAPI·DB) | `backend/`, `infra/` |
| 김나영 | 역할 D1 — Frontend 개발 (코딩) | `frontend/src/`, `src/` (API 연동) |
| 박정빈 | 역할 D2 — UX 디자인 + 발표 준비 | `src/styles.py`, `src/map/`, `src/components/`, `frontend/src/app/globals.css`, 발표자료 |

### 역할 요약 (가이드 문서 기준)
- **역할 A** ★★★☆☆ — FastAPI 엔드포인트, PostgreSQL 연동, JWT 인증
- **역할 B** ★★★★★ — 네이버 API 수집, KOWAS PDF 크롤러, APScheduler
- **역할 C** ★★★★☆ — LSTM/XGBoost 모델, walk-forward 검증, RAG 리포트
- **역할 D1** ★★★☆☆ — Next.js/Streamlit API 연동, 실데이터 연결, 에러 핸들링
- **역할 D2** ★★☆☆☆ — Streamlit CSS 테마, Folium 지도 디자인, 발표 슬라이드

## 절대 규칙
- **main 브랜치 직접 푸시 금지** — feature/* → develop → main PR 필수
- 팀원 담당 모듈 수정 시 반드시 확인 후 진행 (위 역할표 참조)
- API 키 절대 커밋 금지 (.gitignore 확인 필수)

## 아키텍처 참조
@docs/architecture.md

## 브랜치 전략
- `main` : 배포 가능한 안정 버전
- `develop` : 개발 통합 브랜치
- `feature/*` : 기능 개발 (develop에서 분기)
- `hotfix/*` : 긴급 수정 (main에서 분기 → main + develop 머지)

---

## 빠른 시작

```bash
cd /home/wlsdud5035/urban-immune-system
source .venv/bin/activate
pip install -e ".[all]"

# 로컬 인프라 (Kafka + TimescaleDB + Qdrant)
docker compose up -d

# Streamlit 대시보드
streamlit run src/app.py --server.port 8501

# FastAPI 백엔드
uvicorn backend.app.main:app --reload --port 8000

# 테스트 (커밋 전 필수)
pytest

# 린트
ruff check src/ tests/ backend/ pipeline/ ml/
mypy src/ backend/
```

---

## 프로젝트 구조

```
urban-immune-system/
├── src/                    # Streamlit MVP (Phase 1)
│   ├── app.py              # 진입점 — 5탭 대시보드
│   ├── config.py           # 색상·지역·위험 레벨 상수
│   ├── tabs/               # 탭별 렌더러
│   ├── map/                # Folium 지도
│   └── components/         # 헤더·사이드바·카드
├── backend/                # FastAPI REST API
│   └── app/
│       ├── main.py         # CORS·라우터 등록
│       ├── config.py       # Pydantic Settings (환경변수 검증)
│       ├── database.py     # SQLAlchemy async 엔진
│       ├── api/            # signals / predictions / alerts 라우터
│       ├── models/         # ORM: LayerSignal · RiskScore · AlertReport
│       └── services/       # ML 서비스 HTTP 클라이언트
├── pipeline/               # 데이터 수집·스트리밍
│   └── collectors/
│       ├── otc_collector.py       # L1: 네이버 쇼핑인사이트
│       ├── wastewater.py          # L2: KOWAS PDF 파싱
│       ├── search_collector.py    # L3: 네이버 DataLab
│       ├── weather_collector.py   # AUX: 기상청 API
│       ├── kafka_producer.py      # Kafka 직렬화·전송
│       ├── normalization.py       # Min-Max 정규화 (0-100)
│       └── scheduler.py           # APScheduler 크론
├── ml/                     # 추론·학습
│   ├── tft/model.py        # TFT 7/14/21일 예측
│   ├── anomaly/autoencoder.py  # 이상탐지 (재구성 오차)
│   ├── rag/                # Qdrant + LLM 리포트
│   └── serve.py            # FastAPI 추론 엔드포인트
├── frontend/               # Next.js + Deck.gl (Phase 2)
├── infra/
│   ├── k8s/                # K8s 매니페스트
│   └── db/init.sql         # TimescaleDB 하이퍼테이블
├── tests/                  # pytest 22개 테스트
├── pyproject.toml
├── docker-compose.yml
└── .env.example
```

---

## 3계층 데이터 처리 로직

### 아키텍처 원칙

```
[수집] → [Kafka 토픽] → [정규화(0-100)] → [TimescaleDB] → [앙상블] → [경보]
  L1           L2             L3
 약국         하수도          검색
1-2주 선행   2-3주 선행    1-2주 선행
```

> **핵심 규칙**: 어떤 단일 계층도 단독 경보 발령 금지. 반드시 2개 이상 계층 교차검증 필요.
> Google Flu Trends 과대예측 실패 교훈 — L3 단독 사용 절대 금지.

---

### Layer 1: 약국 OTC (Pharmacy)

**소스**: 네이버 쇼핑인사이트 API
**Kafka 토픽**: `uis.layer1.otc`
**수집 주기**: 매주 월요일 09:00
**색상**: `#be185d` (마젠타)

```python
# pipeline/collectors/otc_collector.py

# 모니터링 키워드 — 임의 추가 금지, config.py에서 관리
OTC_KEYWORDS = ["감기약", "해열제", "종합감기약", "타이레놀", "판콜"]

# API 타임아웃 15초 고정 — 변경 시 scheduler.py 재검토 필요
TIMEOUT_SEC = 15

# 반환 타입 명시 필수
async def collect_otc_weekly() -> dict[str, float]:
    """네이버 쇼핑인사이트에서 주간 OTC 구매 트렌드 수집.

    Returns:
        region → 정규화 지수 (0-100)
    Raises:
        CollectorError: API 인증 실패 또는 타임아웃
    """
```

**처리 규칙**:
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` 환경변수 필수 (하드코딩 금지)
- 응답이 비어 있으면 이전 주 값 유지 (NaN 전파 금지)
- 수집 후 즉시 `normalization.min_max_normalize()` 적용

---

### Layer 2: 하수도 바이오마커 (Wastewater)

**소스**: KOWAS (한국 하수도감시 시스템) PDF
**Kafka 토픽**: `uis.layer2.wastewater`
**수집 주기**: 매주 화요일 10:00
**색상**: `#047857` (청록)

```python
# pipeline/collectors/wastewater.py

# PDF 파싱 — pdfplumber 사용
# [CRITICAL] Phase 1 (1~2주): Selenium/Playwright 자동 다운로드 프로토타입 구현 필수
# Fallback: 자동화 실패 시 수동 다운로드 → pipeline/data/kowas/ 저장

def parse_kowas_pdf(pdf_path: str) -> list[WastewaterReading]:
    """KOWAS PDF에서 인플루엔자 바이러스 농도 추출.

    Args:
        pdf_path: pipeline/data/kowas/ 하위 PDF 절대경로
    Returns:
        WastewaterReading 리스트 (region, copies_per_ml, date)
    Raises:
        PDFParseError: 파싱 실패 또는 예상 테이블 구조 불일치
    """
```

**처리 규칙**:
- 단위: copies/mL → Min-Max 정규화 (전체 레코드 기준)
- PDF 구조 변경 감지 시 즉시 `PDFParseError` 발생 (silent fail 금지)
- PDF 저장 경로: `pipeline/data/kowas/`
- **[CRITICAL]** Selenium/Playwright 자동 크롤링 파이프라인 구현 (B 역할 최우선)

---

### Layer 3: 검색 트렌드 (Search/SNS)

**소스**: 네이버 DataLab API (쇼핑인사이트와 다른 엔드포인트)
**Kafka 토픽**: `uis.layer3.search`
**수집 주기**: 매주 월요일 09:05
**색상**: `#1d4ed8` (파랑)

```python
# pipeline/collectors/search_collector.py

# L3 전용 키워드 — L1 키워드와 의도적으로 분리 (구매 vs 증상탐색)
SEARCH_KEYWORDS = ["독감 증상", "인플루엔자", "고열 원인", "몸살 원인", "타미플루"]

# DataLab API — 쇼핑인사이트와 다른 엔드포인트/인증
DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
```

**처리 규칙**:
- L1 OTC 키워드와 혼용 금지 (구매행동 ≠ 증상탐색)
- L3 단독 경보 발령 절대 금지 — 반드시 L1 또는 L2와 교차검증
- 트렌드 지수 급등(>80/100) 단독 감지 시 `YELLOW` 이하로만 설정 가능

---

### Auxiliary: 기상 데이터

**소스**: 기상청 초단기 예측 API (KMA)
**Kafka 토픽**: `uis.aux.weather`
**수집 주기**: 매시간

**처리 규칙**:
- 기온: -20°C ~ 40°C → 0-100 정규화
- 기상 데이터는 TFT 입력 피처 전용 — 경보 점수 직접 기여 금지
- 인과관계 아닌 상관관계: "저온·저습 → 독감 상관" (인과 주장 금지)

---

### 정규화 (Normalization)

```python
# pipeline/collectors/normalization.py

def min_max_normalize(values: list[float]) -> list[float]:
    """모든 계층 신호를 0-100으로 스케일링.

    Args:
        values: 원시 신호값 리스트
    Returns:
        0-100 정규화값 (빈 리스트 또는 상수 입력 처리 포함)
    """
```

**규칙**:
- 빈 리스트 입력 → `[]` 반환 (예외 발생 금지)
- 상수값(모두 동일) 입력 → `[50.0] * n` 반환 (ZeroDivision 방지)
- 계층 간 정규화 독립 적용 (L1·L2·L3 각각 별도 min/max)

---

### 앙상블 경보 로직

```
composite_score = w1 * l1_score + w2 * l2_score + w3 * l3_score

기본 가중치: w1=0.35, w2=0.40, w3=0.25
(L2 하수도 최고 가중치 — 가장 빠른 선행지표)

경보 레벨:
  GREEN  : composite < 30
  YELLOW : 30 ≤ composite < 55
  ORANGE : 55 ≤ composite < 75  (미래 확장)
  RED    : composite ≥ 75
```

**규칙**:
- 가중치는 `backend/app/config.py` 에서만 관리 (하드코딩 금지)
- `YELLOW` 이상 경보는 반드시 2개 이상 계층이 30 이상이어야 발령
- DB 모델 `alert_level` 컬럼: `'GREEN' | 'YELLOW' | 'RED'` 외 값 저장 금지

---

### Kafka 토픽 규칙

| 토픽 | 계층 | 보존 |
|------|------|------|
| `uis.layer1.otc` | L1 약국 | 168시간 |
| `uis.layer2.wastewater` | L2 하수도 | 168시간 |
| `uis.layer3.search` | L3 검색 | 168시간 |
| `uis.aux.weather` | 기상 | 168시간 |

```python
# kafka_producer.py 사용 규칙
# acks="all", retries=3 고정 — 변경 금지 (데이터 손실 방지)
# 직렬화: JSON UTF-8 (바이너리 직렬화 도입 시 버전 헤더 추가)
```

---

## 보안 컨벤션

### 환경변수 원칙

```python
# ✅ 올바름 — pydantic Settings로 로드
from backend.app.config import settings
db_url = settings.database_url

# ❌ 금지 — 하드코딩
DB_PASSWORD = "mypassword123"

# ❌ 금지 — os.getenv 직접 사용 (검증 우회)
import os
key = os.getenv("OPENAI_API_KEY")  # Settings를 통해 접근할 것
```

**필수 환경변수** (`.env.example` 기준):
```bash
DB_PASSWORD=             # TimescaleDB 비밀번호
NAVER_CLIENT_ID=         # 네이버 쇼핑인사이트 + DataLab 공용
NAVER_CLIENT_SECRET=
OPENAI_API_KEY=          # GPT-4o (RAG 리포트)
ANTHROPIC_API_KEY=       # Claude (대체 LLM)
KMA_API_KEY=             # 기상청 초단기예보
NEXT_PUBLIC_MAPBOX_TOKEN= # 프론트엔드 지도
ENVIRONMENT=development  # development | production
```

### 프로덕션 환경 강제 검증

`backend/app/config.py` Pydantic validator — **절대 제거 금지**:

```python
@model_validator(mode="after")
def validate_environment_settings(self) -> Settings:
    is_production = self.environment.lower() == "production"
    if is_production and "changeme" in self.database_url:
        raise ValueError("database_url must not use placeholder credentials in production")
    if is_production and self.ml_service_url.startswith("http://"):
        raise ValueError("ml_service_url must use https in production")
    return self
```

### API 키 보안 규칙

1. **`.env` 파일은 `.gitignore`에 포함** — `git add .env` 즉시 중단 후 히스토리 정리
2. **API 키 로그 출력 금지** — `logger.debug(f"key={key}")` 형태 포함
3. **테스트 코드에도 실제 키 금지** — `pytest-mock` 또는 `monkeypatch` 사용
4. **K8s 프로덕션**: `uis-secrets` Secret에서만 주입 (환경변수 직접 명시 금지)

### CORS 설정

```python
# backend/app/main.py
# allow_origins: 반드시 환경변수 CSV로 관리
# 개발: "http://localhost:3000,http://localhost:8501"
# 프로덕션: 도메인 명시적 지정 (와일드카드 * 금지)
CORSMiddleware(
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],   # PUT/DELETE 추가 시 리뷰 필요
    allow_credentials=False,          # 쿠키 인증 미구현 — True 변경 금지
)
```

### K8s 보안 컨텍스트

모든 Deployment에 반드시 포함 — **제거 금지**:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

### 민감 파일 — 커밋 금지

```
.env
*.pem
*.key
pipeline/data/kowas/*.pdf    # 공공 데이터지만 용량 이슈
ml/checkpoints/              # 모델 체크포인트 (용량)
```

### SQL / ORM 규칙

```python
# ✅ 올바름 — SQLAlchemy ORM 파라미터 바인딩
result = await db.execute(
    select(LayerSignal).where(LayerSignal.region == region)
)

# ❌ 금지 — f-string SQL (인젝션 위험)
query = f"SELECT * FROM layer_signals WHERE region = '{region}'"
```

---

## 코드 규칙

### 공통

- **언어**: 주석·docstring 한국어, 코드 영어 식별자
- **타입 힌트**: public 함수 전체 필수 (`mypy --strict` 통과)
- **import 순서**: stdlib → third-party → local (ruff isort 자동 정렬)
- **로깅**: `logging.getLogger(__name__)` — `print()` 금지
- **외부 API**: 반드시 `try/except` 감싸기 (bare `except:` 금지, 구체적 예외 명시)

### 계층별 파일 위치 규칙

| 작업 | 위치 |
|------|------|
| 수집 로직 변경 | `pipeline/collectors/` |
| 정규화 변경 | `pipeline/collectors/normalization.py` |
| DB 스키마 변경 | `infra/db/init.sql` + ORM 모델 동시 수정 |
| API 엔드포인트 | `backend/app/api/` |
| 경보 가중치 변경 | `backend/app/config.py` |
| ML 하이퍼파라미터 | `ml/configs/model_config.yaml` |
| 상수·색상 | `src/config.py` (Streamlit) / `backend/app/config.py` (API) |

### 새 수집기 추가 시 체크리스트

- [ ] `pipeline/collectors/<name>_collector.py` 생성
- [ ] Kafka 토픽 `uis.<layer>.<name>` 추가 (docker-compose.yml 업데이트)
- [ ] `normalization.min_max_normalize()` 호출 확인
- [ ] `scheduler.py`에 크론 잡 등록
- [ ] `tests/test_<name>_collector.py` 작성
- [ ] `.env.example`에 필요한 환경변수 추가

---

## 테스트 규칙

```bash
pytest                              # 전체
pytest tests/test_normalization.py  # 단일 파일
pytest -k "normalize"               # 키워드 필터
pytest -v --tb=short                # 기본 옵션 (pyproject.toml)
```

### 테스트 파일별 역할

| 파일 | 대상 |
|------|------|
| `test_normalization.py` | `min_max_normalize` 엣지케이스 (빈 리스트, 상수, 스케일링) |
| `test_backend_config.py` | Pydantic Settings 검증 (CSV 파싱, 프로덕션 자격증명) |
| `test_k8s_security.py` | K8s 매니페스트 보안 컨텍스트 (runAsNonRoot 등) |
| `test_config.py` | Streamlit 앱 설정 로딩 |
| `test_utils.py` | 유틸리티 함수 |
| `test_container_layout.py` | Streamlit 컴포넌트 레이아웃 |
| `test_report_generator.py` | RAG-LLM 리포트 생성 (Mock LLM 사용) |

### 테스트 작성 규칙

```python
# ✅ 외부 API는 반드시 Mock
from unittest.mock import AsyncMock, patch

@patch("pipeline.collectors.otc_collector.httpx.AsyncClient")
async def test_collect_otc_mocked(mock_client: AsyncMock) -> None:
    ...

# ✅ 실제 API 키 사용 금지
def test_config_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
    ...
```

---

## 커밋 전 자동화 (pre-commit)

```bash
# pre-commit 초기 설정 (최초 1회)
pip install pre-commit
pre-commit install   # .git/hooks/pre-commit 설치

# 수동 전체 실행
pre-commit run --all-files
```

**커밋 시 자동 실행 순서**:
1. `ruff check --fix` — 린트 + 자동 수정
2. `ruff format` — 코드 포맷
3. `detect-private-key` — API 키 하드코딩 차단
4. `trailing-whitespace` / `end-of-file-fixer` — 공백 정리
5. `pytest` — **테스트 실패 시 커밋 중단**

> **테스트 실패 = 커밋 불가**. `--no-verify` 우회는 긴급 핫픽스 외 금지.

---

## 데이터베이스

### TimescaleDB 하이퍼테이블

```sql
-- layer_signals: 모든 계층 원시 신호
-- 파티셔닝: time (weekly)
-- 인덱스: (time, layer), (layer, region, time DESC)
layer VARCHAR(10)        -- 'L1' | 'L2' | 'L3' | 'AUX' 외 값 삽입 금지
value DOUBLE PRECISION   -- 반드시 0-100 사이 (정규화 후 삽입)
```

### 마이그레이션 규칙

- 스키마 변경: `infra/db/init.sql` + SQLAlchemy ORM 동시 수정
- `NOT NULL` 컬럼 추가: 기본값 필수 또는 배포 순서 관리
- 하이퍼테이블 파티션 변경: 데이터 손실 위험 — 반드시 확인 후 진행

---

## ML 모델

### TFT (Temporal Fusion Transformer)

```yaml
# ml/configs/model_config.yaml 에서만 변경
hidden_size: 64
attention_heads: 4
dropout: 0.1
encoder_length: 24   # 주 단위
prediction_lengths: [7, 14, 21]
```

### 이상탐지 Autoencoder

- 임계값: 재구성 오차 95th percentile (훈련 후 결정)
- 임계값 하드코딩 금지 → `ml/configs/model_config.yaml` 관리

### RAG 리포트

- LLM 선택: 환경변수 `LLM_PROVIDER=openai|anthropic`
- 프롬프트 변경 시 `test_report_generator.py` 함께 업데이트
- Qdrant 컬렉션명: `epidemiology_docs` — 임의 변경 금지

---

## Phase 로드맵

| Phase | 상태 | 주요 내용 |
|-------|------|-----------|
| 1 | ✅ MVP | Streamlit 대시보드, 시뮬레이션 데이터 |
| 2 | 🔧 진행중 | FastAPI 백엔드, 실제 API 연동, Kafka 파이프라인, **KOWAS 자동 크롤링** |
| 3 | 📋 예정 | TFT 추론 완성 (데이터 증강 포함), Kafka Consumer |
| 4 | 📋 예정 | Next.js 프론트엔드 (지연 시 Streamlit 유지), K8s 프로덕션 배포 |

---

## 캡스톤 성공 기준 (회의자료 9.1 기준)

> 심사 기준 — 4가지 모두 충족 목표

| 구분 | 기준 |
|------|------|
| 기술 완성도 | 3계층(L1/L2/L3) 실데이터 자동 수집 + TFT 예측 + 웹 대시보드 통합 작동 |
| 검증 결과 | **F1-Score 0.80 이상** + **FAR 0.20 미만** 유지 (현 baseline: F1=0.84 / FAR=0.16) |
| 서비스성 | Next.js 대시보드(또는 Streamlit)에서 실시간 신호 조회 + AI 경보 리포트 생성 |
| 확장성 | 최소 1개 추가 질병 또는 지역 확장 시연 |

---

## 리스크 파일 (수정 주의)

| 파일 | 이유 |
|------|------|
| `backend/app/config.py` | 프로덕션 보안 검증 로직 포함 |
| `infra/db/init.sql` | 하이퍼테이블 구조 — 재생성 시 데이터 손실 |
| `infra/k8s/*-deployment.yaml` | 보안 컨텍스트 — 제거 시 취약점 |
| `pipeline/collectors/normalization.py` | 계층 간 비교 기준 — 변경 시 전체 재보정 필요 |
| `ml/configs/model_config.yaml` | TFT 체크포인트와 버전 일치 필수 |

---

## Claude Code 스킬 활용 가이드

역할별 권장 스킬 (Claude Code에서 `/스킬명`으로 실행):

### D1 김나영 (Frontend 코딩)

| 스킬 | 사용 시점 |
|------|----------|
| `/frontend-design` | Next.js 컴포넌트·페이지 새로 만들 때 |
| `/arrange` | 대시보드 레이아웃·간격 정리 |
| `/audit` | API 연동 후 접근성·성능 체크 |
| `/harden` | 에러 상태·오버플로우 처리 추가 |

### D2 박정빈 (UX 디자인·발표)

| 스킬 | 사용 시점 |
|------|----------|
| `/colorize` | Streamlit 대시보드 색상 추가 |
| `/animate` | 맥박 애니메이션·호버 효과 |
| `/polish` | 발표 전 최종 UI 마무리 |
| `/critique` | UX 리뷰·피드백 |
| `/distill` | 복잡해진 UI 단순화 |

### A 이우형 (Backend)

| 스킬 | 사용 시점 |
|------|----------|
| `/harden` | FastAPI 에러 핸들링·엣지 케이스 |

### B 이경준·박진영 (Pipeline)

| 스킬 | 사용 시점 |
|------|----------|
| `/simplify` | 수집기 코드 리뷰 후 품질 개선 |
