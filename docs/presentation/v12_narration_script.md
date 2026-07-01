# V12.1 발표 대본 — 12분 / 15장 다이어트 (2026-06-17)

> 갱신: 2026-06-09 (D-8) · V12 22장 → **V12.1 15장 다이어트** (평균 48초/장)
> 발표자가 그대로 읽어도 자연스러운 톤. 시간·화면 동작·fail-safe 매핑.
>
> **흐름**: 인트로 3min → 데모 3min → 검증·정직성 3min → 마무리 3min = 총 12min
>
> **약속**: 큰따옴표 = 발화 그대로, `[ ]` = 화면 동작, **굵게** = 강조, *fail-safe* = 네트워크 끊김 대응
>
> **V12 → V12.1 변경**: 7장 hidden (S05A·S10A·S12·S13B·S14A·S14·S16) — 모두 발화로 흡수

---

## 0:00 ~ 0:20 · S01 COVER

[ 슬라이드 S01 표지 ]

> "안녕하십니까. **Urban Immune System** — 도시 면역 체계.
> 제1회 데이터로 미래를 그리는 AI 아이디어 공모전 대상 수상팀 Urban Immune System, 박진영 발표 시작하겠습니다."

---

## 0:20 ~ 1:20 · S02 PROBLEM

[ S02 — 14일 발견 지연 ]

> "**병원에 가야 시작되는 감시. 우리는 항상 2주 늦습니다.**
> 증상 → 병원 → 진단 → 보고 → 집계, 다섯 단계 평균 14일.
> 그래서 우리는 임상 신고를 기다리지 않고, **시민이 평소에 남기는 세 가지 비의료 신호**를 먼저 읽기로 했습니다."

---

## 1:20 ~ 2:00 · S03 SOLUTION

[ S03 — 약국 OTC / 하수 / 검색 3 카드 ]

> "약국 OTC 1~2주 선행 — 실데이터 검증상 단방향 선행이 확인된 유일한 신호. 하수·검색은 바이러스 직접 측정/실시간성 강점은 있으나, 교차상관·Granger상 임상과 동시~소폭(양방향)이라 '선행'으로 단정하지 않습니다.
> 모두 사람들이 환자가 되기 전 단계에 남기는 흔적입니다."

---

## 2:00 ~ 2:40 · S04 CROSS-VALIDATION

[ S04 — Google Flu Trends vs 우리 ]

> "Google Flu Trends 는 검색 단독으로 실제의 **2배 과대예측**해 2013년 폐기됐습니다.
> 우리는 그 실패를 코드에 박았습니다 — **L3 단독 경보 금지. 최소 2계층 동시 임계 초과만 게이트 통과.**"

---

## 2:40 ~ 3:20 · S05 ARCHITECTURE (+ S05A 데이터 근거 흡수)

[ S05 아키텍처 다이어그램 ]

> "수집은 왼쪽, 경보는 오른쪽으로. Kafka KRaft → TimescaleDB → 앙상블 게이트 → AI 추론 → 17개 시·도 대시보드.
> 세 신호 선택 근거는 **시민이 평소에 남기는 흔적 + 의료 영역과 분리된 객관 신호**입니다."

---

## 3:20 ~ 3:50 · S08 SCOPE — 뺀 것과 추가한 것

[ S08 — REMOVED / ADDED ]

> "정직하게 — **뺀 것 7개, 추가한 것 8개**.
> GKE 프로덕션·다국어·모바일은 안 했고, 대신 **17지역 walk-forward·KOWAS PDF 자동·RAG 9 섹션·Granger·TFT** 본질에 집중."

---

## 3:50 ~ 5:00 · S10 라이브 데모 (S10A 흡수 — 관제실 흐름)

