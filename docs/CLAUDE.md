# docs/ 에이전트 — 박진영 + 전원 공통

## 🎯 정체성
B2G 납품에 필요한 **기술 문서 7종**과 발표 자료의 소유자. 문서 품질이 곧 납품 가능성.

## 💬 말 거는 법
- "시스템 아키텍처 설계서 v1 초안 작성 (mermaid 다이어그램 포함)"
- "API 명세서는 FastAPI `/openapi.json` 에서 자동 뽑아서 넣어줘"
- "ERD 생성 (TimescaleDB 3 hypertable)"
- "ISMS-P 체크리스트 기반 보안 점검 보고서 초안"
- "발표용 데모 시나리오 스크립트 쓰기"

## 🛠 Skills
- `/commit`, `/review-pr`
- 커스텀(후속): `/docs-sync` — 코드 → 문서 자동 갱신 · `/docs-pdf` — Markdown → PDF (pandoc)

## 🔌 MCP 연결
- **GitHub**: PR
- **Notion**(선택): 로드맵 동기화

## 🌿 GitHub 연계
- 브랜치: `docs/*` 또는 `feature/docs-*`
- PR 체크리스트:
  - [ ] Markdown lint (`markdownlint` 또는 육안)
  - [ ] 다이어그램은 Mermaid 문법
  - [ ] 이미지는 `docs/images/` 하위
  - [ ] 버전 헤더: `v{버전} | {YYYY-MM-DD} | {작성자}`

## 🧠 자동 메모리
- 완성된 산출물 리스트·버전
- 리뷰 피드백 반영 이력
- 참조 원천(URL·보고서)

## 📦 상용화 기여 (B2G 필수 7종)
1. **시스템 아키텍처 설계서** — 3계층 구조도, 데이터 흐름도
2. **API 명세서** — OpenAPI 3.0 자동
3. **데이터베이스 설계서** — ERD + 하이퍼테이블
4. **보안 점검 보고서** — ISMS-P 체크리스트
5. **성능 테스트 보고서** — p95, 동시접속
6. **운영 매뉴얼** — 배포·장애 대응
7. **사용자 매뉴얼** — 대시보드 사용법

## ✅ Definition of Done
1. 7종 산출물 초안 존재 (Phase 4 시점)
2. 각 문서 v1 이상 + 최신화 날짜
3. 다이어그램·표·코드 예시 포함
4. PDF export 가능 (pandoc)

## 📍 핵심 파일
- `docs/architecture.md` — 기존
- `docs/api-spec.md` — 기존 (자동화 대상)
- `docs/data-sources.md` — 기존
- `docs/images/` — 스크린샷·다이어그램 이미지
- `docs/meeting-notes/` — 회의록
- `docs/slides/` — 발표 자료
- `docs/business/` — **상용화 전용 서브모듈** (별도 CLAUDE.md 있음)

## 🚧 Phase 2 TODO
- [ ] B2G 산출물 7종 중 미존재 4종 초안
- [ ] OpenAPI 자동 → `docs/api-spec.md` 파이프라인
- [ ] Mermaid ERD → PNG export
- [ ] 발표용 30초 데모 스크립트
