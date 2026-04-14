# tests/ 에이전트 — 박정빈(QA) + 전원 공통

## 🎯 정체성
품질 게이트. pytest 기반 단위·통합·벤치마크·스모크 테스트. **B2G 납품 커버리지 ≥ 70%** 목표.

## 💬 말 거는 법 (박정빈·팀원 공용 예시)
- "`tests/test_alerts_api.py` 새로 작성 — 앙상블 점수 계산 검증"
- "benchmark_xgboost 스타일로 TFT 추론 10ms 체크 벤치 만들어줘"
- "E2E 테스트: 수집 → Kafka → TSDB → API → 대시보드"
- "pytest-cov 커버리지 리포트 HTML 생성"
- "pre-commit hook 에 pytest 붙여"

## 🛠 Skills
- `/commit`, `/review-pr`
- 커스텀(후속): `/test-cov` — pytest-cov HTML 리포트 · `/test-e2e` — 통합 시나리오

## 🔌 MCP 연결
- **GitHub**: PR·CI 결과

## 🌿 GitHub 연계
- 브랜치: `feature/tests-*`
- PR 체크리스트:
  - [ ] 새 코드 → 테스트 최소 1개
  - [ ] 외부 I/O는 mock, 내부 로직은 실제 실행
  - [ ] 파일명: `test_{모듈}.py`, 벤치: `benchmark_{대상}.py`, 통합: `test_integration_{흐름}.py`
  - [ ] `pytest tests/` 통과
- CI Job: `backend-test`, `legacy-test`

## 🧠 자동 메모리
- 추가한 테스트 파일·커버리지 변화
- 플레이키 테스트 목록
- 느린 테스트 상위 5개

## 📦 상용화 기여
- **B2G 산출물**: 성능 테스트 보고서(p95, 동시접속), 테스트 커버리지 리포트
- **ISMS-P**: 테스트 로그 보존 1년

## ✅ Definition of Done
1. `pytest tests/` 전부 통과
2. `pytest --cov` 리포트 70% 이상
3. 신규 테스트는 CI 에서 실행됨
4. flaky 테스트 0개

## 📍 핵심 파일 (현재)
- `tests/test_backend_config.py` — 백엔드 설정 검증
- `tests/test_normalization.py` — 정규화 로직
- `tests/test_report_generator.py` — RAG 보고서
- `tests/test_config.py` — Pydantic Settings
- `tests/test_k8s_security.py` — K8s 매니페스트 보안
- `tests/test_container_layout.py` — Streamlit 레이아웃
- `tests/test_utils.py` — 공용 유틸
- `tests/test_claude_md_presence.py` (신규) — 에이전트 CLAUDE.md 존재·구조 검증

## 🚧 Phase 2 TODO
- [ ] E2E 통합 테스트 (수집→DB→API→대시보드)
- [ ] 부하 테스트 (locust 또는 k6)
- [ ] pytest-cov 기준선 고정
- [ ] 플레이키 감지 · 자동 재시도
