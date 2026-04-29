# UIS 챗봇 지식 베이스

> 챗봇이 답변할 시스템 동작 설명. `{...}` 자리표시자는 부팅 시 코드/설정에서 동적 치환된다.
> **이 파일과 코드를 동시에 갱신하라**. 텍스트 설명은 여기서, 숫자 값은 코드 단일 출처에서.

## 시스템 개요
Urban Immune System(UIS)은 한국 감염병 조기경보 AI 시스템입니다. 임상 확진보다 1~3주 빠른 비의료 신호 3계층(약국·하수·검색)을 교차검증해 광역 단위 위험을 추정합니다. B2G(질병관리청·지자체) 납품을 목표로 합니다.

## 데이터 파이프라인
1. **수집** — APScheduler cron으로 주 1회 외부 소스에서 데이터 수집
2. **정규화** — 각 계층 0~100 Min-Max 스케일링
3. **적재** — TimescaleDB(`layer_signals` 하이퍼테이블)에 시계열 저장
4. **앙상블** — 3계층 가중합 + 2-레이어 교차검증 게이트로 위험도 산출
5. **ML 추론** — XGBoost(주모델) / TFT(7·14·21일 선행) / Autoencoder(라벨 없는 이상탐지)
6. **RAG 리포트** — Qdrant 역학 가이드 검색 + Claude로 markdown 리포트 작성
7. **대시보드** — Next.js(KoreaMap·KPI·시계열·팬데믹탐지·AI리포트 SSE)

## 3계층 신호와 갱신 주기
- **L1 OTC 약국판매** (네이버 쇼핑인사이트) — 매주 월 09:00 KST 수집
- **L3 검색 트렌드** (네이버 DataLab) — 매주 월 09:05 KST
- **L2 KOWAS 하수 바이오마커** — 매주 화 09:30 PDF 다운로드 → 10:00 파싱·적재
- **AUX 기상** (기상청 KMA) — 매시간 정각
- **KCDC 임상 확진자** (정답 라벨) — 매주 금 09:30
- **앙상블 점수 계산** — 매주 수 11:00 (3계층 수집 후)
- **RAG 야간 배치** — 매일 12:00 (YELLOW 이상 지역만, GREEN 스킵)

## 앙상블 공식
```
composite_score = {w1} · L1 + {w2} · L2 + {w3} · L3
```
- L2(하수) 가중치가 가장 높습니다 — 임상 확진자보다 가장 빠른 선행지표
- L3(검색)는 인포데믹 위험으로 단독 발령 금지

## 경보 레벨
| 레벨 | composite 임계 | 의미 |
|---|---|---|
| GREEN | < {yellow_threshold} | 정상 모니터링 |
| YELLOW | {yellow_threshold} ≤ x < {orange_threshold} | 주의 — 손씻기·캠페인 강화 |
| ORANGE | {orange_threshold} ≤ x < {red_threshold} | 경계 — 격리병상·항바이러스제 점검 |
| RED | ≥ {red_threshold} | 심각 — 광역 비상대응 |

**게이트 규칙**: YELLOW 이상 발령은 L1·L2·L3 중 **{gate_min_layers}개 이상 계층**이 **{gate_layer_threshold}점 이상**이어야 합니다. 단독 계층만 높으면 GREEN으로 자동 다운그레이드(Google Flu Trends 과대예측 사고 교훈).

## ML 모델 역할
- **XGBoost** (`/api/v1/predictions`) — 현재 주모델. composite 회귀, walk-forward CV 5-fold로 검증.
- **TFT** (`/api/v1/predictions/tft-{{7,14,21}}d`) — 7·14·21일 선행 예측. 데이터 누적 후 주모델로 전환 예정.
- **Autoencoder** (`/api/v1/predictions/anomaly`) — 라벨 없이 정상 패턴만 학습 → 재구성 오차로 "평소와 다른 신호" 검출. 신규 병원체 조기탐지용.
  - 현재 임계값: **{autoencoder_threshold:.4f}** ({autoencoder_percentile}p percentile)

## RAG 리포트
- 트리거: 매일 12시 배치(YELLOW+) 또는 사용자가 대시보드에서 클릭(SSE 실시간)
- 검색: Qdrant `epidemiology_docs` 컬렉션 17건(WHO·KDCA·논문 등) → top-3 가이드 인용
- LLM: Claude Haiku (속도 우선) — 7섹션 markdown(요약·지표·레이어·전망·권고·문헌·면책)
- 권고는 alert_level별 액션 가이드(보건당국/의료기관/시민) 차등

## 시스템 가치
- **선행성**: 하수 신호가 임상 확진보다 1~2주 빠름 (Granger 인과성 p<0.05 검증)
- **교차검증**: 단일 신호 단독 경보 금지 — Google Flu Trends 사고(검색만 의존 → 140% 과대예측) 교훈
- **라벨 불필요**: Autoencoder가 정상 패턴 학습으로 미지의 병원체도 검출 가능

## 자동화
- 모든 cron은 GCP VM `Asia/Seoul` 타임존 systemd 서비스(`uis-scheduler`)에서 가동
- 코드 자체는 GitHub `feat/business-docs-and-rag-expand` 브랜치에서 관리, PR 머지 시 develop → main
- 모델 재학습은 의도적으로 **수동** (역학조사관 검토 후 재학습이 ISMS-P 권장 사항)

## 면책
본 시스템은 AI 보조 의사결정 도구입니다. 공중보건 정책 수립 시 인간 전문가(역학조사관·보건당국)의 검토가 필수이며, 의료적 진단·처방을 대체하지 않습니다 (ISMS-P 2.9 / EU AI Act 준수).
