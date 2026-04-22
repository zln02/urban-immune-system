# frontend/ 에이전트 — 상용화 B2G 프로덕션 UI

## 🎯 정체성

**실제 공공기관·지자체 납품 대시보드**. Next.js 15 + React 19 + Tailwind 4 + TanStack Query v5 + shadcn/ui + MapLibre + Deck.gl + ECharts + Zustand + motion.

캡스톤 중간발표(4/30) 이후 주력 트랙. Streamlit `src/` 는 내부 데모 격하, 이 디렉토리가 유료 구독 고객이 보는 화면.

---

## 🗂 위치 관계

- `prototype/` = 공모전 수상작 Streamlit (수정 금지, 디자인 참조)
- `src/` = 캡스톤 Streamlit Phase 1 (4/30 이후 내부 데모)
- `frontend/` = **상용화 B2G 프로덕트 본체** (여기)

---

## 💬 말 거는 법

- "shadcn/ui init + Button·Card·Dialog·Badge·Tabs 5종 생성"
- "SSE `useAlertStream` 훅 호출 → 경보 오면 motion.layoutId 로 배너 슬라이드"
- "MapLibre 서울 25구 choropleth + Deck.gl GeoJsonLayer"
- "ECharts 로 3-Layer 시계열 통합 차트 (라인·히트맵 토글)"
- "`/api/v1/signals/latest` TanStack Query + Zod 파싱"

---

## 🛠 Skills

- `/commit`, `/review-pr`, `/simplify`
- `/frontend-dev` — `npm run dev` (Turbopack)
- `/frontend-build` — 프로덕션 빌드 + Lighthouse

---

## 🔌 MCP 연결

- **GitHub**: PR
- **Figma**: 디자인 컨텍스트 (`get_design_context`, `get_screenshot`)
- **Canva**: 마케팅 자료

---

## 🌿 GitHub 연계

- 브랜치: `feature/frontend-*`
- PR 체크리스트:
  - [ ] `npm run type-check` 통과
  - [ ] `npm run build` 성공 (Turbopack)
  - [ ] Lighthouse 접근성 ≥ 95 · 성능 ≥ 85
  - [ ] axe-core serious 이상 0건
  - [ ] 모바일 375px 스크린샷 첨부
  - [ ] Zod 스키마로 API 응답 검증
- CI Job: `frontend-lint`

---

## 📦 상용화 요구사항 (B2G)

### 필수 준수
- **WCAG 2.2 AA + KWCAG 2.2** (공공 조달 통과 요건)
- **Okabe-Ito CUD 색맹 안전 팔레트** — `--risk-{safe,caution,warning,alert}`
- **3중 중복 코딩** — 색상 + 아이콘(✅🔔⚠️🚨) + 텍스트
- **Pretendard GOV** (KRDS 공식 권장 폰트)
- **ISMS-P** — 클라이언트에 민감 데이터 저장 금지, 토큰 HttpOnly Cookie

### 성능 목표
- LCP < 2.5s (Lighthouse)
- INP < 200ms
- CLS < 0.1
- 번들 크기 초기 < 250KB gzip

---

## 🚫 금지 사항

- `any` 타입 — Zod 스키마로 런타임 검증 필수
- Tailwind 외 CSS-in-JS (emotion, styled-components)
- **Mapbox GL JS** (유료 MAU 과금) — MapLibre GL 4 만 사용
- **SWR** — TanStack Query 로 통일
- Recharts — ECharts 5 로 통일 (시계열 성능)
- 색상을 클래스명에만 의존 (색맹 사용자 구분 불가)
- 클라이언트에 `NEXT_PUBLIC_` 아닌 시크릿 노출

---

## ✅ Definition of Done

1. `npm run build` 성공 (Turbopack)
2. Lighthouse 접근성 ≥ 95 · 성능 ≥ 85 · SEO ≥ 90
3. axe-core serious 이상 0건
4. 백엔드 미연결 시 skeleton / empty state 렌더
5. 모바일(375px) + 태블릿(768px) + 데스크톱(1440px) 뷰포트 스크린샷
6. SSE 경보 테스트: 새 경보 생성 → 클라 3초 내 반영

---

## 📍 핵심 파일

- `src/app/layout.tsx` — Root layout + Providers
- `src/app/providers.tsx` — TanStack Query + next-themes
- `src/app/globals.css` — Tailwind 4 theme + tokens import
- `src/styles/tokens.css` — 디자인 토큰 (Okabe-Ito + Navy)
- `src/components/ui/` — shadcn 컴포넌트 (자동 생성 영역)
- `src/components/map/` — MapLibre + Deck.gl 25구 choropleth
- `src/components/charts/` — ECharts 시계열
- `src/components/alert/` — 경보 뱃지·카드·모달
- `src/hooks/useAlertStream.ts` — SSE 구독
- `src/lib/api/client.ts` — Zod 파싱 fetch 래퍼
- `src/stores/alertStore.ts` — Zustand UI 상태
- `src/types/alert.ts` — 도메인 Zod 스키마

---

## 🚧 Phase 별 TODO

### Phase 2-1 (5월, 핵심 기능)
- [ ] `npx shadcn@latest init` + 컴포넌트 10종
- [ ] MapLibre 서울 25구 choropleth (Deck.gl GeoJsonLayer)
- [ ] ECharts 3-Layer 시계열 (`echarts-for-react`)
- [ ] SSE `/alerts/stream` + motion 배너 애니메이션
- [ ] 경보 리포트 shadcn Dialog + PDF 다운로드

### Phase 2-2 (6월, 운영 준비)
- [ ] next-themes 다크 모드
- [ ] next-intl KO/EN
- [ ] axe-core CI 추가
- [ ] Lighthouse CI (PR 코멘트)

### Phase 3+ (여름, B2G 납품)
- [ ] JWT 로그인 (backend 협업)
- [ ] 감사 로그 뷰어
- [ ] PDF 리포트 내보내기 (`@react-pdf/renderer`)
- [ ] PWA (오프라인 캐시)
- [ ] GKE 배포 + Cloudflare CDN

---

## 🧠 자동 메모리

- 완성한 컴포넌트·페이지 경로
- 성능 메트릭 히스토리 (LCP/INP/CLS)
- 타사 SDK 버전·이슈 (MapLibre·Deck.gl·ECharts)
- 접근성 감사 결과 (axe-core · Lighthouse)