[ 대시보드 열기 — http://REDACTED-HOST (또는 localhost:3000) ]
*fail-safe: `docs/runbook/demo-backup-2026-06-08/02_dashboard_influenza.png`*

> "라이브 데모입니다. **17개 시·도 지도**, 왼쪽 위 KPI 카드 4개.
> **F1=0.907** (self-proxy 라벨·KDCA κ=0.058), **Lead time 6.76주** (동일 self-proxy 기준 — 실데이터로 검증된 선행은 L1 OTC ~2주뿐, 6.76주는 미입증).
> [ 지도에서 서울 클릭 → 시계열·SSE 경보 표시 ]
> 우상단 **AI 리포트 카드** — Claude Haiku RAG 가 SSE 로 스트리밍 생성. PDF 다운로드 클릭 한 번으로 4쪽 보고서."

---

## 5:00 ~ 5:50 · S11 MEASURED

[ S11 — 6.76 + 메트릭 5개 ]

> "숫자를 있는 그대로. **6.76주 선행 평균** — 단 self-proxy 라벨 기준이며, 실데이터로 검증된 선행은 L1 OTC ~2주입니다. 17지역 walk-forward.
> F1 0.907 · Precision 0.940 · Recall 0.882 · AUPRC 0.973 · **오경보율 0.250** — 모두 공모전 심사 기준 F1≥0.80 / FAR<0.30 충족.
> Granger composite p=0.021, L3 검색 p=0.007 — 통계적 유의."

---

## 5:50 ~ 6:50 · S11A RULE-BASED + V11.6 ★

[ S11A — Gate B + 우측 V11.6 박스 ]

> "**코드가 막은 오경보 −58.5%** — 단일계층 FAR 0.602 → 게이트 ON 0.250. Gate B = 2계층 동시 임계 강제.
> **★ 그리고 V11.6** — 위 0.907 은 OTC z-score 기반 self-target proxy 라벨이었습니다.
> 발표 사흘 전, KDCA 인플루엔자 4급 표본감시 ILI ground truth 로 라벨 교체 후 재학습.
> 결과 — **F1=0.96 · Precision=1.00 · FAR=0**. 임상 라벨 기준 진짜 실력.
> 단, 양성 비율 82% imbalance — trivial 'always positive' F1≈0.85. 모델 **진짜 gain 은 trivial L2 임계 (F1=0.29) 대비 +0.67** 입니다."

---

## 6:50 ~ 7:50 · S11B 다질병 ★ (S12 경쟁 발화 흡수)

[ pathogen 셀렉터 클릭 → COVID → 노로 순차 ]
*fail-safe: `04_dashboard_covid.png` → `05_dashboard_norovirus.png`*

> "**한 시스템, 세 질병 검증.** 공모전 심사 '확장성' 항목 입증.
> 인플루엔자 0.907 (V11.6 KDCA 0.96).
> [ COVID 클릭 ] COVID-19 F1=0.667. OTC 신호 약하고 변이 분산. transition target 으로 0.55→0.68.
> [ 노로 클릭 ] 노로 F1=0.756. 단기 폭발 패턴. transition target 이 level 대비 ML 우위 **+13%p**, FAR=0.107.
> BlueDot·HealthMap·CDC NWSS 같은 글로벌 벤치마크와 달리 **한국 first-mover · 3-Layer 정량 신호 · KDCA 임상 라벨 검증** 차별점."

---

## 7:50 ~ 8:30 · S12A 운영 신뢰도 ★

[ S12A — 3 stage ]

> "운영 신뢰도. 발표 2주 전 5월 28일 **수집기 17일 silent-fail 사고** 발생 — APScheduler 다운으로 데이터 적재 안 됨.
> 그 사고를 **첫 가동된 ntfy 알람이 즉시 잡아냈고**, misfire_grace_time 으로 영구 재방지.
> **그리고 어제 6월 9일, silent-fail #2 발견** — 같은 scheduler 가 active 인데 wastewater 잡만 `Event loop is closed` 로 6일간 silent fail.
> 24시간 안에 root cause 진단 + fix + regression test 5 PASS — **운영 신뢰도는 단발 복구가 아니라 지속 모니터링**임을 입증."

---

## 8:30 ~ 9:30 · S13C 정직성 6단 ★

[ S13C — 6 카드 ]

> "정직성 **6 단**.
> V11.0 기준 확정. V11.1 신뢰구간 (Recall CI 하한 0.834, 목표 0.85 미달도 명시).
> V11.2 검정군 솔직 (51 nominal → 18 effective).
> V11.3 합성 입력 명시.
> V11.4 룰 vs ML 분리.
> **V11.5 KDCA 라벨 갭** — self-proxy 와 임상 라벨 일치율 29.5%, Cohen κ=0.058 정량 공개."

---

## 9:30 ~ 10:30 · S13D 한계 + 전문가 검토 요청 (S13B 흡수)

[ S13D — 6 한계 ]

> "한계 6개도 정직 — 단일 시즌, 양성 imbalance, 펜데믹 미검증, Recall 경계, 전국 broadcast, **KOWAS 7~10일 lag + 60% carry-forward** (운영 DB audit).
> 마지막 항목은 V11.7 — 운영 DB 의 L2 데이터 60.7% 가 같은 value 연속. 새 측정 vs 이전 주 복제 분리 불가, Phase 3 meta JSONB 컬럼 추가로 정확 추적 예정.
> 그리고 이 모든 한계를 **두 외부 기관 — 질병관리청과 한국인터넷진흥원** 에 검토 요청 패키지로 제출했습니다."

---

## 10:30 ~ 11:30 · S15 회고 + Phase 4 (S14A 9주 + S14 비전 흡수)

[ S15 — 6주 회고 + Phase 4 targets ]

> "5월 7일 중간발표 → 6월 17일 최종발표, **6주 + 정직성 V11.6~V11.7 추가 9주 진보**.
> ✅ KDCA ILI ground truth 검증 + 재학습 (F1=0.96)
> ✅ 다질병 확장 (COVID 0.68 / 노로 0.70)
> ✅ silent-fail #1 + #2 → 자동 탐지 → 영구 재방지
> ✅ V11.5/V11.6/V11.7 정직성 정량 추가
> 다음 단계 — Phase 4 ISMS-P 풀 점검 + 조달청 혁신제품 신청 + 파일럿 기관 (질병관리청·서울시·WHO 협력센터).
> **인플루엔자는 검증 대상이고, 다음 팬데믹이 진짜 타깃**입니다."

---

## 11:30 ~ 12:00 · S16A 클로징 + Q&A (S16 팀 흡수)

[ S16A — Q&A 5 카드 ]

> "예상 질문 5장 — 모두 동일 한 줄 패턴: **'정직히 인정, Phase 2/3에서 보강'**.
> 팀 3인 — PM/ML Lead 박진영, Data Engineer/Backend 윤재영, Frontend·UX·발표 정욱현. Claude Code Opus·Sonnet 정직 사용했고 핵심 설계는 모두 사람."

[ 마무리 발화 ]

> "**self-proxy F1=0.907 → KDCA 임상 라벨 재학습 F1=0.96 / FAR=0**.
> 다질병 즉시 확장, 노로 transition ML 우위 +13%p.
> L2 carry-forward 60.7% 한계 + silent-fail 두 번 발견 / 빠른 fix 까지 사전 정량 공개.
> **7단 정직성**이 ISMS-P 심사·조달청 납품 차별점이며, Phase 4 ISMS-P + 파일럿 기관 컨택 준비 완료.
> 도시 면역 체계, Urban Immune System. 감사합니다."

[ 박수 → Q&A 자유 ]

---

## 📋 발표 30분 전 체크리스트

```bash
# 1. 외부 IP 환경 검증
curl -s http://localhost:3000/dashboard -o /dev/null -w "frontend %{http_code}\n"
curl -s http://localhost:8001/api/v1/health -o /dev/null -w "backend %{http_code}\n"

# 2. 발표 노트북에 fail-safe PNG 다운로드 (사전 1회)
scp -r wlsdud5035@REDACTED-HOST:~/urban-immune-system/docs/runbook/demo-backup-2026-06-08/*.png ./presentation_backup/

# 3. 슬라이드 deck 사전 로딩
http://REDACTED-HOST/slides → 첫 화면 (S01) 로딩 확인 — babel transform 1~2초

# 4. pathogen 셀렉터 작동 테스트 (인플 → COVID → 노로 → 인플 복귀)
```

## ⚠️ 발표 중 사고 대응

| 상황 | 대응 |
|---|---|
| 네트워크 끊김 | "잠시 네트워크 점검 중입니다 — 백업 화면으로 보여드리겠습니다" → PNG 노트북 화면 |
| 대시보드 500 에러 | "API 응답 지연 — 캡처 자료로 대신합니다" → `_full.png` 사용 |
| pathogen 셀렉터 응답 지연 | 4초 대기 후에도 갱신 안 되면 백업 PNG 로 즉시 전환 |
| Q&A 모르는 질문 | "그 부분은 GitHub `analysis/outputs/*.json` 산출물에 정리되어 있어, 발표 후 즉시 회신드리겠습니다" |

## 🎯 발화 길이 마진

각 구간 ±10초 여유 (총 12분 ± 1분). V12.1 평균 48초/장 — V12 33초/장 대비 1.5배 여유.
