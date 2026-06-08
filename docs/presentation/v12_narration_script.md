# V12 발표 대본 — 12분 분 단위 발화 스크립트 (2026-06-17)

> 작성: 2026-06-08 (D-9, PPT freeze 6/15)
> 발표자가 그대로 읽어도 자연스러운 톤. 시간 단위·화면 동작·fail-safe 매핑.
>
> **흐름**: 인트로 3min → 데모 3min → 검증·정직성 3min → 마무리 3min = 총 12min
>
> **약속**: 큰따옴표 = 발화 그대로, `[ ]` = 화면 동작, **굵게** = 강조, *fail-safe* = 네트워크 끊김 대응

---

## 0:00 ~ 0:20 · S01 COVER

[ 슬라이드 S01 표지 띄움 ]

> "안녕하십니까. **Urban Immune System** — 도시 면역 체계.
> 동신대 컴퓨터공학과 5인팀 캡스톤, 박진영 발표 시작하겠습니다."

---

## 0:20 ~ 1:20 · S02 PROBLEM

[ S02 — 14일 발견 지연 ]

> "**병원에 가야 시작되는 감시. 우리는 항상 2주 늦습니다.**
> 증상 발현 → 병원 방문 → 진단 → 보건소 보고 → 질병관리청 집계.
> 이 다섯 단계에 평균 14일이 걸리고, 뉴스로 도달할 때엔 지역 확산은 이미 시작된 후입니다.
> 그래서 우리는 임상 신고를 기다리지 않고, **시민이 평소에 남기는 세 가지 비의료 신호**를 먼저 읽기로 했습니다."

---

## 1:20 ~ 2:00 · S03 SOLUTION

[ S03 — 약국 OTC / 하수 / 검색 3 카드 ]

> "약국 OTC 구매는 1~2주 선행. 하수 바이오마커는 **2~3주 선행** (가장 빠름).
> 검색 트렌드는 1~2주 선행.
> 세 신호 모두 사람들이 평소에 남기는 흔적입니다. 환자가 되기 전 단계."

---

## 2:00 ~ 2:30 · S04 CROSS-VALIDATION

[ S04 — Google Flu Trends vs 우리 ]

> "Google Flu Trends 는 검색 단독 신호로 실제의 **2배 과대예측**해 2013 년 폐기됐습니다.
> 우리는 그 실패를 코드에 박았습니다. **L3 단독 경보 절대 금지. 최소 2계층 동시 임계 초과만 게이트 통과.**"

---

## 2:30 ~ 3:00 · S05 ARCHITECTURE (+ S05A 데이터 근거)

[ S05 아키텍처 → S05A 카드 빠른 스킵 ]

> "수집은 왼쪽, 경보는 오른쪽으로. Kafka KRaft → TimescaleDB → 앙상블 게이트 → AI 추론 → 17개 시·도 대시보드.
> 3계층 선택 근거는 시민이 평소에 남기는 흔적 + 의료 영역과 분리된 객관 신호입니다."

---

## 3:00 ~ 3:30 · S08 SCOPE — 뺀 것과 추가한 것

[ S08 — REMOVED / ADDED ]

> "정직하게 말씀드리면, 캡스톤 범위에서 **뺀 것 7개**, **추가한 것 8개** 있습니다.
> GKE 프로덕션 클러스터·다국어 i18n·모바일 앱은 안 했고, 대신 **17지역 walk-forward 검증·KOWAS PDF 자동 다운로더·RAG 9 섹션·Granger 인과·TFT 70K params** 같은 본질에 집중했습니다."

---

## 3:30 ~ 4:30 · S10 + S10A 라이브 데모 진입

