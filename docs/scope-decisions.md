# 스코프 결정 — 캡스톤 기말까지 뭐 포기할지

> 박진영 결정 · 2026-04-22 · 냉정한 현실 기반

## 🎯 캡스톤 기말 목표 = **L-Demo (A 수준)**
- Streamlit 5탭 로컬 데모 · TFT 합성 학습 체크포인트 · 네이버 API 실데이터 1회 수집 · LLM 리포트 실 API 호출
- **포기**: L-Production (ISMS-P·24시간·GKE) — 졸업 후 1인 창업 트랙

## 🔴 **지금 당장 포기할 것 Top 3**

### 1. K8s GKE 배포
- **이유**: GCP 서비스 계정·WIF·Ingress·TLS 세팅이 6주 안 불안정
- **대안**: "Docker Compose 로컬 검증 완료 · GKE 매니페스트는 설계 단계로 작성" → 발표 슬라이드 1장에 "Phase 5 실행" 선언
- **영향**: 심사 감점 없음. 오히려 "선택과 집중" 어필

### 2. Next.js `frontend/` 프로덕션 UI
- **이유**: Phase 1 Streamlit 이 이미 발표용으로 충분. Next.js 는 백엔드 실 API 연결까지 필요 → 6주 내 완성 시간 부족
- **대안**: "Phase 2 는 B2G 납품 시 착수, 현재 Streamlit 에 디자인 검증 집중" → 발표에서 **Streamlit 이 Phase 1 으로 의도된 전략** 임을 선명히
- **이슈 #56 (Phase B Next.js)** → **pending 유지하되 기말 이후로 연기**

### 3. Qdrant RAG 벡터 DB 임베딩
- **이유**: KDCA 문서 수집·전처리·임베딩이 별도 3-4일 작업. 현재 RAG 구조만 있고 콘텐츠 0
- **대안**: KDCA 주간 보고 텍스트 5-10건을 Python 리스트에 하드코딩 → 프롬프트에 직접 주입 = **가짜 RAG 데모**. 발표에서 "RAG 파이프라인 구조 + 기초 콘텐츠 로 작동, 실제 Qdrant 임베딩은 Phase 3" 투명 선언
- **영향**: 실 Qdrant 없어도 LLM 리포트 생성 가능

---

## 🟡 **축소할 것 (기능 유지하되 단순화)**

### 4. Kafka → **직접 INSERT** 로 단순화 (옵션)
- **문제**: Kafka Consumer 구현이 학부생 난이도 높음. offset·재시작·중복 적재 디버깅
- **대안**: 수집기에서 `asyncpg` 로 TimescaleDB 직접 INSERT → Kafka 는 **"설계로 남기고 실제 구현은 Phase 5"** 선언
- **판단**: 이우형이 시도해서 1일 안에 안 되면 대안으로 전환

### 5. TFT → **LightGBM 베이스라인** 먼저
- **문제**: TFT 학습은 25구 × 2년 데이터 필요. 단일 시즌 52주로는 수렴 의심. CPU 느림
- **대안**: LightGBM (이미 의존성 있음) + lag 피처 베이스라인 → 1일 안에 체크포인트 확보. TFT 는 "시도 중" 로 발표
- **판단**: D-7 까지 LightGBM 먼저 확정, TFT 는 시간 남으면 추가

### 6. KOWAS 자동화 → **수동 CSV 입력**
- **문제**: `wastewater.py` 정규식이 실제 PDF 포맷과 안 맞을 확률 85%
- **대안**: KOWAS 공개 PDF 수동 다운로드 → Excel 에서 구조화 → CSV 저장 → 직접 INSERT
- **발표**: "Phase 3 에서 자동 크롤러 완성" 선언

---

## ✅ **유지·집중할 것 (기말까지 반드시)**

| 기능 | 이유 |
|---|---|
| Streamlit 5탭 안정화 | 발표 주력, 이미 완성도 높음 |
| P0 수치 정직성 (F1/MCC/AUPRC 실측) | ✅ 완료 (합성 데이터 기반, 재현 가능) |
| FastAPI `/health` `/signals/latest` | ✅ config 수정 완료 · 실 DB 쿼리 W18 (이슈 #3) |
| LightGBM 체크포인트 | 1일 투자, 성과 확실 |
| LLM 리포트 API 호출 | OpenAI/Anthropic 키만 있으면 즉시 |
| Okabe-Ito 색맹 팔레트 | ✅ 완료 |
| 포트폴리오 (ADR·TS·FAQ) | ✅ 6건 기록, 기말까지 15건 목표 |
| 팀원 4명 PR 최소 1건씩 | W18 필수 (교수님 원맨쇼 반박) |

---

## 📊 새 로드맵 (축소 반영)

### Phase 1 (~4/30 중간발표)
- ✅ Streamlit 대시보드 완성도
- ✅ P0 수치 재현 가능
- 🎯 팀원 4명 첫 PR 머지
- 🎯 네이버 API 실데이터 1회 수집 (이우형)
- 🎯 LightGBM 체크포인트 (박진영)

### Phase 2 (5-6월 기말)
- 🎯 Kafka Consumer OR 직접 INSERT 로 실데이터 1시즌 적재
- 🎯 TFT 재시도 (성공 시 추가, 실패 시 LightGBM 유지)
- 🎯 LLM RAG 하드코딩 콘텐츠 5건
- 🎯 ngrok 터널 or Cloud Run 소규모 공개 URL
- 🎯 포트폴리오 authored-by 팀원 1편씩

### Phase 3+ (졸업 후)
- 법인 설립 · KOWAS MOU · 네이버 Enterprise
- Qdrant RAG 실 임베딩
- Next.js 프로덕션 UI
- K8s GKE · ISMS-P · 조달청 등록

---

## 🎤 발표에서 **이 축소를 어떻게 말할지**

### ❌ 하지 말 것
- "시간이 없어서 안 했어요" (변명)
- "K8s 도 곧 될 거예요" (근거 없는 약속)

### ✅ 이렇게 말할 것
> "저희는 캡스톤 6주 일정에서 **'진짜 돌아가는 것'** 과 **'설계만 된 것'** 을 명확히 구분했습니다. Streamlit 대시보드 + FastAPI + LightGBM + 네이버 API 수집은 **실제 동작**시켰고, K8s GKE · Next.js 프로덕션 UI · Qdrant RAG 임베딩은 **설계·뼈대는 완성**하되 실제 구현은 Phase 3 (창업 트랙) 로 투명하게 분리했습니다. 이 의사결정 자체가 `docs/portfolio/decisions/ADR-XXX` 에 기록되어 있습니다."

→ **스코프 관리 역량** 어필 기회로 전환.

---

## 📝 팀 공지 문구 (Discord 복사용)

```
@everyone 스코프 결정 공지 (2026-04-22)

현재 범위에서 3개 기능 '포기 아닌 연기' 선언:
1. K8s GKE 배포 → 설계만, Phase 5
2. Next.js 프로덕션 UI → 기말 이후
3. Qdrant RAG 실 임베딩 → 하드코딩으로 데모

집중할 것:
- Streamlit 완성도
- 팀원 각자 PR 1건 (이슈 #3-6)
- LightGBM 체크포인트
- LLM 리포트 실 API 호출

상세: docs/scope-decisions.md
```

---

## 🔗 연관 문서
- `docs/meeting-notes/midterm-9day-sprint.md` — 9일 일자별 계획
- `docs/team-explainer.md` — 프로젝트 쉬운 설명
- `docs/portfolio/decisions/` — ADR 기록
