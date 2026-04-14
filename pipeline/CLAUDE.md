# pipeline/ 에이전트 — 이우형(Data Engineer) 전용

## 🎯 정체성
3-Layer(약국OTC·하수바이오마커·검색트렌드) + AUX(기상) 데이터 수집 → 정규화 → Kafka 토픽 발행 → TimescaleDB 적재의 **데이터 공장장**. 납품 기준은 **수집 성공률 ≥ 99%, 적재 지연 < 5분**.

## 💬 말 거는 법 (이우형이 하는 예시 지시)
- "Kafka Consumer 구현해서 `layer_signals` 테이블에 적재 완성"
- "KOWAS PDF 자동 다운로드 스케줄러 완성 (`wastewater.py` 실데이터)"
- "네이버 API 429 응답에 exponential backoff 붙여"
- "수집 이력 로그 테이블 추가 (audit용)"
- "APScheduler 크론 엔트리 정리"

## 🛠 Skills
- `/commit`, `/review-pr`, `/simplify`
- 커스텀(후속): `/pipeline-smoke` — collectors 1회 실행 · `/pipeline-monitor` — Kafka UI 열기(`:8080`)
- Agent 병렬: 수집기별 재시도 정책 리팩터는 Haiku 서브에이전트 병렬

## 🔌 MCP 연결
- **GitHub**: PR
- **Notion**(선택): 데이터 원천·API 키 관리 페이지

## 🌿 GitHub 연계
- 브랜치: `feature/pipeline-*`
- PR 체크리스트:
  - [ ] `pytest tests/test_normalization.py` 통과
  - [ ] `ruff check pipeline/` 통과
  - [ ] 새 API 키 `.env.example` 에 추가 (값은 비움)
  - [ ] 수집 실패 재시도(exp backoff) 포함
  - [ ] Kafka 토픽 변경 시 `kafka_producer.py` + consumer 양쪽 반영
- CI Job: `pipeline-lint`

## 🧠 자동 메모리
- 수집기 API 쿼터·제한 (예: 네이버 1000회/일)
- 정규화 min/max 값 기준일
- PDF 파서 실패 패턴
저장 제외: API 키·Secret.

## 📦 상용화 기여
- **B2G 산출물**: 데이터 원천 계약서, 수집 SLA, 수집 감사 로그
- **ISMS-P**: 외부 API 호출 로깅·개인정보 미수집 증빙
- **운영 매뉴얼**: 수집 실패 시 대응 절차 (`docs/operations.md` 섹션)

## ✅ Definition of Done
1. `pytest` 통과
2. `ruff check pipeline/` 0 error
3. `python -m pipeline.collectors.scheduler` 또는 단일 수집기 실행 OK
4. Kafka UI(`:8080`)에서 메시지 발행 확인
5. TimescaleDB `layer_signals` 에 해당 row insert 확인

## 📍 핵심 파일
- `pipeline/collectors/kafka_producer.py` — Kafka KRaft 프로듀서 (L1/L2/L3/AUX)
- `pipeline/collectors/scheduler.py` — APScheduler 크론
- `pipeline/collectors/otc_collector.py` — L1 네이버 Shopping Insight
- `pipeline/collectors/search_collector.py` — L3 네이버 DataLab
- `pipeline/collectors/weather_collector.py` — AUX 기상청 KMA
- `pipeline/collectors/wastewater.py` — L2 KOWAS PDF
- `pipeline/collectors/normalization.py` — Min-Max 0~100 정규화

## 🚧 Phase 2 TODO
- [ ] Kafka Consumer → TimescaleDB 적재 완성
- [ ] KOWAS PDF 자동 다운로드·파싱
- [ ] exponential backoff 재시도
- [ ] 수집 이력 감사 테이블(`collection_audit`)
