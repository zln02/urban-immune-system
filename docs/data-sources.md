# 데이터 소스 명세

## Layer 1 — 약국 OTC 구매 트렌드

| 항목 | 내용 |
|------|------|
| 출처 | 네이버 쇼핑인사이트 API |
| URL | `https://openapi.naver.com/v1/datalab/shopping/categories` |
| 인증 | Client ID / Client Secret (환경변수) |
| 갱신 | 주 1회 (월요일 09:00 KST) |
| 단위 | 상대 지수 (0~100 정규화) |
| 키워드 | 감기약, 해열제, 종합감기약 (OTC 카테고리) |
| 선행 시간 | ~1~2주 |
| 근거 | Li et al. (2025), NRDM (2025) |

> ⚠️ 쇼핑(구매 행동, L1)과 검색어(증상 탐색, L3)는 의도적으로 분리됨

## Layer 2 — 하수 바이오마커

| 항목 | 내용 |
|------|------|
| 출처 | KOWAS (환경부 국가하수감시체계) |
| URL | https://www.kowas.kr |
| 수집 방식 | 주간 PDF 보고서 수동 다운로드 → pdfplumber 파싱 |
| 자동화 목표 | Phase 3~4 (OCR + Selenium 크롤링) |
| 갱신 | 주 1회 (화요일 KOWAS 발행 후) |
| 단위 | copies/L (정규화 0~100) |
| 선행 시간 | ~2~3주 (가장 빠른 선행 신호) |
| 근거 | CDC NWSS, NAS (2023) |
| 현황 | 2024-25 시즌 26주치 수동 수집 완료 |

## Layer 3 — 검색어 트렌드

| 항목 | 내용 |
|------|------|
| 출처 | 네이버 데이터랩 API |
| URL | `https://openapi.naver.com/v1/datalab/search` |
| 인증 | Client ID / Client Secret (공유) |
| 갱신 | 주 1회 (월요일 09:05 KST) |
| 키워드 | 독감 증상, 인플루엔자, 고열 원인, 몸살 원인, 타미플루 |
| 선행 시간 | ~1~2주 |
| 주의사항 | 단독 사용 시 과대추정 위험 (GFT 교훈) → 반드시 교차검증 |
| 근거 | Ginsberg (Nature, 2009), ARGO (PNAS, 2015) |

## 보조 — 기상 데이터

| 항목 | 내용 |
|------|------|
| 출처 | 기상청 초단기실황 API |
| 갱신 | 매시간 |
| 피처 | 기온 (T1H), 습도 (REH) |
| 용도 | TFT 보조 입력 피처 (인과관계 없음) |

## Ground Truth — 인플루엔자 확진 통계

| 항목 | 내용 |
|------|------|
| 출처 | KDCA (질병관리청) 감염병 포털 |
| URL | https://www.kdca.go.kr |
| 갱신 | 주 1회 |
| 용도 | 모델 학습 레이블, 검증 Ground Truth |

## 검증 결과 요약

- **교차상관**: 하수 -2~-3주, OTC -1~-2주, 검색어 -1주 선행
- **Granger 인과검정**: p < 0.05 (L1·L3 유의, L2 약함 — `analysis/outputs/lead_time_summary.json` 참조)
- **3-Layer 17개 시·도 walk-forward 백테스트** (2025-2026 인플루엔자 시즌, n=1,020)
  - F1=0.84 · Precision=0.96 · Recall=0.77 · FAR=0.16
  - 평균 lead time 5.9주 (확진 peak 대비)
  - 출처: `analysis/outputs/backtest_17regions.json`
- **Train/Test Split**: walk-forward (TimeSeriesSplit, gap=4주)
