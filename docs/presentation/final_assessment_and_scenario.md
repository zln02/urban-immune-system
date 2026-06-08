# UIS 최종 시스템 평가 + 캡스톤 발표 시나리오

> 작성: 2026-06-03 · 발표 D-5~10 (6/8~6/13)
> 작성자: 박진영 (PM/ML Lead) + Claude Opus 4.7

---

## 1. 현재 시스템 수준 객관 평가

### 1.1 모듈별 완성도 (10점 만점)

| 모듈 | 점수 | 근거 |
|------|-----|------|
| **데이터 수집 (pipeline)** | 8.5 | L1·L2·L3 다질병 53주, KOWAS 67 PDF, 17지역 broadcast. 자동 알람 가동. **미흡**: KOWAS Selenium 자동화는 Phase 3 |
| **저장 (Kafka+TimescaleDB)** | 9.0 | KRaft Kafka, 하이퍼테이블 layer_signals, asyncpg pool. 1년치 누적 안정 |
| **ML 모델** | **7.5** | 인플루엔자 KDCA peak F1=0.882 ✅ / 노로 transition ML 우위 입증 +13%p. **proxy 한계 정직 노출**. KDCA confirmed 미연동이 ceiling |
| **백엔드 API (FastAPI)** | 8.5 | 17개 라우터, SSE 스트림, Pydantic Settings, K8s SecurityContext, ISMS-P 미들웨어 |
| **프론트엔드 (Next.js)** | 8.0 | 17개 시도 지도, 3축 검증 매트릭스, RAG 리포트, pathogen 셀렉터, β 라벨. **미흡**: HTTPS 미적용 |
| **운영 (nginx+systemd)** | 7.0 | 외부 IP 노출(:80), Basic Auth, 이중 알람(ntfy+GitHub Issue). **미흡**: HTTPS·IP 제한 |
| **테스트·CI** | 8.0 | 단위 113 + 통합 19, ruff/mypy/tsc/gitleaks 7잡 게이트. coverage ≥35% |
| **문서·발표 자료** | 8.5 | architecture.md, V11.5 honesty, 회고·일지·sales-targets |

**종합**: **8.1 / 10** — 캡스톤 통과·B2G PoC 대화 가능 수준. 단 KDCA confirmed 연동 전까지 다질병 ML은 supervised 수준 미달.

---

### 1.2 캡스톤 4대 평가 기준 충족도

| 기준 | 상태 | 근거 |
|------|------|------|
| ① **기술 완성도** | ✅ 충족 | 3계층 실데이터 수집 + ML 17지역 walk-forward + Next.js 대시보드 통합 |
| ② **검증 결과** | ✅ 충족 (인플루엔자) / ⚠ 부분 (다질병) | 인플루엔자 F1=0.882 / FAR=0.206 (목표 F1≥0.80 / FAR<0.30 충족). 다질병은 proxy 한계 정직 노출 + 노로 transition +13%p |
| ③ **서비스성** | ✅ 충족 | http://34.47.113.176/dashboard 외부 노출, 실시간 신호·AI 경보·PDF 다운로드 |
| ④ **확장성** | ✅ 충족 | 다질병(COVID·노로) 시연 + region-pooled 모델 + 카테고리 사전 일반화 |

**4/4 충족** — 단, ② 평가는 인플루엔자 강하고 다질병은 정직 한계 명시.

---

### 1.3 ML 결과 통합 테이블 (정직)

| 병원체 | 모드 | 라벨 출처 | ML F1 | trivial F1 | gain | FAR | MCC | AUPRC |
|--------|------|-----------|-------|------------|------|-----|-----|-------|
| **인플루엔자** | level | **KDCA peak (외부)** | **0.882** | — | external supervised | **0.206** | 0.595 | 0.973 |
| COVID-19 | level | L2 self-proxy | 0.667 | 0.792 | -0.125 | 0.287 | 0.451 | 0.741 |
| COVID-19 | transition | L2 self-proxy | 0.217 | 0.276 | -0.060 | 0.135 | 0.135 | — |
| 노로 | level | L2 self-proxy | **0.756** | 0.797 | -0.042 | 0.273 | 0.527 | 0.762 |
| **노로** | **transition** | L2 self-proxy | **0.396** | 0.265 | **+0.131** | **0.107** | 0.334 | — |

**핵심 메시지**
- 인플루엔자: **외부 라벨이 있을 때의 실력** = 0.882
- proxy level: trivial이 ML을 이김 (proxy 한계 인정 — 정직성)
- 노로 transition: 어려운 task에서 ML이 trivial 대비 **+13%p**, FAR=0.107 (캡스톤 기준 큰 폭 충족)

---

