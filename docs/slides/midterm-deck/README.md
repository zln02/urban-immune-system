# Urban Immune System — 중간발표 Deck

2026-04-30 캡스톤 디자인 중간발표용 슬라이드.
Claude Design(claude.ai/design)에서 제작한 Notion 디자인 언어 기반 16 슬라이드 HTML 프레젠테이션.

## 파일 구성

```
midterm-deck/
├── index.html          # 본 파일(16 슬라이드 + 발표자 노트 16개)
├── deck-stage.js       # <deck-stage> 웹 컴포넌트 (슬라이드 전환/스케일/노트 동기화)
├── styles/
│   ├── deck.css        # 덱 전용 스타일 (한국어 Pretendard 우선)
│   └── notion-tokens.css  # Notion 디자인 토큰(색·타이포·여백)
└── README.md           # 본 파일
```

## 실행

```bash
# 1. 간단한 정적 서버
cd docs/slides/midterm-deck
python3 -m http.server 8080

# 2. 브라우저에서 접속
open http://localhost:8080
```

## 조작

- `→` / `Space` — 다음 슬라이드
- `←` — 이전 슬라이드
- `F` — 전체화면
- `N` — 발표자 노트 토글
- `0` — 표지로 복귀

## 슬라이드 17장 구성 (실제 섹션 순서)

| # | 제목 | 비고 |
| --- | --- | --- |
| 01 | 표지 | LG DX 대상 배지 + 팀 5명 |
| 02 | 문제 — 병원은 이미 늦다 | 기존 감시 체인 표 |
| 03 | 해법 — 3-Layer 조기 신호 | 약국·하수·검색 카드 3개 |
| 04 | 왜 3개를 교차하나 | 구글 독감 트렌드 실패 교훈 |
| 05 | 시스템 구조 | 수집 → DB → AI → 대시보드 |
| 06 | 캡스톤 8주의 결정사항 | KOWAS 픽셀 분석, Claude, walk-forward 등 |
| 07 | 검증 결과 | F1=0.667 · Precision=1.000 · AUC=0.931 |
| 08 | 코드 깊이 ① — 데이터 파이프라인 | KOWAS 차트 픽셀 분석 코드 |
| 09 | 현재 완성도 | 모듈별 진행 % 막대 |
| 10 | 대시보드 데모 | Next.js 17 시·도 |
| 11 | 실측 성능 | 레이어별 지표 + Granger 인과검정 |
| 12 | 코드 깊이 ② — ML 모델 | walk-forward + Autoencoder |
| 13 | 재현 명령어 | 4개 bash 명령으로 모든 숫자 재생성 |
| 14 | 경쟁 맵 | BlueDot · CDC NWSS · 우리 |
| 15 | 코드 깊이 ③ — AI 리포트 | RAG + SSE 스트리밍 |
| 16 | 로드맵 + 상용화 | Phase 1~5, 지자체/광역/WHO |
| 17 | 팀 + 남은 이슈 + Q&A | 팀원 5명 + 리스크 3개 |

## 디자인 원칙

- Notion 시각 언어: 따뜻한 흰색, 1px whisper 경계선, Notion Blue 포인트, 근흑 텍스트, 넉넉한 여백
- 한국어 우선 타이포그래피 (Pretendard + Inter fallback)
- 색맹 안전(CUD) 레이어 팔레트: 자홍(약국) / 청록(하수) / 파랑(검색)
- 비전공자 용어 풀이: Kafka → "실시간 데이터 우체통", Granger → "A가 B보다 먼저 움직이는지 통계 검증"
- 다크 모드 슬라이드 3장(표지·정정·최종 비전)으로 감정 피벗 구분

## 수정 가이드

- 모든 슬라이드는 `<section data-label="NN 제목">` 블록. 순서 변경은 DOM 순서 조작.
- 발표자 노트 16개는 `index.html` 상단 `<script type="application/json" id="speaker-notes">` 배열.
- 슬라이드 간 공통 클래스는 `styles/deck.css` 상단에 정의.
- 레이아웃 기준 해상도: 1920 × 1080 (`<deck-stage width="1920" height="1080">`). 표시 크기는 뷰포트에 자동 스케일.
