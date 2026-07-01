# Urban Immune System — 팀원 실행 가이드
## 개발 점검 · 특허 출원 · 전문가 검증

**작성일**: 2026-05-10 (중간발표 D+3)  
**작성자**: 박진영 (PM / ML Lead)  
**수신**: 윤재영(Data Engineer/Backend) · 정욱현(Frontend·UX·발표)

---

## 1부. 현재 개발 현황 및 담당자별 과제

### 전체 완성도 (2026-05-10 기준)

| 모듈 | 담당 | 완성도 | 핵심 미완 사항 |
|---|---|---|---|
| ML | 박진영 | 75% | TFT-real 데이터 누적 후 재학습 |
| Backend | 윤재영 | 80% | advisory_pdf·report_pdf 테스트 0%, ML fallback 없음 |
| Pipeline | 윤재영 | 65% | KOWAS Selenium 자동화, kafka 테스트 0%, scorer 31% |
| Frontend | 정욱현 | 85% | slides-animated 삭제 미커밋, 단위 테스트 없음 |
| Infra / QA | 박진영 | 70% | 커버리지 39%(목표 70%), systemd 미기동, K8s ingress 없음 |

### 즉시 처리 (P0 — 오늘)

1. `git push origin develop` — 로컬 1커밋이 origin 대비 ahead 방치 중
2. `frontend/public/slides-animated/` 13개 삭제 파일 + `docs/STATUS.md` · `docs/layer_specs.md` 커밋
3. FastAPI backend(:8001), Next.js frontend(:3000) 서비스 기동 확인

---

### 윤재영 (Backend) 담당 과제

**개발 (최종발표 전)**

- [ ] `backend/app/services/advisory_pdf.py` 테스트 작성 (현재 커버리지 0%)
- [ ] `backend/app/services/report_pdf.py` 테스트 보강 (현재 16%)
- [ ] `backend/app/services/alert_service.py` 커버리지 40% → 70%
- [ ] `backend/app/services/prediction_service.py` ML 서비스 미실행 시 fallback 로직 추가
- [ ] `backend/app/middleware/auth.py` 커버리지 78% → 90%+

**특허 관련**

- [ ] 발명 공개 신고서에 이름·소속·서명 제출 (아래 3부 참조)
- [ ] Backend API 엔드포인트 문서화 완료 (전문가 데모 시 필요)

**전문가 검증 관련**

- [ ] Swagger/OpenAPI 문서 (`/docs`) 스크린샷 캡처 → `docs/business/advisory/` 추가
- [ ] p95 응답시간 측정 리포트 작성 (조달청 기준 500ms 이하 증빙)

---

### 정욱현 (Frontend) 담당 과제

**개발 (최종발표 전)**

- [ ] `frontend/public/slides-animated/` 13개 deleted 파일 스테이징 후 커밋
- [ ] `frontend/src/lib/api.ts` 분산된 fetch 호출 통합 정리
- [ ] `README.md` Next.js 버전 표기 수정 (현재 15 → 실제 14.2.3)
- [ ] 단위 테스트 최소 1개 파일 추가 (컴포넌트 스모크 테스트)

**특허 관련**

- [ ] 발명 공개 신고서에 이름·소속·서명 제출 (아래 3부 참조)
- [ ] 대시보드 UI의 독창적 요소 정리 (전문가 데모 시나리오에 포함될 화면 목록)

**전문가 검증 관련**

- [ ] 역학 전문가 데모용 시연 스크립트 작성 (5분 분량, 클릭 경로 명시)
- [ ] 17개 시도 지도 + 경보 SSE 흐름 화면 녹화 준비

---

### 박진영 (DevOps / QA) 담당 과제

**개발 (최종발표 전 — 가장 중요)**

- [ ] 커버리지 39% → 50% 달성 (W18 단기 목표)
  - `kafka_producer.py` 테스트 신규 작성 (현재 0%)
  - `pipeline/kowas_parser.py` 테스트 신규 작성 (현재 0%)
  - `pipeline/kowas_loader.py` 테스트 신규 작성 (현재 0%)
  - `backend/app/services/report_pdf.py` 보강 (현재 16%)
- [ ] `pyproject.toml` CI gate 36% → 45%로 상향
- [ ] `uis-backend.service` systemd 기동 (`sudo systemctl start uis-backend`)
- [ ] `uis-frontend.service` systemd 기동 (`sudo systemctl start uis-frontend`)
- [ ] K8s ingress·service YAML 작성 (Phase 4 GKE 준비)
- [ ] `tests/integration/test_e2e_rag_report.py` unskip (TODO W18)

**특허 관련 (가장 중요한 역할)**

