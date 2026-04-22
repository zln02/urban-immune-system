# backend/ 에이전트 — 이경준(Backend) 전용

## 🎯 정체성
FastAPI REST API 서버. 3-Layer 신호 조회, 위험도 앙상블, 경보 생성, ML 서비스 프록시를 제공한다. **B2G 납품의 얼굴**이라 보안·감사·성능(p95<500ms)을 가장 먼저 본다.

## 💬 말 거는 법 (이경준이 하는 예시 지시)
- "`/alerts/generate` 엔드포인트 실데이터 기준으로 완성해줘"
- "JWT 인증 미들웨어 붙이고 `/docs` 에 반영"
- "감사 로그 미들웨어: 요청자·timestamp·응답코드 기록"
- "rate limiting 붙여야 하는데 slowapi 로 갈까 nginx 로 갈까 비교"
- "API 명세서 OpenAPI 자동 생성본을 `docs/api-spec.md` 로 export"

## 🛠 Skills
- `/commit`, `/review-pr`, `/simplify`
- 커스텀(후속): `/backend-run` — uvicorn reload 기동 · `/backend-openapi` — OpenAPI 스펙 추출
- Agent 병렬: 엔드포인트별 테스트 작성은 Haiku 서브에이전트 병렬

## 🔌 MCP 연결
- **GitHub**: PR·이슈
- **Notion**(선택): API 변경 changelog 동기화

## 🌿 GitHub 연계
- 브랜치: `feature/backend-*`
- PR 체크리스트:
  - [ ] `pytest tests/test_backend_config.py` 통과
  - [ ] `ruff check backend/` + `mypy backend/` 0 error
  - [ ] SQL은 전부 파라미터 바인딩 확인(문자열 포맷 금지)
  - [ ] CORS `ALLOWED_ORIGINS` allowlist 유지
  - [ ] 새 엔드포인트는 OpenAPI 자동 문서화 확인
- CI Job: `backend-lint`, `backend-test`

## 🧠 자동 메모리
- 추가한 엔드포인트 경로·메서드·인증 방식
- 스키마 변경 마이그레이션 필요 여부
- 성능 이슈(쿼리 느림, 커넥션 풀 튜닝 등)
저장 제외: DB 비밀번호·JWT 시크릿.

## 📦 상용화 기여
- **B2G 산출물**: OpenAPI 명세서, JWT 인증 가이드, 감사 로그 샘플
- **ISMS-P**: 파라미터 바인딩·CORS·감사 추적 3대 보안 요건 담당
- **p95 < 500ms**: 납품 SLA

## ✅ Definition of Done
1. `pytest tests/` 통과
2. `ruff` + `mypy` 0 error
3. `uvicorn backend.app.main:app --port 8000` 기동 후 `/docs` 렌더 확인
4. 신규 엔드포인트는 감사 로그 미들웨어 타는지 확인
5. PR 본문에 보안 체크리스트 5개 체크

## 📍 핵심 파일
- `backend/app/main.py` — FastAPI 앱, CORS, 라우터 등록
- `backend/app/database.py` — Async SQLAlchemy 세션 팩토리
- `backend/app/config.py` — Pydantic Settings (보안 기본값 거부)
- `backend/app/api/signals.py` — 3-Layer 신호 조회
- `backend/app/api/alerts.py` — 앙상블·경보 생성
- `backend/app/api/predictions.py` — ML 서비스 프록시
- `backend/app/services/prediction_service.py` — ML 추론 HTTP 클라이언트

## 🚧 Phase 2 TODO
- [ ] `/alerts/generate` 실로직 (현재 placeholder)
- [ ] JWT 인증 + API Key 이중 지원
- [ ] 감사 로그 미들웨어 (`X-Requested-By` 헤더 기반)
- [ ] Rate limiting (slowapi 또는 nginx)
- [ ] OpenAPI 스펙 자동 `docs/api-spec.md` 반영
