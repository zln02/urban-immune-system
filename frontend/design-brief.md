# Urban Immune System — Claude Design Brief

> 📋 **사용법**: claude.ai/design 열고 GitHub `zln02/urban-immune-system` 연결 → 아래 프롬프트 전체 복사해서 붙여넣기.
> Claude Design 이 frontend/ 코드베이스와 `tokens.css` · `CLAUDE.md` 를 자동 추출해서 일관성 있게 디자인 시스템 생성.

---

## 🎨 Claude Design 에 붙여넣을 프롬프트

```
# Urban Immune System — B2G 공공 감염병 조기경보 대시보드

## 프로젝트 정체
- 실제 질병관리청(KDCA)·지자체 감시센터 공무원이 매일 쓰는 모니터링 시스템
- 목표 고객: 1순위 질병관리청 감염병감시지원단, 2순위 서울시 감염병관리지원단, 3순위 WHO 협력센터
- 현재 단계: Streamlit 내부 데모 존재. Next.js 15 기반 상용화 버전을 당신이 디자인해주세요.
- 발표 일정: 2026-04-30 캡스톤 중간발표, 2027 B2G 납품 목표

## 핵심 기능 (3-Layer 교차검증)
1. 💊 약국 OTC 구매 트렌드 (L1 · ~2주 선행) — 네이버 쇼핑인사이트
2. 🚰 하수 바이오마커 (L2 · ~3주 선행) — 환경부 KOWAS
3. 🔍 검색 트렌드 (L3 · ~1주 선행) — 네이버 데이터랩
→ 3개가 동시에 상승하면 경보 발령 (단일 신호 노이즈 필터)

## 필수 페이지 5개
1. **랜딩 페이지** (`/`) — 서비스 소개 + 로그인 유도
2. **대시보드 홈** (`/dashboard`) — 서울 25구 choropleth 지도 + 실시간 경보 배너 + 3-Layer 시계열 + AI 리포트 카드
3. **구별 상세** (`/district/[code]`) — 해당 구 7·14·21일 예측 (95% CI) + Granger 인과검정 + 경보 이력
4. **AI 리포트** (`/reports/[id]`) — RAG 기반 경보 분석 리포트 + PDF 다운로드 + "AI 생성·인간 검토 필요" 워터마크
5. **설정** (`/settings`) — 임계값·알림·언어(KO/EN)·다크 모드

## 기술 스택 (고정)
- Next.js 15 (App Router, Turbopack, use cache)
- React 19 (Compiler)
- Tailwind CSS 4 (CSS-first, @theme directive)
- shadcn/ui + Radix UI 6종 (Dialog, Popover, Tabs, Toast, Tooltip, Slot)
- TanStack Query v5 (SSE invalidation)
- Zustand 5 (UI 필터 상태)
- MapLibre GL JS 4 + Deck.gl 9 (25구 choropleth)
- Apache ECharts 5 (시계열·히트맵·캘린더)
- motion v12 (ex-Framer, 40% 번들 감소)
- next-themes · next-intl · Zod

## 디자인 토큰 (엄격 준수)

### 색상 — Okabe-Ito CUD (색맹 안전 팔레트)
위험도 4단계, 각각 아이콘 + 텍스트 3중 중복 코딩 필수:
- `--risk-safe`: #009E73 (Bluish Green) · Level 1 · ✅ 안전
- `--risk-caution`: #E69F00 (Orange-Yellow) · Level 2 · 🔔 주의
- `--risk-warning`: #D55E00 (Vermillion) · Level 3 · ⚠️ 경계
- `--risk-alert`: #CC0000 (Pure Red) · Level 4 · 🚨 경보

3-Layer 브랜드 색상:
- `--layer-pharmacy`: #be185d (약국 OTC)
- `--layer-sewage`: #047857 (하수)
- `--layer-search`: #1d4ed8 (검색)

세만틱 베이스:
- primary: hsl(215 54% 24%) — Navy (공공기관 기본)
- background: hsl(0 0% 100%) / dark: hsl(215 28% 10%)
- radius: 0.75rem (lg) / 0.625rem (md) / 0.5rem (sm)

### 타이포그래피
- 본문·UI: Pretendard GOV (KRDS 공식 권장 가변 폰트)
- 숫자·데이터: 동일 Pretendard (tabular-nums 활성)
- 코드: JetBrains Mono

### 레이아웃
- 헤더 높이 64px (4rem)
- 사이드바 폭 280px (1.75rem 접힘 가능)
- 대시보드 grid: 12 column, gap 24px
- 카드 padding 20-24px

## 디자인 참조 (있으면 이 분위기로)
- IBM Carbon Design System (공공기관 + 데이터 밀도) — 자세한 명세는 `frontend/.design-refs/ibm-carbon.md` 332줄 참조
- KRDS 범정부 UI/UX 디자인 시스템 (한국 정부 공식) — 아래 "한국 공공 디자인 규정" 섹션 준수
- Vercel (검정·흰색 정밀함, Geist 타이포)
- CDC Data Tracker (공공보건 공식 톤)
- ClickHouse Analytics (기술적 문서·노란 액센트 대안)
- Linear (모달·키보드·접근성)

## 한국 공공 디자인 규정 (KRDS 2024 · 행정안전부 · 디지털플랫폼정부위원회)

> 공공기관·공기업 납품 시 **의무 준수**. 위반 시 조달 심사 감점. 공식: https://www.krds.go.kr

### 색상 체계 — 13단계 Gray + 11단계 컬러
- **Primary · Secondary · Gray** 3분류
- Gray: 0(흰색) · 100(검정) 포함 **13단계** 스케일 (0, 10, 20, 30, 40, 50, 60, 70, 80, 85, 90, 95, 100)
- Primary/Secondary/System: **11단계** 명도 스케일 (5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95)
- **대비 매직 넘버** (명도 레벨 선택 시 기준):
  - `40` = 3:1 (UI 요소 경계선 최소)
  - `50` = 4.5:1 (본문·아이콘 WCAG AA 최소)
  - `70` = 7:1 (본문 WCAG AAA)
  - `90` = 15:1 (최고 대비)
- **System Colors 4종**:
  - Danger (빨강) · Warning (노랑) · Success (초록) · Information (파랑)
- **우리 적용**:
  - Primary = Navy `#1F2D5B` (공공기관 기본)
  - Gray 스케일 = IBM Carbon 의 Gray 10·20·30·50·70·90·100 차용 (동일 13단계 호환)
  - System = 위 Okabe-Ito 위험도 팔레트가 대체 (색맹 안전 + KRDS System 4종 매핑)

