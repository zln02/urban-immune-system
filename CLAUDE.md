# Urban Immune System — AI 감염병 조기경보

## Commands
```bash
cd /home/wlsdud5035/urban-immune-system
source .venv/bin/activate
pip install -e ".[all]"
pip install -e ".[dev]"

# 실행
streamlit run src/app.py --server.port 8501

# 테스트
pytest

# 린트
ruff check src/ tests/
```

## Architecture
Streamlit 5탭 대시보드 (위험도 지도/시계열/상관관계/교차검증/AI리포트)

3-Layer 신호: 약국 OTC + 하수 바이오마커 + 검색 트렌드

현재 시뮬레이션 데이터, Phase 2에서 실제 API 연동 예정

Phase 2 구조: backend/(FastAPI) + pipeline/(Kafka) + ml/(TFT+RAG) + frontend/(Next.js)

docker compose up -d -> Kafka KRaft + TimescaleDB + Qdrant

## Key Paths
src/ — 메인 소스 (모듈화 완료)

src/tabs/ — 탭별 렌더링

src/map/ — Folium 지도

src/components/ — UI 컴포넌트

prototype/ — 레거시 단일파일 버전 (보존)

analysis/ — 데이터 분석 스크립트

## Code Rules
한국어 주석 유지

타입 힌트 public 함수 필수

import 순서: stdlib → third-party → local

## 팀 에이전트 시스템
팀원 5명은 각자 자기 모듈 디렉토리에서 `claude` 세션을 열어 역할 특화 에이전트와 대화한다.

| 팀원 | 진입 경로 | 에이전트 역할 |
|---|---|---|
| 박진영 | `cd ml && claude` 또는 `cd docs && claude` | ML Lead + PM + B2G 문서 |
| 이경준 | `cd backend && claude` | FastAPI·보안·감사로그 |
| 이우형 | `cd pipeline && claude` | Kafka·수집·정규화 |
| 김나영 | `cd frontend && claude` (Phase2) / `cd src && claude` (Phase1) | UI·지도·시각화 |
| 박정빈 | `cd infra && claude` 또는 `cd tests && claude` | K8s·CI·QA |

각 모듈 CLAUDE.md 가 Claude Code에 의해 최근접 우선으로 자동 로드된다.

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
