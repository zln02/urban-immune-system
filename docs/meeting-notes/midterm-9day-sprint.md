# 중간발표 D-9 9일 스프린트 계획

> 작성 2026-04-21 · 기준 발표일 **2026-04-30** · 작성자 박진영
> 목표: "돌아가는 시스템 시연 가능" + "박진영 원맨쇼 반박 가능"

---

## 🎯 L2 달성 목표 (현실적 최대치)

**L2 = 배치 실데이터 시연** (성공 확률 55%)
- KDCA ILINet 2024-25 시즌 CSV 수동 다운로드
- 네이버 DataLab API 키 발급 후 1회 수집
- LightGBM walk-forward 학습 → 실데이터 F1 확보
- Streamlit 에 "합성 / 실데이터" 비교 탭 추가
- ngrok 터널로 발표 당일 임시 URL 제공

**L3 (라이브 스트리밍) 절대 주장 금지**: Kafka Consumer 미구현. "지금 실시간 연결" 거짓말 금지.

---

## 📅 일별 작업 (담당자 명시)

### D-9 · 2026-04-21 (월) — **오늘**
| 담당 | 작업 | 산출물 |
|---|---|---|
| 박진영 | 네이버 개발자센터 앱 등록 → Client ID/Secret 발급 → `.env` 입력 | 키 2개 |
| 박진영 | KDCA 감염병포털 (is.kdca.go.kr) 2024-25 시즌 ILINet CSV 수동 다운로드 | `pipeline/data/kdca_ili_2024.csv` |
| 이우형 | (온보딩) SSH 접속 + `cd pipeline && claude` 배지 확인 + 이슈 #4 읽기 | Slack 보고 |
| 이경준 | (온보딩) 이슈 #3 읽기 + backend config.py 수정 확인 (방금 고침) | Slack 보고 |
| 김나영 | (온보딩) 이슈 #5 읽기 + Streamlit URL 열어보기 | 스크린샷 |
| 박정빈 | (온보딩) 이슈 #6 읽기 + Branch Protection 웹 UI 설정 | 설정 스크린샷 |

### D-8 · 4/22 (화)
| 담당 | 작업 |
|---|---|
| 박진영 | `python analysis/notebooks/performance_measurement.py` 에 KDCA CSV 로드 경로 추가, LightGBM 옵션 추가 → 실데이터 F1 1차 결과 |
| 이우형 | `search_collector.py` 로 네이버 검색 12주치 수집 → `pipeline/data/naver_search_2024.csv` |
| 이경준 | `/api/v1/signals/latest` 임시 구현 (TimescaleDB row 0 이면 JSON 반환) |
| 김나영 | `src/tabs/validation.py` 에 "실데이터 탭" 분리 |
| 박정빈 | CI 에 trivy + codeql 잡 녹색 유지 · axe-core accessibility 추가 |

