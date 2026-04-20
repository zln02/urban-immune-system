# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Urban Immune System — AI 감염병 조기경보

3-Layer 비의료 신호(약국 OTC + 하수 바이오마커 + 검색 트렌드)를 AI(TFT)로 교차검증하여 감염병을 1~3주 선행 감지하고, RAG-LLM으로 자동 경보 리포트를 생성하는 시스템.

## Commands

```bash
# 환경 설정
cd /home/wlsdud5035/urban-immune-system
source .venv/bin/activate
cp .env.example .env          # API 키 설정 (Naver, OpenAI, KMA 등)
pip install -e ".[all]"       # 전체 의존성 (backend+pipeline+ml+dev)

# Phase 1 — Streamlit 대시보드
streamlit run src/app.py --server.port 8501

# Phase 2 — 인프라 + Backend + Frontend
docker compose up -d          # Kafka KRaft(:9092) + TimescaleDB(:5432) + Qdrant(:6333) + Kafka UI(:8080)
uvicorn backend.app.main:app --reload --port 8000
cd frontend && npm install && npm run dev   # Next.js :3000

# 테스트
pytest                                # 전체
pytest tests/test_config.py           # 단일 파일
pytest -k "test_utils"                # 키워드 매칭
pytest --cov=src --cov=backend        # 커버리지 (B2G 목표: ≥70%)

# 린트
ruff check src/ tests/ backend/ pipeline/ ml/
ruff check --fix src/                 # 자동 수정

# Docker 정리
docker compose down -v                # 볼륨 포함 정리
```

## Architecture

**Phase 1 (현재 캡스톤 데모)**: `src/` Streamlit 5탭 대시보드. 시뮬레이션 데이터 fallback 지원.

**Phase 2 (상용화)**: 풀스택 분리 아키텍처
- `backend/` — FastAPI + SQLAlchemy async (p95 < 500ms)
- `pipeline/` — Kafka KRaft producer → TimescaleDB hypertable consumer (수집 성공률 ≥ 99%)
- `ml/` — PyTorch TFT 7/14/21일 예측 + Autoencoder 이상탐지 + RAG-LLM 리포트 (F1 ≥ 0.70)
- `frontend/` — Next.js 14 + Deck.gl 9 + Recharts (LCP < 2.5s)
- `infra/` — K8s(GKE asia-northeast3) + DB 스키마 + Prometheus/Grafana

데이터 흐름: 3-Layer 수집 → Kafka → TimescaleDB → Autoencoder 이상탐지 → TFT 예측 → RAG-LLM 리포트 → Dashboard

## Key Paths

- `src/` — Streamlit 대시보드 (`src/tabs/` 탭별, `src/map/` Folium 지도, `src/components/` UI)
- `backend/app/` — FastAPI 엔트리포인트 `main.py`
- `pipeline/` — Kafka producer/consumer, 3-Layer 수집기
- `ml/` — TFT 모델, Autoencoder, RAG 리포트 생성기
- `frontend/` — Next.js 14 앱
- `infra/db/init.sql` — TimescaleDB 초기화 스키마
- `prototype/` — 레거시 단일파일 (보존, 수정 금지)
- `analysis/` — 공모전 분석 스크립트 (아카이브)

## Code Rules

- 한국어 주석 유지
- 타입 힌트 public 함수 필수
- import 순서: stdlib → third-party → local
- Ruff line-length: 120

## Git Branching

`main` → `develop` → `feature/*` 브랜치. main/develop 직접 push 금지, 반드시 PR.

## CI (GitHub Actions — 6 Jobs)

backend-lint (ruff+mypy) / pipeline-lint (ruff) / ml-lint (ruff) / backend-test (pytest) / legacy-test (pytest src/) / frontend-lint (eslint+tsc)

## 팀 에이전트 시스템

팀원 5명은 각자 자기 모듈 디렉토리에서 `claude` 세션을 열어 역할 특화 에이전트와 대화한다.

| 팀원 | 진입 경로 | 에이전트 역할 |
|---|---|---|
| 박진영 | `cd ml && claude` 또는 `cd docs && claude` | ML Lead + PM + B2G 문서 |
| 이경준 | `cd backend && claude` | FastAPI·보안·감사로그 |
| 이우형 | `cd pipeline && claude` | Kafka·수집·정규화 |
| 김나영 | `cd frontend && claude` (Phase2) / `cd src && claude` (Phase1) | UI·지도·시각화 |
| 박정빈 | `cd infra && claude` 또는 `cd tests && claude` | K8s·CI·QA |

각 모듈 CLAUDE.md가 Claude Code에 의해 최근접 우선으로 자동 로드된다.

## B2G 납품 금지 규칙 (ISMS-P)

- SQL: 문자열 포맷 금지 → 반드시 파라미터 바인딩(`$1` / `:param` / SQLAlchemy bind)
- CORS: `*` 금지 → `ALLOWED_ORIGINS` 환경변수 allowlist만
- 기본 비밀번호 금지: `changeme*`, `password`, `1234`, `admin` 등
- API 키·토큰 로그 출력 시 `sk-*`, `Bearer *` 마스킹
- 모든 외부 API 호출은 try/except + 로깅 (네이버 429·KMA 타임아웃 대응)
- alert_reports 등 변경성 테이블은 `created_by`, `created_at` 감사 필드 필수

## 상용화 문서

- `docs/business/roadmap.md` — 캡스톤 발표 + Phase 4 이후 상용화 타임라인
- `docs/business/isms-p-checklist.md` — ISMS-P 인증 체크리스트
- `docs/business/sales-targets.md` — 타깃 고객 리스트
- `docs/business/pricing-model.md` — 구독/건당/PoC 3-tier 가격 초안
- `docs/business/procurement.md` — 조달청·나라장터 절차

기능 변경 시 위 문서에 영향 있는지 1줄 이상 검토 후 PR에 기록.
