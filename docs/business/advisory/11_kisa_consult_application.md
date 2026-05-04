# 한국인터넷진흥원 (KISA) — ISMS-P 사전 컨설팅 신청서

**제목**: AI 기반 감염병 조기경보 시스템 ISMS-P 사전 의견 자문 요청

**신청일**: 2026년 5월 2일
**신청 주체**: 동신대학교 컴퓨터공학과 캡스톤 디자인 팀 (학생 PoC)
**대표자**: 박진영 (PM, wlsdud5035@gmail.com)
**지도교수**: (캡스톤 지도교수 성함·서명)
**시스템명**: Urban Immune System (UIS) v0.4

---

## 1. 신청 배경

저희 팀이 캡스톤 디자인 과제로 개발 중인 **Urban Immune System** 은 향후 B2G 납품 (질병관리청 · 광역 자치단체 보건환경연구원) 을 목표로 하고 있습니다.

발표·PoC 단계 이전에 ISMS-P 인증 적정성 및 개인정보보호법 적합성 사전 의견을 받기 위해 자문을 요청드립니다.

## 2. 시스템 개요

### 2.1 처리하는 데이터

| 데이터 | 출처 | 가명·익명 처리 | 저장 위치 |
|---|---|---|---|
| L1 약국 OTC 트렌드 지수 | 네이버 쇼핑인사이트 API | **시·도 단위 집계** (개인 식별 불가) | TimescaleDB · 7일 보존 |
| L2 하수 바이러스 농도 | KOWAS 공개 PDF | 환경 데이터 (개인정보 비해당) | 동일 |
| L3 검색 트렌드 지수 | 네이버 데이터랩 API | **시·도 단위 집계** | 동일 |
| 기상 (기온·습도) | 기상청 KMA API | 환경 데이터 | 동일 |

→ **개인정보 직접 처리 없음**. 모든 입력은 출처 단계에서 시·도 단위 집계 지수만 수신.

### 2.2 출력

- 시·도별 종합 위험점수 (0-100) + 경보 레벨 (GREEN·YELLOW·ORANGE·RED)
- AI 보조 리포트 (Claude Sonnet 4.6 RAG, KDCA 9섹션 포맷, 면책 조항 강제 삽입)
- 대상: 보건당국 의사결정 보조 (인간 전문가 검토 전제)

## 3. 보안 통제 현황

### 3.1 적용 통제 (구현 완료)

| 통제 항목 | 구현 상태 | 코드 위치 |
|---|---|---|
| K8s Pod 보안 컨텍스트 (`runAsNonRoot: true`) | ✅ | `infra/k8s/*-deployment.yaml` |
| 권한 상승 차단 (`allowPrivilegeEscalation: false`) | ✅ | 동일 |
| 읽기 전용 루트 파일시스템 | ✅ | 동일 |
| 모든 Linux capability 제거 (`drop: ['ALL']`) | ✅ | 동일 |
| 환경변수 검증 (Pydantic Settings) | ✅ | `backend/app/config.py` |
| API 키 하드코딩 차단 (pre-commit `detect-private-key`) | ✅ | `.pre-commit-config.yaml` |
| Kafka 메시지 손실 방지 (`acks=all` `retries=3`) | ✅ | `pipeline/collectors/kafka_producer.py` |
| SSE 스트리밍 (단방향, 쿠키 인증 미사용) | ✅ | `backend/app/api/alerts.py` |
| AI 면책 조항 강제 삽입 (ISMS-P 2.9 / EU AI Act 13·14) | ✅ | `ml/rag/report_generator.py` |
| 감사 로그 (`triggered_by`, `trigger_source`) | ✅ | `infra/db/init.sql:alert_reports` |

### 3.2 미구현 (Phase 2 ~ Phase 3 예정)

- DB 컬럼 단위 암호화 (AES-256)
- KMS 키 관리 (현재 .env 평문)
- ISMS-P 인증 신청 (현재 25% 준비)

## 4. 자문 의뢰 사항

1. **개인정보 비해당성 확인**
   - 시·도 단위 집계 지수만 처리하는 본 시스템이 개인정보보호법 제2조 1호 ("살아 있는 개인에 관한 정보") 비해당 판정 가능 여부

2. **ISMS-P 적용 범위 권고**
   - 본 시스템 규모(연 동시접속 ~50명 · 데이터 26주 · 17지역)에 ISMS-P 신청 시 권고되는 통제 우선순위

3. **AI 면책 조항 적정성**
   - RAG 리포트에 강제 삽입되는 면책 조항 (ISMS-P 2.9 / EU AI Act 13·14조 인용) 이 의료기기법 SaMD 비해당 주장의 근거로 충분한지

4. **네이버 API 재판매 이슈**
   - 네이버 쇼핑인사이트·DataLab API 응답을 직접 저장 없이 0-100 정규화 지수로만 변환·저장하는 방식이 약관 (재판매 금지 조항) 위반 여지가 있는지

## 5. 첨부 자료

| 파일 | 내용 |
|---|---|
| `21_architecture_summary.md` | 시스템 구조 + 데이터 흐름 |
| `22_dpia_draft.md` | 개인정보 영향평가 (DPIA) 초안 |
| `40_code_snapshot.tar.gz` | 보안 컨트롤 핵심 코드 스냅샷 |
| `30_reproduce_command.txt` | 재현 가능성 검증 |

## 6. 회신 요청

가능한 시점에 서면·이메일 회신 부탁드립니다. 정식 ISMS-P 인증 신청은 Phase 3 (2027년 상반기) 예정이며, 본 사전 의견을 Phase 2 (2026년 하반기) 보안 강화 우선순위 결정에 활용하겠습니다.

---

박진영 드림
동신대학교 컴퓨터공학과
2026년 5월 2일
