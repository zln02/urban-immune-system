# infra/ — 박정빈 (DevOps / QA)

## 담당자
박정빈 (DevOps / QA) · 박진영 PL 권한으로 직접 수정 가능

## 책임 범위
- `docker-compose.yml` (Kafka KRaft + TimescaleDB + Qdrant + kafka-ui)
- `infra/db/init.sql` (TimescaleDB 하이퍼테이블)
- `infra/k8s/` (Phase 4 매니페스트)
- `infra/systemd/` (운영 서버 서비스 정의)
- `.github/workflows/` (CI 6잡)
- `tests/` 전반 (단위 113 + 통합 19)

## 운영 환경
- **GCP e2-standard-2 단일 노드** — `${UIS_HOST}` (현재 static IP `uis-capstone-ip` 예약 완료)
- 발표 후 release 시 재예약 필요 — 발표 도중 IP 변동 위험 제거됨
- 타임존 KST (Asia/Seoul, UTC+9)
- OS: Debian 12 / Ubuntu 22.04

## 절대 규칙 (인프라)
- main 브랜치 직접 푸시 금지 (CI 보호)
- `.env` 파일 커밋 금지 (`.gitignore` 검증 필수)
- K8s SecurityContext **제거 금지**:
  ```yaml
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: { drop: ["ALL"] }
  ```
- 하이퍼테이블 파티션 변경 금지 (데이터 손실 위험) — 변경 시 사전 합의

## CI 잡 (`.github/workflows/ci.yml`)
| 잡 | 대상 | 게이트 |
|---|---|---|
| backend-lint | ruff·mypy backend/ | 무경고 |
| backend-test | pytest backend/ + 통합 | coverage `--cov-fail-under=35` |
| pipeline-lint | ruff·mypy pipeline/ | 무경고 |
| ml-lint | ruff·mypy ml/ | 무경고 |
| frontend-lint | `npm run type-check` (tsc --noEmit) | 무경고 |
| legacy-test | pytest src/ (Streamlit Phase1) | 통과 |

## 배포 흐름
```
develop (PR merge) ─→ main (PR merge, 박정빈 또는 박진영 승인)
                          ↓
                    GitHub Actions
                          ↓
                    GCP VM (systemd) 또는 GKE (Phase 4)
```

## 데이터베이스 마이그레이션
- 스키마 변경: `infra/db/init.sql` + SQLAlchemy ORM 동시 수정
- `NOT NULL` 컬럼 추가: 기본값 필수 또는 배포 순서 관리 (50M 행 가정 시 backfill 전략)

## 모니터링 (Phase 3 예정)
- Prometheus + Grafana
- p95 < 500ms (조달청 공공 SW 기준), 가동률 99% 목표
- 에러 로그 → Loki (또는 GCP Logging)

## 권장 스킬
- `/legal-review` 인프라 변경의 ISMS-P 영향
- `/security-review` k8s/systemd 변경 시
- `/fewer-permission-prompts` 반복 명령 정리