### 1.4 자산 (B2G·R&D 가치)

| 자산 | 가치 |
|------|------|
| **데이터 파이프라인** | 17지역 × 3계층 × 53주, 즉시 KDCA·지자체 PoC 투입 가능 |
| **봐서 이해되는 ML 정직성** | proxy 한계 노출 + trivial 비교 = ISMS-P/조달청 신뢰성 가산 |
| **다질병 확장 프레임** | pathogen 인자화, 1개 추가 ≈ 1~2시간 (라벨만 필요) |
| **3축 검증 매트릭스** | 분류·시점·회귀 한 화면 = 심사위원 즉시 판단 가능 |
| **운영 체계** | systemd·nginx·이중 알람·시크릿 스캔 = 납품 수준 90% |

---

## 2. 발표 시나리오 (12분 권장)

### 2.1 슬라이드 흐름 (시간 배분)

| # | 슬라이드 | 시간 | 핵심 메시지 |
|---|---------|------|-----------|
| 1 | **타이틀** | 0:20 | Urban Immune System — 3계층 비의료 신호로 감염병 1~3주 선행 탐지 |
| 2 | **문제·왜 지금** | 1:00 | KDCA 확진자 지연 7~14일 → 지자체 대응 늦음. 3계층(L1·L2·L3)으로 임상 1~3주 선행 |
| 3 | **아키텍처 다이어그램** | 1:00 | docs/architecture.md Mermaid. 수집→Kafka→TimescaleDB→ML→FastAPI→Next.js |
| 4 | **데이터 (17지역, 53주)** | 0:40 | OTC 87주 / 하수 62주 / 검색 62주 / KMA 기상. 다질병 53주 |
| 5 | **인플루엔자 결과 (메인)** | 1:30 | **F1=0.882, FAR=0.206, Lead 6.76주**. 17지역 walk-forward. KDCA peak 외부 검증 |
| 6 | **3축 검증 매트릭스 (라이브 데모)** | 1:30 | 대시보드 띄우고 ① 분류 ② 시점 ③ 회귀 카드 보여줌 |
| 7 | **다질병 확장 (COVID·노로)** | 1:30 | self-target proxy + L1 카테고리 사전. **정직성**: trivial 비교 + transition task |
| 8 | **정직성 카드 (KEY)** | 1:00 | "level proxy는 trivial이 ML 이김(인정), 노로 transition은 ML +13%p 우위. KDCA 확진자 연동 후 인플루엔자 수준 supervised 회복 가능" |
| 9 | **시연: SSE 경보 + RAG 리포트** | 1:00 | 외부 IP 라이브, Claude Haiku RAG, PDF 다운로드 |
| 10 | **B2G 사업화 경로** | 0:30 | docs/business/sales-targets.md — KDCA·서울시·WHO 협력센터 PoC 시나리오 |
| 11 | **한계·로드맵** | 0:40 | KOWAS PDF 수동·KDCA 확진자 미연동·HTTPS — Phase 3 P0 |
| 12 | **Q&A** | 1:30 | (아래 예상 QA) |

**합계 ~12분** (Q&A 포함 13분)

---

### 2.2 핵심 데모 시퀀스 (슬라이드 6, 9)

```
1. http://34.47.113.176/dashboard 열기 (Basic Auth)
2. 인플루엔자 디폴트 → F1=0.882, Lead 6.76주 카드 강조
3. 지도에서 서울·경기 클릭 → 시계열·SSE 경보 표시
4. 병원체 셀렉터 → COVID-19 (β) 전환
5. 분류 카드 변경: F1=0.667 (vs trivial 0.792, gain -0.125)
   ← "정직성 — proxy 한계 인정"
6. AI 리포트 카드 우상단 SSE 스트림 (Claude Haiku RAG)
7. PDF 다운로드 클릭 → 4쪽 보고서 즉시 생성
```

---

### 2.3 예상 QA 10선 + 답변 (1줄 핵심)

