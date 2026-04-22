# Urban Immune System — Frontend (상용화 B2G 대시보드)

> **Next.js 15 + React 19 + Tailwind 4 + TanStack Query v5 + shadcn/ui**
> 2026-04-22 ~ · 실제 공공기관·지자체 납품용 상용 제품

---

## 🎯 정체성

- 질병관리청·지자체 감시센터 공무원이 실제로 쓰는 화면
- **WCAG 2.2 AA + KWCAG 2.2** 준수 (공공 조달 필수)
- 모바일 반응형 + 다크 모드 + 한국어·영어
- SSE 기반 실시간 경보 푸시

---

## 🗂 위치 관계

| 디렉토리 | 역할 |
|---|---|
| `prototype/` | 2026-03 공모전 수상작 Streamlit (참조 · 수정 금지) |
| `src/` | 캡스톤 중간발표 전용 Streamlit Phase 1 (4/30 이후 내부 데모 격하) |
| **`frontend/` (여기)** | **상용화 B2G 납품 프로덕트 본체** |

---

## 🚀 실행

```bash
cd frontend
npm install          # Next.js 15 · React 19 · 신규 의존성 전부
npm run dev          # http://localhost:3000 (Turbopack)
npm run build        # 프로덕션 빌드
npm run type-check   # TypeScript 엄격 검사
npm run lint         # ESLint
```

### 환경변수 (`.env.local`)

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_MAP_STYLE_URL=https://demotiles.maplibre.org/style.json
```

---

## 🏛 디렉토리 구조

```
frontend/src/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout + Providers 주입
│   ├── page.tsx                  # 랜딩 페이지
│   ├── providers.tsx             # TanStack Query + next-themes
│   └── globals.css               # Tailwind 4 + design tokens import
│
├── components/
│   ├── ui/                       # shadcn/ui (자동 생성)
│   ├── map/                      # MapLibre + Deck.gl choropleth
│   ├── charts/                   # ECharts 시계열·히트맵
│   ├── alert/                    # 경보 카드·뱃지·모달
│   └── layout/                   # Header·Sidebar·Footer
│
├── hooks/
│   └── useAlertStream.ts         # SSE 실시간 경보 구독
│
├── lib/
│   ├── api/client.ts             # Zod 파싱 fetch 래퍼 + ApiError
│   └── utils/cn.ts               # Tailwind classnames 머저
│
├── stores/
│   └── alertStore.ts             # Zustand UI 필터 상태
│
├── types/
│   └── alert.ts                  # DistrictRisk · AlertEvent · SignalPoint
│
└── styles/
    └── tokens.css                # Okabe-Ito CUD + Navy + KRDS 토큰
```

---

## 🎨 디자인 시스템

- **색상**: Okabe-Ito CUD (색맹 안전) — `--risk-{safe,caution,warning,alert}`
- **3중 중복 코딩**: 색상 + 아이콘 (✅🔔⚠️🚨) + 텍스트
- **폰트**: Pretendard GOV (KRDS 공식)
- **모티프**: shadcn/ui + Radix UI (WCAG AA 자동)

---

## 📡 Backend API 연동

| 엔드포인트 | 역할 | Query key |
|---|---|---|
| `GET /api/v1/signals/latest` | 25구 최신 위험도 | `['signals', 'latest']` |
| `GET /api/v1/alerts/stream` | **SSE 실시간 경보** | `useAlertStream()` |
| `GET /api/v1/alerts/current` | 현재 경보 목록 | `['alerts', 'current']` |
| `POST /api/v1/reports/generate` | AI 리포트 생성 | Mutation |

---

## 🛣 로드맵

### Phase 2-1 (5월) — 핵심 기능
- [ ] shadcn/ui init + 컴포넌트 10종 생성
- [ ] MapLibre 기반 서울 25구 choropleth
- [ ] ECharts 시계열 (3-Layer 통합)
- [ ] SSE 경보 스트림 + motion 애니메이션

### Phase 2-2 (6월) — 운영 준비
- [ ] 다크 모드 + i18n (KO/EN)
- [ ] axe-core 접근성 CI 추가
- [ ] Lighthouse CI (성능 ≥85, 접근성 ≥95)

### Phase 3+ (여름) — B2G 납품
- [ ] JWT 로그인 (backend 협업)
- [ ] 감사 로그 뷰어
- [ ] PDF 리포트 내보내기
- [ ] GKE 배포 + Cloudflare

---

## 🚫 금지 사항

- `any` 타입 사용 (Zod 스키마로 런타임 검증)
- Tailwind 외 CSS-in-JS (emotion, styled-components)
- 색상을 클래스명에만 의존 (색맹 + 아이콘 + 텍스트 3중 필수)
- Mapbox (유료 벤더 종속) — MapLibre 만 사용
- SWR (TanStack Query 로 통일)
