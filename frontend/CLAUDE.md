# frontend/ — D1 김나영 전용

## 담당자
역할 D1 — 김나영 (Frontend 개발 · API 연동)

## 기술 스택
- Next.js 14 App Router (`app/` 디렉터리)
- Deck.gl v9 (3D 히트맵)
- Recharts (시계열 차트)
- SWR (데이터 패칭)
- Tailwind CSS

## 환경변수 규칙
```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000   # 백엔드 FastAPI
NEXT_PUBLIC_MAPBOX_TOKEN=pk...               # Deck.gl 지도
```
- `NEXT_PUBLIC_` 접두사 없는 키는 클라이언트 번들에 포함되지 않음 — 주의
- 하드코딩 금지, 반드시 환경변수 참조

## API 연동 대상 엔드포인트
| 컴포넌트 | 엔드포인트 | 폴링 주기 |
|---------|-----------|---------|
| `RiskMap.tsx` | `GET /api/v1/signals/latest` | SWR revalidateOnFocus |
| `TrendChart.tsx` | `GET /api/v1/signals/timeseries` | 60초 |
| `AlertReport.tsx` | `GET /api/v1/alerts/current` | 60초 |

## 코드 규칙
1. **DUMMY_DATA 교체 시**: 타입 정의 먼저 (`types/` 또는 인라인 interface) → 실데이터 연결
2. **SWR refreshInterval**: 60000ms 고정 (변경 시 백엔드 부하 고려)
3. **에러 상태 필수**: API 실패 시 로딩 스피너 또는 에러 배너 표시
4. **타입 힌트**: TSX 컴포넌트 props 전부 interface 정의 필수
5. **`lib/api.ts`**: API 클라이언트 함수는 이 파일에서만 export — 컴포넌트 내 직접 fetch 금지
6. **반응형 디자인 필수**: 모바일 대응 (Tailwind `sm:` / `md:` 브레이크포인트 적용)
7. **실시간 알림 UI**: ORANGE/RED 경보 발령 시 배너 또는 팝업으로 즉시 표시

## 현재 DUMMY_DATA 위치
- `components/RiskMap.tsx` — DUMMY_DATA 상수 → `/api/v1/signals/latest` 연결 필요
- `components/TrendChart.tsx` — 이미 API 연동 (안정화 필요)
- `components/AlertReport.tsx` — 60초 폴링 구현됨

## 폴더 구조
```
frontend/
├── src/
│   └── app/
│       ├── page.tsx          # 메인 대시보드 (RiskMap+TrendChart+AlertReport)
│       ├── layout.tsx
│       ├── globals.css       # ← D2 박정빈 담당
│       ├── lib/
│       │   └── api.ts        # API 클라이언트 (D1 담당)
│       └── components/
│           ├── RiskMap.tsx   # Deck.gl 3D 히트맵 (D1 담당)
│           ├── TrendChart.tsx
│           └── AlertReport.tsx
```

## 주차별 개발 계획 (8주 로드맵)

| 주차 | 목표 |
|------|------|
| 1~2주 | Next.js 14 프로젝트 셋업 + Deck.gl 지도 프로토타입 |
| 3~4주 | 시계열 차트 구현 + FastAPI 엔드포인트 연동 |
| 5~6주 | 경보 UI (배너/팝업) + 반응형 디자인 적용 |
| 7~8주 | UX 테스트 + 프로덕션 배포 |

> **[경고 — 가이드.pdf]** Next.js 전환이 지연될 경우 **Streamlit 유지**로 즉시 전환.
> Next.js 전환 지연은 8주 전체를 날릴 수 있는 최대 위험 요소.
> 3주차 종료 시 Next.js 지도 미완성이면 Streamlit fallback으로 결정.

## 권장 스킬
- `/frontend-design` — 컴포넌트 신규 생성
- `/arrange` — 레이아웃·간격
- `/audit` — API 연동 후 접근성·성능 체크
- `/harden` — 에러 상태·오버플로우 처리
- `/adapt` — 반응형 디자인 (모바일 브레이크포인트)
