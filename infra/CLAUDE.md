# infra/ 에이전트 — 박정빈(DevOps/QA) 전용

## 🎯 정체성
인프라·CI/CD·K8s·DB 스키마·백업의 **운영 책임자**. 납품 시 **장애 복구 절차(RTO/RPO)**, **K8s GKE 배포**, **CI 6 Job 안정성**을 보증한다.

## 💬 말 거는 법 (박정빈이 하는 예시 지시)
- "`init.sql` 에 인덱스 추가 + 마이그레이션 스크립트 작성"
- "K8s `ml-deployment.yaml` 리소스 limits 재조정"
- "docker compose 에 prometheus + grafana 추가 (모니터링)"
- "CI `backend-test` Job 타임아웃 원인 파악"
- "주 1회 pg_dump 크론 설정"

## 🛠 Skills
- `/commit`, `/review-pr`, `/simplify`
- 커스텀(후속): `/deploy-check` — K8s dry-run · `/infra-up` — `docker compose up -d` · `/infra-down` — 정지

## 🔌 MCP 연결
- **GitHub**: Actions 로그·release·secrets 확인
- **Notion**(선택): 장애 포스트모템

## 🌿 GitHub 연계
- 브랜치: `feature/infra-*`, `hotfix/*`
- PR 체크리스트:
  - [ ] `kubectl apply --dry-run=client -f infra/k8s/*.yaml` OK
  - [ ] `docker compose config` 파싱 통과
  - [ ] `init.sql` 변경 시 마이그레이션 SQL 동봉
  - [ ] CI workflow 수정 시 `act` 또는 테스트 커밋 선행
  - [ ] secrets 하드코딩 0건
- CI Job: 6개 전체 + `deploy.yml`(GKE asia-northeast3)

## 🧠 자동 메모리
- 배포한 버전·이미지 태그
- K8s 리소스 사이징 이력
- DB 스키마 마이그레이션 이력
저장 제외: GCP 서비스계정 키, WIF 설정 값.

## 📦 상용화 기여
- **B2G 산출물**: 운영 매뉴얼, 장애 대응 절차, 백업·복구 절차, 보안 점검 보고서 기반
- **ISMS-P**: 접근 통제, 백업, 로그 보존(1년)
- **SLA**: 가동률 99.5%, RTO < 1h, RPO < 1h

## ✅ Definition of Done
1. `sudo docker compose up -d` 모든 서비스 `healthy`
2. `sudo docker compose ps` healthcheck 통과
3. K8s 매니페스트 `kubectl apply --dry-run` OK
4. CI 6 Job 통과
5. `init.sql` 변경 시 롤백 SQL 준비

## 📍 핵심 파일
- `infra/db/init.sql` — TimescaleDB 하이퍼테이블 3개 + 연속집계
- `infra/k8s/namespace.yaml`
- `infra/k8s/backend-deployment.yaml`
- `infra/k8s/pipeline-deployment.yaml`
- `infra/k8s/ml-deployment.yaml`
- `../docker-compose.yml` — Kafka+TSDB+Qdrant+KafkaUI
- `../.github/workflows/ci.yml` (6 Job)
- `../.github/workflows/deploy.yml` (GKE)

## 🚧 Phase 2 TODO
- [ ] frontend K8s 매니페스트 추가
- [ ] Prometheus + Grafana 모니터링 스택
- [ ] pg_dump 주간 백업 크론 (→ GCS)
- [ ] HPA (Horizontal Pod Autoscaler)
- [ ] GKE Workload Identity 최종화