- [ ] **오늘**: `github.com/zln02/urban-immune-system` PUBLIC/PRIVATE 확인
  - PUBLIC이면 최초 커밋 날짜 기록 → 12개월 특허 마감일 계산
  - 핵심 알고리즘 파일(`pipeline/scorer.py`, `ml/xgboost/model.py`)의 외부 노출 여부 검토
- [ ] KIPRIS 선행기술 조사 실시 (아래 3부 참조)
- [ ] 발명 공개 신고서에 이름·소속·서명 제출

**전문가 검증 관련**

- [ ] 시스템 SLA 리포트 작성: 최근 30일 uptime, 평균 응답시간, 에러율
- [ ] 감사 로그(`alert_reports` 테이블) 샘플 출력 → 전문가 패키지에 포함
- [ ] ISMS-P 풀 점검 완료 리포트 (docs/business/advisory/에 추가)

---

## 2부. 특허 가이드

### 우리 프로젝트 특허 가능성 판단

**결론: 출원 가능. 단, 공지 예외 12개월 시계가 돌고 있어 지금이 골든타임이다.**

#### 특허 가능한 핵심 요소

**1. 교차검증 게이트 방법론 (특허 가능성: 중상)**

`pipeline/scorer.py`의 게이트 B 로직이 핵심 청구 대상이다.

```
"비의료 이종 신호(약국 OTC구매·하수 바이러스농도·검색트렌드) N개 이상이
 동시에 기준값을 초과할 때에만 감염병 조기경보를 발령하는 방법 및 시스템"
```

이 구조는 오경보율(FAR)을 게이트 OFF 대비 65.8% 감소시켰다는 수치가 있다.
기존 시스템(WHO EIOS, CDC NWSS, BlueDot)은 단일 계층이거나 교차검증 게이트를 명시적으로 구현하지 않는다.

**2. 한국 특화 3계층 파이프라인 (특허 가능성: 중)**

- 네이버 쇼핑인사이트(OTC) + KOWAS(하수) + 네이버 데이터랩(검색) 자동 수집·정규화 파이프라인 구성 방법
- 주간 단위 자동화 수집 + TimescaleDB 적재 + 앙상블 경보 로직의 통합 구현

**3. 감사로그 내재화 경보 리포트 (특허 가능성: 중하)**

XAI 메타데이터 강제 기록 + RAG-LLM 면책고지 자동 삽입 구조

---

#### ⚠️ 공지 예외 기간 경고 (가장 중요)

한국 특허법 제30조: 발명자 본인이 공개한 날로부터 **12개월 이내 출원** 필수.
이 기간을 넘기면 신규성 상실로 특허 출원 불가능하다.

| 공개 행위 | 날짜 | 특허 마감일 |
|---|---|---|
| 한국능률협회 AI 공모전 수상 | 2026-03 (정확한 날짜 확인 필요) | 2027-03 이전 |
| GitHub 공개 저장소 (PUBLIC이면) | 최초 커밋 날짜 확인 필요 | 최초커밋일 + 12개월 |
| 중간 점검 발표 | **2026-05-07** | **2027-05-07** |

**결론**: 가장 빠른 공개일을 기준으로 출원 마감일이 결정된다.
지금 당장 시작해야 한다.

---

### 특허 출원 절차 (단계별)

#### Step 1. 발명 공개 신고서 작성 — 이번 주 필수

팀원 3명 전원이 서명해야 한다. 아래 항목을 문서로 작성한다.

```
[발명 공개 신고서 양식]

발명의 명칭 (국문):
  비의료 이종 신호 교차검증 기반 감염병 조기경보 시스템 및 방법

발명의 명칭 (영문):
  Infectious Disease Early Warning System and Method Based on
  Cross-validation of Heterogeneous Non-medical Signals

발명자:
  1. 박진영 (동신대학교 AI학과 / PM·ML Lead)
  2. 윤재영 (동신대학교 AI학과 / Data Engineer·Backend)
  3. 정욱현 (동신대학교 AI학과 / Frontend·UX·발표)

발명의 요약:
  약국 OTC 구매량·하수 바이러스 농도·인터넷 검색 트렌드 등
  3계층 비의료 신호를 XGBoost+Autoencoder로 앙상블하여
  임상 확진 보고보다 평균 6.76주 선행하는 감염병 조기경보를 발령.
  2개 이상 계층이 동시에 임계값을 초과할 때에만 경보 발령하는
  교차검증 게이트를 도입하여 오경보율 65.8% 감소.

공지 경위:
  1. 2026-03-__ : 한국능률협회 AI 아이디어 공모전 대상 수상 (공개 발표)
  2. 2026-__-__ : GitHub 저장소 최초 공개 (확인 후 날짜 기입)
  3. 2026-05-07 : 동신대학교 중간 점검 발표

발명자 서명:  (각자 날인)
작성일: 2026-05-10
```