### D-7 · 4/23 (수)
| 담당 | 작업 |
|---|---|
| 박진영 | KDCA + 네이버 검색 통합 피처 3개로 LightGBM 재학습 → 실데이터 F1 최종 |
| 이우형 | `otc_collector.py` 실제 네이버 쇼핑 카테고리 ID 로 교체 + 1회 수집 |
| 이경준 | JWT 인증 미들웨어 PR 오픈 (이슈 #3) |
| 김나영 | 실데이터 시각화 2차 반복 · Storybook 컴포넌트 1개 스캐폴드 |
| 박정빈 | k6 스파이크 테스트 스크립트 1개 |

### D-6 · 4/24 (목)
| 담당 | 작업 |
|---|---|
| 박진영 | 발표 슬라이드 수치 갱신 (합성 F1=0.643 + 실데이터 F1=??) |
| 이우형 | `authored-by/이우형/kafka-timescaledb-pipeline.md` 초안 |
| 이경준 | `authored-by/이경준/jwt-audit-log-design.md` 초안 |
| 김나영 | `authored-by/김나영/deckgl-choropleth.md` 초안 |
| 박정빈 | `authored-by/박정빈/k6-sla-gate.md` 초안 |

### D-5 · 4/25 (금)
| 담당 | 작업 |
|---|---|
| 전원 | 각자 authored-by 포스트 머지 (git blame 증거) |
| 박진영 | 발표 스크립트 재분배 버전 작성 (박진영 5분 + 팀원 2.5분씩) |
| 박정빈 | Prometheus 대시보드 JSON 1개 (모니터링 증거) |

### D-4 · 4/26 (토)
| 담당 | 작업 |
|---|---|
| 박진영 | ngrok 터널 테스트 (30분 임시 URL 생성 · 외부 접속 확인) |
| 전원 | 팀원별 슬라이드 섹션 3장 작성 (git blame 증거) |
| 박정빈 | 로컬 docker compose 최소 버전 (TSDB 만) 안정화 · Plan B |

### D-3 · 4/27 (일)
| 담당 | 작업 |
|---|---|
| 전원 | **풀 리허설 1회** (ZOOM 녹화) · 피드백 수집 |
| 박진영 | 예상 질문 Top 10 답변 재확인 (`demo-scripts.md`) |
| 김나영 | 스크린샷 5장 `docs/images/screenshots/` 재캡처 (Okabe-Ito 팔레트) |

### D-2 · 4/28 (월)
| 담당 | 작업 |
|---|---|
| 박진영 | **팀 W18 회의** — 협업 가이드 PDF 배포 · 스코어보드 집계 |
| 전원 | 주간 일지 작성 (docs/weekly-reports/2026-W18/) |

### D-1 · 4/29 (화)
| 담당 | 작업 |
|---|---|
| 전원 | **풀 리허설 2회** (실제 노트북·프로젝터 환경) |
| 박진영 | Plan B 전환 훈련 (데모 URL 죽을 때 10초 이내 로컬 전환) |
| 박정빈 | 발표 당일 체크리스트 최종 (인터넷·노트북·HDMI 어댑터·USB PPT 백업) |

### D-0 · 4/30 — 발표일

---

## 🎤 발표 15분 시간 분배 (박진영 원맨쇼 반박)

| 시간 | 발표자 | 슬라이드 | 내용 |
|---|---|---|---|
| 0:00-1:00 | 박진영 | 1-2 | 표지 + 문제 정의 |
| 1:00-3:00 | 박진영 | 3-4 | 3-Layer 아이디어 + 아키텍처 |
| 3:00-5:30 | **이우형** | 5 | 데이터 파이프라인 (Kafka·KOWAS 파서·수집 SLA) |
| 5:30-8:00 | **이경준** | 6 | Backend API (JWT · Rate Limiting · OpenAPI · p95) |
| 8:00-10:30 | **김나영** | 7 Demo | Frontend 데모 (지도 · Storybook · E2E) |
| 10:30-13:00 | **박정빈** | 8 | DevOps (CI · Prometheus · k6 · ISMS-P) |
| 13:00-15:00 | 박진영 | 9-14 | B2G 로드맵 + 솔직 진단 + Q&A |

박진영 5분 + 팀원 각 2.5분. 슬라이드 섹션별로 팀원이 직접 git commit → git blame 에 본인 이름.

---

## 🔴 교수님 예상 질문 대응 3대

**Q1. "박진영 이외 기여 증거는?"**
답변:
- `git shortlog -sn` 로 팀원 5명 커밋 분포 제시
- `.github/CODEOWNERS` 로 모듈별 자동 리뷰 할당 확인
- `docs/portfolio/authored-by/{이름}/` 팀원별 포스트 제출
- 발표 시간 분배 (박진영 5분 + 팀원 각 2.5분)

**Q2. "실제 돌아가나요?"**
답변:
- "Streamlit 5탭 로컬 시연 가능합니다 (URL 또는 ngrok 터널)"
- "Backend `/health` `/docs` 응답 확인되어 있습니다 (방금 config 버그 수정 완료)"
- "상관관계·검증 수치는 statsmodels·sklearn 으로 **실제 계산**됐고, 데이터만 합성(seed=42)입니다"
- "위험도 지도·리포트 수치는 현재 하드코딩 상태 — 솔직히 인정하고 Phase 2 계획 제시"

**Q3. "언제 실데이터 되나요?"**
답변:
- "네이버 API 는 당일 발급 가능, D-8 까지 1회 수집 완료 예정"
- "KDCA CSV 수동 다운로드 후 LightGBM 으로 D-7 까지 실데이터 F1 확보 목표"
- "Kafka Consumer → TimescaleDB 실시간 적재는 Phase 2 (5-6월) 로 투명하게 선언"

---

## ⚠️ 시연 실패 Plan B

| 상황 | 대응 |
|---|---|
| 발표장 네트워크 불안정 | ngrok 포기 · 로컬 노트북 Streamlit |
| Streamlit 죽음 | 스크린샷 10장 PDF · 미리 녹화된 MP4 3분 |
| 네이버 API 429 | `NAVER_MOCK=true` 환경변수로 캐시 반환 |
| TFT 예측 실패 | "LightGBM 베이스라인 먼저" 투명 선언 |
| 질문 답 막힘 | "`docs/portfolio/interview-faq/` 에 정리되어 있습니다. 이메일 답변드리겠습니다" |

---

## ✅ 성공 기준 (4/30 종료 시점)

- [ ] 15분 발표 무사 완료 + Q&A 5분 대응
- [ ] 팀원 4명 각자 슬라이드 섹션 발표 (박진영 원맨 반박)
- [ ] 로컬 Streamlit 데모 작동 (URL 또는 로컬)
- [ ] KDCA 실데이터 기반 LightGBM F1 수치 제시 (합성 0.643 외 1개 더)
- [ ] `authored-by/` 팀원별 포스트 1편씩 존재
- [ ] 솔직한 자기 진단 슬라이드(Slide 8) 로 신뢰도 확보
- [ ] 불가능한 주장("실시간 연결") 절대 안 함
