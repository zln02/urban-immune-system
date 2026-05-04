# frontend/ — 김나영

## 담당자
김나영 (Frontend) · 박진영 PL 권한으로 직접 수정 가능

## 기술 스택 (실측 2026-05-02)
- **Next.js 14.2.3** App Router (`src/app/`) — Phase 4 에서 15.2 마이그레이션 검토
- React 18.3.1 / TypeScript 5.4.5
- @tanstack/react-query 5.x (서버 데이터 캐시)
- SWR 2.x (일부 컴포넌트 잔존)
- Recharts 2.x (시계열)
- @deck.gl 9.x (히트맵 — 옵셔널)
- 네이버 Maps Web Dynamic API (옵셔널, key 있을 때만)
- Tailwind CSS 3.4

## 환경변수 (`.env.local`)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001     # 클라이언트→백엔드 (브라우저 노출)
UIS_API_INTERNAL_URL=http://127.0.0.1:8001         # SSR/Route Handler 내부 호출 (서버 전용)
NEXT_PUBLIC_NAVER_MAPS_KEY_ID=...                  # 있으면 네이버 지도, 없으면 SVG fallback
NEXT_PUBLIC_NAVER_MAPS_CLIENT_ID=...               # 호환용 alias
```
- 백엔드 포트는 **8001** (루트 CLAUDE.md `uvicorn ... --port 8001` 와 일치)
- `NEXT_PUBLIC_*` 만 클라이언트 번들 포함, 나머지는 서버 전용

## 실제 폴더 구조
```
frontend/
├── package.json
├── next.config.mjs
└── src/
    ├── app/
    │   ├── page.tsx                 # 랜딩
    │   ├── dashboard/page.tsx       # 17지역 대시보드 (메인)
    │   ├── api/v1/[...path]/route.ts  # 백엔드 프록시 (UIS_API_INTERNAL_URL 사용)
    │   ├── layout.tsx
    │   └── globals.css
    ├── components/
    │   ├── map/
    │   │   ├── korea-map.tsx        # SVG fallback
    │   │   └── korea-map-naver.tsx  # 네이버 지도 (key 있을 때)
    │   ├── charts/
    │   │   └── trend-chart.tsx
    │   ├── alert/
    │   │   ├── ai-report-card.tsx   # SSE 스트림 RAG 리포트
    │   │   ├── alert-banner.tsx
    │   │   └── kpi-card.tsx
    │   ├── anomaly/
    │   ├── chat/                    # /api/v1/chat SSE
    │   └── ui/                      # panel, risk-pill, icons
    ├── hooks/
    │   ├── useSignalTimeseries.ts   # @tanstack/react-query 기반
    │   └── ...
    └── lib/
        └── api.ts                   # API_BASE 단일 출처
```

## API 연동 패턴
| 컴포넌트 | 엔드포인트 | 패턴 |
|---|---|---|
| `dashboard/page.tsx` | `/api/v1/signals/*` | react-query + 60초 staleTime |
| `ai-report-card.tsx` | `/api/v1/alerts/stream` | EventSource (SSE) |
| `chat/*` | `/api/v1/chat/*` | EventSource (SSE) |
| `trend-chart.tsx` | `/api/v1/signals/timeseries` | `useSignalTimeseries` hook |

> 컴포넌트 내 `fetch` 직접 호출 금지 — `lib/api.ts` 또는 `hooks/use*` 경유.

## 코드 규칙
1. 새 데이터 fetch → `hooks/use*.ts` 신설 (react-query `useQuery`/`useMutation`)
2. SSE → 클라이언트 컴포넌트 (`"use client"`) + `EventSource`, cleanup 필수
3. 환경변수는 반드시 `process.env.NEXT_PUBLIC_*` 또는 서버에서 `process.env.UIS_API_INTERNAL_URL`
4. props 타입 inline interface, any 금지 (`tsc --noEmit` CI 게이트)
5. 모바일 대응 Tailwind `sm:`/`md:` 브레이크포인트
6. RED/ORANGE 경보는 `alert-banner` 또는 `ai-report-card` 즉시 표시

## 빌드 / 테스트
```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
npm run type-check   # tsc --noEmit (CI에서 frontend-lint 잡)
npm run build        # 프로덕션 빌드
```

## Phase 로드맵
- Phase 2 ✅ — Next.js 14.2.3 대시보드 + SSE/RAG + 17지역 + react-query 완료
- Phase 3 🔧 — 네이버 지도 prod 키 안정화, 챗봇 RAG 확장, PWA 모바일 푸시
- Phase 4 📋 — Next.js 15.2 마이그레이션 (React 19 + Turbopack + async cookies/headers 브레이킹 대응)

## 권장 스킬
- `/frontend-design` 컴포넌트 신규
- `/arrange` 레이아웃·간격
- `/audit` 접근성·성능
- `/harden` 에러·오버플로우
- `/adapt` 모바일 브레이크포인트