### 타이포그래피 — Pretendard GOV (공공 전용)
- **공식 폰트**: Pretendard GOV (가변 폰트) — 대한민국 중앙부처 홈페이지 표준
- Latin 자형이 공공 가독성 목적으로 수정됨 (일반 Pretendard 와 다름)
- **다운로드**: https://github.com/orioncactus/pretendard (GOV 버전 릴리스 포함)
- 본 프로젝트 `globals.css` 에 이미 CDN 임포트 등록됨
- 타이틀·숫자·UI 전부 Pretendard GOV 로 통일 (한국어+영어)

### 접근성 — WCAG 2.2 AA + KWCAG 2.2
- 본문 색상 대비 **4.5:1 이상** (strict)
- 대형 텍스트(18px+) **3:1 이상**
- UI 컴포넌트·아이콘 **3:1 이상**
- 키보드만으로 전체 기능 접근 가능
- focus-visible 2px outline 필수
- 각 페이지 `<h1>` 1개, 건너뛰기 링크 제공
- 한국어 `lang="ko"` 루트 지정

### 레이아웃 · 간격
- 기본 단위 **8px grid** (IBM Carbon 동일) — 모든 여백·패딩·크기가 8의 배수
- 브레이크포인트: 576 / 768 / 992 / 1200 / 1400
- 최대 콘텐츠 폭 1200px (B2G 대시보드는 1440px 허용)

### 모션·애니메이션
- duration 150ms (micro) · 250ms (standard) · 400ms (entrance)
- easing: `cubic-bezier(0.2, 0, 0.38, 0.9)` (IBM productive)
- `prefers-reduced-motion` 존중 (멀미 유발 금지)

## 한국 공공 요구사항 (필수)
- WCAG 2.2 AA + KWCAG 2.2 준수 (공공 조달 탈락 방지)
- 색상 대비 4.5:1 이상 (전역)
- 색맹 시뮬레이션 (Deuteranopia·Protanopia)에서 4단계 전부 구분 가능
- 모든 상호작용 키보드 접근 가능
- 한국어 기본, 영어 토글 (WHO 시연용)
- 모바일 375px ~ 데스크톱 1440px+ 반응형