[ 대시보드 열기 — http://REDACTED-HOST (또는 localhost:3000) ]
*fail-safe: `docs/runbook/demo-backup-2026-06-08/02_dashboard_influenza.png` 띄움*

> "라이브 데모입니다. 화면이 외부 서버 GCP VM 에 떠 있고,
> Basic Auth 통해 보안 검토 끝난 상태로 시연합니다.
> 첫 화면 — **17개 시·도 지도**. 왼쪽 위 KPI 카드 4개 보입니다.
> **F1=0.907**, 검증 정확도. **Lead time 6.76주**, 임상 신고 평균 47일 전 위험 신호 포착.
> Composite score 19.58, L2 score 9.14 — 모두 실데이터."

---

## 4:30 ~ 5:30 · S11/S11A 검증 결과 + V11.6 ★

[ 대시보드 검증 매트릭스 영역 스크롤 → S11A 슬라이드 전환 ]
*fail-safe: `03_dashboard_influenza_full.png`*

> "검증 매트릭스. Precision 0.940 · Recall 0.882 · FAR 0.250 — 캡스톤 기준 F1 ≥ 0.80 / FAR < 0.30 모두 충족.
> Granger 인과검정 composite p=0.021, L3 검색 p=0.007 — 통계적 유의.
> **★ 그리고 V11.6** — 위 0.907 은 OTC z-score 기반 self-target proxy 라벨이었습니다.
> 발표 3일 전, KDCA 인플루엔자 4급 표본감시 ILI ground truth 로 라벨 교체 후 재학습했습니다.
> 결과 — **F1=0.96 · Precision=1.00 · FAR=0**. 임상 라벨 기준 진짜 실력입니다.
> 단, 양성 비율 82% 의 imbalance 캐비엇 — 'always positive' trivial F1 ≈ 0.85.
> 모델의 **진짜 gain 은 trivial L2 임계 baseline (F1=0.29) 대비 +0.67** 입니다. 정직히 분리 보고드립니다."

---

## 5:30 ~ 6:30 · S11B 다질병 시연 ★

[ 대시보드 — pathogen 셀렉터 클릭 → 'COVID-19 (베타)' 선택 → 화면 갱신 대기 → 다시 '노로바이러스' ]
*fail-safe: `04_dashboard_covid.png` → `05_dashboard_norovirus.png` 순차*

> "**한 시스템, 세 질병 검증.** 캡스톤 평가 4번째 항목 '확장성' 입증입니다.
> 같은 파이프라인·같은 모델·같은 대시보드.
> 인플루엔자 0.907 (V11.6 KDCA 0.96).
> [ COVID 클릭 ] COVID-19 F1=0.68. OTC 신호 약하고 변이 다양성으로 분산. transition target 도입으로 0.55→0.68 개선.
> [ 노로 클릭 ] 노로바이러스 F1=0.70. 단기 폭발 패턴 — 식중독·집단발병. transition target 이 level 대비 ML 우위 +13%p, FAR=0.107 입증.
> **질병별 신호 강도 차이를 그대로 노출** 합니다. 인플루엔자만 강하다 가 아니라 약한 질병도 베이스라인 측정 가능."

---

## 6:30 ~ 7:00 · S12 경쟁 + S12A 운영 신뢰도 ★

[ S12 → S12A 신규 슬라이드 ]

> "BlueDot·HealthMap·CDC NWSS — 글로벌 벤치마크 대비 우리는 **3-Layer 정량 신호 + 6.76주 선행 + KDCA 임상 라벨 검증** 한국 first-mover.
> 그리고 운영 신뢰도. **2주 전 5월 28일** — 수집기 17일 silent-fail 사고 발생.
> APScheduler 다운으로 데이터 적재 안 됨.
> 그 사고를 **첫 가동된 ntfy 알람이 즉시 잡아냈고**, misfire_grace_time 으로 영구 재방지했습니다.
> 사람보다 빠른 자동 탐지 입증 — Issue #63, GitHub 영구 기록."

---

## 7:00 ~ 8:00 · S13B/C/D 정직성 ★★

[ S13B 전문가 → S13C 정직성 6단 → S13D 6 한계 ]

> "정직성. 두 기관에 검증 요청했습니다 — 질병관리청과 한국인터넷진흥원.
> 그리고 V11.0 부터 V11.5 까지 정직성 **6 단**.
> V11.0 기준 확정. V11.1 신뢰구간 공개 (Recall CI 하한 0.834, 목표 0.85 살짝 미달도 명시).
> V11.2 검정군 솔직 (51 nominal → 18 effective).
> V11.3 합성 입력 명시.
> V11.4 룰 vs ML 분리.
> **V11.5 KDCA 라벨 갭** — self-proxy 와 KDCA ILI 일치율 29.5%, Cohen κ=0.058 (≈random) 정량 공개.
> 한계 6개도 같이 — **단일 시즌, 양성 imbalance, 펜데믹 미검증, Recall 경계, 전국 broadcast, KOWAS 7-10일 lag + 60% carry-forward.**
> 마지막 항목 — 운영 DB audit 결과 L2 데이터의 60.7% 가 같은 value 연속. 새 측정 vs 이전 주 복제 분리 불가, Phase 3 meta JSONB 컬럼 추가로 정확 추적 예정."

---

## 8:00 ~ 9:30 · S15 회고 + S14A Evolution 9주

[ S15 → S14A ]

> "5월 7일 중간발표 → 6월 17일 최종발표, 6주 동안 한 것.
> ✅ KDCA ILI ground truth 검증 + 재학습 (F1=0.96)
> ✅ 다질병 확장 (COVID 0.68 / 노로 0.70)
> ✅ silent-fail 사고 → 자동 탐지 → 영구 재방지
> ✅ V11.6 + V11.7 정직성 정량 추가
> 9주 Evolution — V11.0 부터 V11.6 까지 메트릭 +0.066 (self-proxy) → +0.053 (KDCA), 정직성 5단 추가."

---

## 9:30 ~ 10:30 · S14 비전 + S16 팀

[ S14 → S16 ]

> "인플루엔자는 검증 대상이고, **다음 팬데믹이 진짜 타깃** 입니다.
> 타깃 고객 — KDCA 국가 R&D / 서울시·광역지자체 SaaS / WHO 협력센터 국제 벤치마크.
> 5인 팀 — PM/AI 박진영, Backend 이경준, Data 이우형, Frontend 김나영, DevOps 박정빈.
> AI 도구 (Claude Code Opus·Sonnet) 정직 사용했고, 핵심 설계·의사결정은 모두 사람."

---

## 10:30 ~ 12:00 · S16A Q&A 5장 + 결론

[ S16A Q&A 5 카드 ]

> "예상 질문 5장 — 모두 동일 한 줄 패턴: **'정직히 인정, Phase 2/3에서 보강'**.
> AI 도구 정직 / Recall borderline / 시도별 신호 같음 / TFT PoC / 단일 시즌."

[ 마무리 발화 ]

> "**우리는 인플루엔자에서 self-proxy F1=0.907 → KDCA 임상 라벨 재학습 F1=0.96 / FAR=0 까지 달성**했고,
> 다질병 (COVID·노로) 으로 즉시 확장, 노로 transition 에서 ML 우위 +13%p 입증했습니다.
> L2 데이터 60.7% carry-forward 한계까지 사전 정량 공개했습니다.
> 이 **7단 정직성**이 ISMS-P 심사·조달청 납품에서 차별점이며,
> Phase 3 HIRA OpenAPI 활성 + meta 마이그레이션으로 carry-forward 정확 추적까지 후속 준비되어 있습니다.
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
http://REDACTED-HOST/slides (또는 localhost:3000/slides)
# 첫 화면 (S01) 로딩 확인 — babel transform 1~2초

# 4. pathogen 셀렉터 작동 테스트 (인플 → COVID → 노로 → 인플 복귀)
```

## ⚠️ 발표 중 사고 대응

| 상황 | 대응 |
|---|---|
| 네트워크 끊김 | "잠시 네트워크 점검 중입니다 — 백업 화면으로 보여드리겠습니다" → PNG 노트북 화면 |
| 대시보드 500 에러 | "API 응답 지연 — 캡처 자료로 대신합니다" → `docs/runbook/demo-backup-2026-06-08/*_full.png` |
| pathogen 셀렉터 응답 지연 | 4초 대기 후에도 갱신 안 되면 백업 PNG 로 즉시 전환 |
| Q&A 모르는 질문 | "그 부분은 GitHub `analysis/outputs/*.json` 산출물에 정리되어 있어, 발표 후 즉시 회신드리겠습니다" |

## 🎯 발화 길이 마진

각 구간 ±10초 여유 (총 12분 ± 1분). 시연 라이브 클릭 지연 시 발화 잠시 멈춤 자연스러움.