---

#### Step 2. 산학협력단(TLO) 발명 신고 — 2주 이내

**신고 기관**: 동신대학교 산학협력단 (또는 기술이전센터)  
**담당 부서**: 지식재산팀 (교학처 내)

**신고 시 제출 서류**:
1. 발명 공개 신고서 (Step 1에서 작성한 문서)
2. 발명 설명서 (기술 요약 5~10페이지 — `docs/business/advisory/10_surveillance_bulletin.pdf` 활용 가능)
3. 공지 증거 자료 (공모전 수상 확인서, 발표 자료, GitHub URL)

**기대 효과**:
- 대학이 특허 출원비(출원료 약 52만원 + 심사청구료) 부담 가능
- 출원인 = 대학교 or 대학+학생 공동 (협의 필요)
- 직무발명 해당 여부 및 권리 귀속 사전 합의 필수

---

#### Step 3. KIPRIS 선행기술 조사 — 2주 이내 (박진영 담당)

**사이트**: https://www.kipris.or.kr (한국특허정보원)

**검색 키워드 (국문)**:
- "감염병 조기경보 비의료 신호"
- "하수 감시 인플루엔자 조기경보"
- "OTC 구매 트렌드 감염병"
- "다계층 앙상블 감염병 예측"

**검색 키워드 (영문, Google Patents)**:
- "wastewater surveillance influenza early warning system"
- "multi-layer heterogeneous signal ensemble alert gate"
- "OTC sales trend infectious disease prediction"

**확인할 선행기술 (이미 알려진 것)**:
- Lee et al. 2023 (Nature) — OTC × Wastewater 2계층 융합
- Deng et al. 2025 (Frontiers in Public Health) — 2-Layer EWS
- CDC NWSS (운영 시스템)

---

#### Step 4. 네이버 API 약관 서면 확인 — 5월 내 (박진영 담당)

B2G 납품 전 네이버 개발자센터에 서면 질의:
"쇼핑인사이트·데이터랩 API 결과를 집계 지수로 변환해 보건당국에 납품하는 것이 재판매 금지 조항에 해당하는지"

---

## 3부. 전문가 검증 가이드

### 검증 준비 현황

**현재 갖춰진 것 (강점)**:
- `ml/reproduce_validation.py` — 시드 고정, 1줄 재현
- `ml/model_card.md` — Hugging Face 표준 Model Card
- `docs/business/advisory/` — 9개 전문가용 자료 패키지
- `docs/business/advisory/20_walk_forward_backtest.pdf` — 검증 리포트
- `docs/business/advisory/22_dpia_draft.md` — DPIA 초안
- `docs/business/advisory/10_kdca_request_letter.md` — KDCA 자문 공문 초안

**전문가가 물어볼 취약점 (선제 대응 준비)**:
1. "왜 26주 단일 시즌 데이터밖에 없나?" → "2025-2026 인플루엔자 시즌 1회. Phase 3에서 2시즌 이상 누적 계획"
2. "L1·L3가 전국 단일값인데 왜 17개 지역 경보를 내나?" → "Phase 3에서 HIRA OpenAPI 지역 분리 예정. 현재는 보수적 전국 기준 broadcast"
3. "L2 Granger p=0.267이면 유의하지 않지 않나?" → "단독은 미유의, 3계층 composite p=0.021로 유의. 이것이 게이트 B의 근거"

---

### 검증 기관 및 신청 방법

#### 기관 1. 질병관리청(KDCA) 역학조사과

**담당 부서**: 감염병위기대응국 감염병감시과  
**연락처**: 043-719-7700 (충북 청주 오송)  
**신청 방법**:
1. `docs/business/advisory/10_kdca_request_letter.md` 를 공문 형식으로 출력·날인
2. 이메일 (kdca@kdca.go.kr) 또는 우편 발송
3. **필수 문구**: "비공개 자문 요청 — 본 자료는 학술·정책 연구 목적으로만 활용 바라며 외부 공개 시 사전 동의를 구합니다"
4. 특허 출원 전까지 핵심 알고리즘(`scorer.py` 구현 상세)은 제외하고 발송

**제출 패키지** (docs/business/advisory/ 내):
- `01_executive_summary.pdf`
- `10_surveillance_bulletin.pdf`
- `20_walk_forward_backtest.pdf`
- `ml/model_card.md` (출력본)

---

#### 기관 2. 국립감염병연구소 (NIID, 오송)