## 필수 컴포넌트 (생성해주세요)
1. `<AlertBanner>` — 상단 고정 실시간 경보 배너, motion.layoutId 로 새 경보 슬라이드 인
2. `<RiskMap>` — 서울 25구 choropleth, 호버 시 툴팁, 클릭 시 구별 상세 이동
3. `<TrendChart>` — 3-Layer 시계열, Train/Test 분할선 표시, 줌·팬 가능
4. `<AlertCard>` — 위험도 색상 + 아이콘 + 구명 + 타임스탬프, 클릭 시 모달
5. `<AIReport>` — RAG 리포트 카드, 신뢰구간 표시, PDF 다운로드 버튼, "AI 생성" 워터마크
6. `<LayerLegend>` — 3-Layer 범례, 4단계 위험도 설명, 색맹 안전 팔레트 가이드
7. `<ThresholdSlider>` — 임계값 백분위 조정 (50-95%)
8. `<DistrictSelector>` — 서울 25구 선택 dropdown, autocomplete
9. `<ExportButton>` — PDF · CSV · PNG 다중 export, 감사 로그 기록
10. `<AuditLog>` — 사용자 액션 추적 (ISMS-P 감사 요구사항)

## 우선순위
1. 먼저 **대시보드 홈** 화면 (페이지 2번) 라이브 HTML 생성
2. 디자인 시스템이 frontend/src/styles/tokens.css 와 일관되는지 확인
3. 완료되면 Handoff to Claude Code 로 번들 생성

## 금기 사항
- Mapbox GL JS (유료 벤더, 우리는 MapLibre 만)
- 색상을 class 명에만 의존 (색맹 구분 불가)
- 팀원 이름·학교 로고 (캡스톤 아닌 상용 서비스)
- "LG전자 공모전" 크레딧 큰 배너 (하단 footer 에 한 줄만)
- emoji 만으로 상태 표시 (텍스트 병기 필수)

## 출력
handoff 번들에 포함되어야 하는 것:
- 각 컴포넌트 별 shadcn 규격 .tsx 파일
- Tailwind 4 @theme 블록 확장판
- motion 애니메이션 variants 프리셋
- ECharts option 객체 (시계열 · 히트맵)
- MapLibre style JSON + Deck.gl layer 설정
- 접근성 체크리스트 (aria-*, 키보드 매핑)
```

---

## 📚 추가 레퍼런스 (Claude Design 에 업로드 권장)

Claude Design 은 채팅창에 파일 업로드 가능. 더 정교한 결과 원하면 아래 3개 첨부:

1. **`frontend/.design-refs/ibm-carbon.md`** (332줄) — IBM Carbon 상세 명세 (색상 토큰·타이포·컴포넌트 패턴 전부)
2. **`frontend/src/styles/tokens.css`** — 우리 현재 Okabe-Ito + KRDS 매핑
3. **`frontend/CLAUDE.md`** — 금기 사항·상용 요구사항

awesome-design-md 전체 69개는 **노이즈**. IBM Carbon 1개만으로 충분 — 기본 스켈레톤 제공 + KRDS·Okabe-Ito 로 한국 공공 맞춤.

---

## 🎯 Claude Design 사용 순서

1. claude.ai → 상단 메뉴 **Design** 탭 (또는 직접 https://claude.ai/design)
2. **GitHub 연결** — 우측 상단 설정 → Integrations → GitHub → `zln02/urban-immune-system` 선택
3. 위 프롬프트 **전체 복사 후 붙여넣기**
4. 추가 레퍼런스 파일 3개 업로드 (ibm-carbon.md · tokens.css · CLAUDE.md)
4. 대기 30-60초 → 라이브 HTML 페이지 생성됨
5. 인라인 코멘트·음성으로 수정 (예: "경보 배너 더 두껍게", "지도 배경 다크")
6. 만족하면 상단 **Handoff to Claude Code** 버튼
7. 번들 코드·스펙 복사
8. 이 CLI 로 돌아와서 "디자인 핸드오프 받았어 [붙여넣기]" 요청
   → 내가 `frontend/src/components/` 에 shadcn 규격으로 통합 + 커밋
