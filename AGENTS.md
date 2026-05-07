# AGENTS.md — 팀 역할 & AI 에이전트 가이드

> 이 파일은 Cursor / Codex / Claude Code 모두가 자동 인식합니다.
> 절대 규칙·브랜치 전략은 [CLAUDE.md](CLAUDE.md) 참조.

---

## 팀 구성

| 이름 | 역할 | 담당 모듈 |
|------|------|----------|
| 박진영 (PM·PL) | PM / ML Lead — 전체 아키텍처·총괄 | `ml/`, `docs/`, `docs/business/` (전 모듈 풀 권한) |
| 이경준 | Backend (FastAPI·DB·라우터 17개) | `backend/` |
| 이우형 | Data Engineer (수집·스케줄러·KOWAS) | `pipeline/` |
| 김나영 | Frontend (Next.js Phase2·Streamlit Phase1) | `frontend/`, `src/` |
| 박정빈 | DevOps / QA (CI·k8s·systemd·테스트) | `infra/`, `.github/`, `tests/` |

## 박진영 PL 권한

박진영은 PL 권한으로 **모든 모듈에 사전 합의 없이 수정·푸시·머지 가능**.
(글로벌 메모리 `team_pl_authority.md` 참조)

> **단, main 브랜치 직접 푸시 금지는 PL 권한과 무관하게 절대 유지.**

---

## Claude Code 스킬 활용 가이드

> 아래 스킬은 **Claude Code 전용** (`/<스킬명>`). Cursor·Codex에서는 인식되지 않음.

### 김나영 (Frontend)

| 스킬 | 사용 시점 |
|------|----------|
| `/frontend-design` | Next.js 컴포넌트·페이지 새로 만들 때 |
| `/arrange` | 대시보드 레이아웃·간격 정리 |
| `/audit` | API 연동 후 접근성·성능 체크 |
| `/harden` | 에러 상태·오버플로우 처리 추가 |

### 박정빈 (UX 디자인·발표)

| 스킬 | 사용 시점 |
|------|----------|
| `/colorize` | Streamlit 대시보드 색상 추가 |
| `/animate` | 맥박 애니메이션·호버 효과 |
| `/polish` | 발표 전 최종 UI 마무리 |
| `/critique` | UX 리뷰·피드백 |
| `/distill` | 복잡해진 UI 단순화 |

### 이우형 (Backend)

| 스킬 | 사용 시점 |
|------|----------|
| `/harden` | FastAPI 에러 핸들링·엣지 케이스 |

### 이경준·박진영 (Pipeline)

| 스킬 | 사용 시점 |
|------|----------|
| `/simplify` | 수집기 코드 리뷰 후 품질 개선 |
