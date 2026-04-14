# frontend/ 에이전트 — 김나영(Frontend, Phase2 Next.js) 전용

## 🎯 정체성
**B2G 프로덕션 UI**. Next.js 14 + Deck.gl 9 + Recharts + SWR + TypeScript + Tailwind. 실제 납품·유료 구독 고객이 볼 화면. 모바일 포함 반응형, 접근성(WCAG AA), 성능(LCP<2.5s) 목표.

## 💬 말 거는 법 (김나영이 하는 예시 지시)
- "RiskMap 컴포넌트에 백엔드 `/signals/latest` 연동"
- "AlertReport 카드에 근거 표시(RAG citation) 추가"
- "SWR 캐시 전략: 신호는 30s, 경보는 실시간 revalidate"
- "Mapbox 토큰을 `NEXT_PUBLIC_MAPBOX_TOKEN` 로 분리"
- "Vitals(LCP/FID/CLS) 측정 + 리포트"

## 🛠 Skills
- `/commit`, `/review-pr`, `/simplify`
- 커스텀(후속): `/frontend-dev` — `npm run dev` · `/frontend-build` — 프로덕션 빌드 검사

## 🔌 MCP 연결
- **GitHub**: PR
- **Notion**(선택): 디자인 스펙

## 🌿 GitHub 연계
- 브랜치: `feature/frontend-*`
- PR 체크리스트:
  - [ ] `npm run lint` / `npm run type-check` 통과
  - [ ] `npm run build` 성공
  - [ ] Deck.gl 지도 타일 유효한지(토큰 체크)
  - [ ] 접근성(axe 또는 Lighthouse) 심각도 경고 0
  - [ ] 모바일 뷰포트 스크린샷 첨부
- CI Job: `frontend-lint`

## 🧠 자동 메모리
- 완성한 컴포넌트·페이지 경로
- 성능 메트릭(LCP/FID/CLS)
- 타사 SDK 버전·이슈

## 📦 상용화 기여
- **B2G 산출물**: 프로덕션 UI, 사용자 매뉴얼(스크린샷), 접근성 보고서
- **가격 티어 분기**: 구독 tier(프로/엔터프라이즈) 기능 플래그

## ✅ Definition of Done
1. `npm run build` 성공
2. Lighthouse 성능 90+ / 접근성 90+
3. 백엔드 API 미연결 시 graceful empty state
4. `frontend/Dockerfile` 로 컨테이너 빌드 OK (infra 에이전트와 협업)
5. 모바일 + 데스크톱 스크린샷 `docs/images/` 커밋

## 📍 핵심 파일
- `frontend/package.json` — 의존성 (Next.js 14, Deck.gl 9, Recharts, SWR)
- `frontend/src/` — 소스 (TypeScript)
- `frontend/Dockerfile` — 프로덕션 이미지
- 예상 컴포넌트: `RiskMap`, `AlertReport`, `TrendChart`, `Dashboard`

## 🚧 Phase 2 TODO
- [ ] 백엔드 실데이터 API 연결 (SWR fetcher)
- [ ] Deck.gl 서울 25구 choropleth
- [ ] 실시간 경보 푸시(WebSocket 또는 SSE)
- [ ] 다국어(KO/EN) — B2G 시연 영문 대응
- [ ] 로그인 화면 (JWT — backend 에이전트와 협업)