| # | 질문 | 답변 |
|---|------|------|
| 1 | "F1=0.882 어느 데이터로 검증?" | KDCA 인플루엔자 ILI 주간보고 peak 17지역 walk-forward, gap=4주 5-fold, `analysis/outputs/backtest_17regions.json` |
| 2 | "다질병 0.67~0.76은 왜 인플루엔자보다 낮은가?" | KDCA COVID·노로 확진자 미연동 → L2 self-target proxy 학습. proxy의 한계로 단순 임계가 trivial로 작동. KDCA 연동 후 인플루엔자 수준 회복 예상 |
| 3 | "trivial보다 ML이 못하면 ML 의미는?" | level proxy에서는 그렇지만, 어려운 task(노로 transition)에서 ML 우위 +13%p. KDCA 외부 라벨 도착 후 supervised로 본질 가치 |
| 4 | "Google Flu Trends 실패와 무엇이 다른가?" | GFT는 L3 단독. 본 시스템은 L3 단독 경보 금지 + 2개 이상 계층 30 이상 게이트 + L2 하수 바이오마커(객관 신호) 가중치 0.40 최고 |
| 5 | "ISMS-P 준수는?" | Pydantic Settings 환경변수 검증, K8s SecurityContext (runAsNonRoot, readOnlyRootFilesystem), CORS 명시 도메인, 시크릿 스캔 CI, DPIA 초안 (`docs/business/advisory/22_dpia_draft.md`) |
| 6 | "납품 가격 모델?" | `docs/business/pricing-model.md` 3-tier (PoC 건당·연 구독·전국 확장) |
| 7 | "데이터 신뢰성·재현성?" | TimescaleDB 하이퍼테이블 1년치 누적, 67 PDF 파싱 캐시, ruff/mypy/pytest 113건 CI 게이트, 시크릿 스캔 |
| 8 | "한계는?" | ① L1·L3 네이버 API 전국 단일값 (HIRA Phase 3 분리), ② KOWAS PDF 수동 (Selenium Phase 3), ③ TFT-real 26주 한계 (12주 누적 후 재학습), ④ KDCA COVID 확진자 미연동 (P0) |
| 9 | "다음 단계는?" | Phase 4: ISMS-P 풀 점검 + 조달청 혁신제품 신청 + KDCA·서울시 PoC 파일럿 |
| 10 | "정직성 자랑한 이유?" | 심사위원이 의심할 수 있는 모든 지점을 먼저 노출 → 신뢰 확보. 사후 발견 시 신뢰 추락보다 사전 인정이 정량 가치 큼 |

---

### 2.4 어조 가이드

- **자랑할 것**: 인플루엔자 F1=0.882 + Lead 6.76주, 17지역 walk-forward 실측, 노로 transition ML +13%p, 라이브 외부 IP 데모
- **인정할 것**: proxy 한계, KDCA 확진자 미연동, KOWAS 수동, HTTPS 미적용
- **차별화**: "정직한 ML 시스템" — 다른 팀이 부풀린 지표 가지고 올 때 우리는 trivial 비교까지 공개

---

## 3. 발표까지 남은 To-Do (D-5~10)

| 우선 | 작업 | 소요 | 담당 |
|------|-----|------|------|
| **P0** | KDCA COVID·노로 확진자 API 신청 | 본인 | 박진영 (진행 중) |
| P1 | 대시보드 HTTPS (Let's Encrypt + DNS) | 2시간 | 박진영 |
| P1 | 발표 슬라이드 (Canva/Notion) | 4시간 | 박진영 |
| P1 | 리허설 2회 (시연 포함) | 2시간 | 전원 |
| P2 | KDCA 데이터 도착 시 즉시 다질병 supervised 재학습 | 2시간 (자동 파이프라인) | 박진영 |
| P2 | nginx Basic Auth 비번 재설정 + 팀 공유 | 5분 | 박진영 |
| P3 | TFT 다질병 회귀 확장 (B) | 3시간 | 발표 후 R&D |

---

## 4. 권장 결론 멘트 (발표 마무리)

> "우리는 인플루엔자에서 F1=0.882로 KDCA peak 6.76주 선행 탐지를 17지역 실측 검증했고,
> 다질병(COVID·노로)으로 동일 파이프라인 즉시 확장했습니다.
> 다만 KDCA 확진자 데이터 연동 전까지는 proxy 학습의 한계를 정직하게 노출했습니다.
> 이 정직성이 ISMS-P 심사·조달청 납품에서 차별점이며,
> KDCA 데이터 도착 즉시 다질병도 인플루엔자 수준에 도달할 수 있는 파이프라인이 이미 준비되어 있습니다."

---

## 5. 자료 원본 위치 (심사위원 질문 시 즉시 지목)

- `analysis/outputs/backtest_17regions.json` (인플루엔자 17지역 walk-forward)
- `analysis/outputs/backtest_xgboost_{covid,norovirus}_17regions.json` (level)
- `analysis/outputs/backtest_xgboost_{covid,norovirus}_transition_17regions.json` (transition)
- `analysis/outputs/lead_time_summary.json` (서울 Granger/CCF)
- `analysis/outputs/tft_regression_backtest_17regions.json` (TFT 회귀)
- `docs/architecture.md` (3계층 + 컴포넌트 토폴로지)
- `docs/business/sales-targets.md` (KDCA·서울시·WHO PoC 시나리오)
- `docs/business/pricing-model.md` (3-tier 가격)