**역할**: KDCA 산하, 실험·역학 연구 전문  
**접근 방법**: 소속 대학 지도교수를 통한 공동연구 제안서 제출  
**제안 내용**: "비의료 신호 기반 조기경보 AI 모델 — 역학적 타당성 검토 공동연구"

---

#### 기관 3. 대학 역학·감염병 교수진

**접근 방법**:
1. 전남대학교 의과대학 감염내과 or 예방의학교실 교수에게 이메일 발송
2. 내용: "연구 프로토타입 자문 요청 — 모델 역학적 타당성 검토"
3. `docs/business/advisory/10_surveillance_bulletin.pdf` + `model_card.md` 첨부

**이점**: 가장 빠르게 피드백 받을 수 있음. 논문 공동저자 또는 사사 가능성.

---

#### 기관 4. WHO 서태평양지역사무소 협력센터

**접근 방법**: 국내 WHO 협력센터(서울대병원 WHO 협력센터) 통해 간접 접촉  
**현실적 타임라인**: 6월 최종발표 이후 권고 (현재 단계에서는 우선순위 낮음)

---

### 전문가 검증 비밀유지 절차

KDCA 또는 외부 전문가에게 자료 발송 전:

1. 공문에 "비공개 자문 요청" 명시 (발명 공개 신고서 작성 후 진행)
2. 핵심 알고리즘 코드(`scorer.py`, `model.py`)는 포함하지 않음
3. 결과·성능 수치와 방법론 개요만 포함
4. 구두 설명은 가능하나 소스코드 공유 금지

---

## 4부. 팀원별 최종 체크리스트

### 윤재영 체크리스트

```
개발
[ ] advisory_pdf.py 테스트 작성 (커버리지 0% → 50%+)
[ ] report_pdf.py 테스트 보강 (16% → 50%+)
[ ] prediction_service.py ML fallback 로직 추가
[ ] alert_service.py 커버리지 40% → 70%

특허
[ ] 발명 공개 신고서 서명 제출 (이번 주)

전문가 검증
[ ] Swagger 문서 스크린샷 → advisory 패키지 추가
[ ] p95 응답시간 측정 리포트 작성
```

### 정욱현 체크리스트

```
개발
[ ] slides-animated 삭제 파일 커밋 (오늘)
[ ] README.md Next.js 버전 표기 수정
[ ] api.ts 분산 fetch 통합
[ ] 컴포넌트 스모크 테스트 1개 추가

특허
[ ] 발명 공개 신고서 서명 제출 (이번 주)

전문가 검증
[ ] 역학 전문가 데모용 5분 시연 스크립트 작성
[ ] 대시보드 화면 녹화 (경보 SSE 흐름 포함)
```

### 박진영 체크리스트

```
개발 (최우선)
[ ] kafka_producer.py 테스트 신규 작성
[ ] kowas_parser.py 테스트 신규 작성
[ ] kowas_loader.py 테스트 신규 작성
[ ] CI gate 36% → 45%로 상향
[ ] uis-backend.service, uis-frontend.service systemd 기동

특허 (오늘 필수)
[ ] github.com/zln02/urban-immune-system PUBLIC 여부 확인
[ ] 최초 커밋 날짜 기록 → 12개월 마감일 계산
[ ] KIPRIS 선행기술 조사 실시
[ ] 발명 공개 신고서 서명 제출 (이번 주)

전문가 검증
[ ] 시스템 SLA 리포트 (30일 uptime, 응답시간, 에러율)
[ ] ISMS-P 점검 완료 리포트 작성
[ ] 감사 로그 샘플 → advisory 패키지 추가
```

---

## 부록. 타임라인 요약

| 시점 | 해야 할 일 |
|---|---|
| **오늘 (5/10)** | GitHub 공개 여부 확인, develop push, 삭제 파일 커밋 |
| **이번 주 (5/14까지)** | 발명 공개 신고서 5명 서명 완료 |
| **2주 이내 (5/24까지)** | 산학협력단 발명 신고, KIPRIS 선행기술 조사, KDCA 자문 공문 발송 |
| **5월 내** | 네이버 API 약관 서면 확인, 커버리지 45% 달성 |
| **최종발표 전 (6월 초)** | 커버리지 60%, 전문가 검증 피드백 반영, 특허 출원 진행 여부 결정 |
| **납품 목표** | 커버리지 70%, K8s 배포 완료, ISMS-P 점검 완료 |

---

*본 문서는 박진영(PM)이 작성하였으며, 팀원 전원에게 공유됩니다.*  
*특허 관련 사항은 변리사 또는 산학협력단과 최종 확인 후 진행하세요.*
