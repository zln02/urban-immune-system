# MLOps Cron Runbook — UIS 운영 자동화

> **적용 시점**: 2026-05-08 (중간발표 다음날) 권장
> **담당**: 박진영 (PM/ML Lead)
> **검토**: 박정빈 (DevOps/QA)

## 배경

`pipeline/collectors/scheduler.py` 가 APScheduler 단일 프로세스(nohup)로 가동 중이었음 (PID 1461998, 4/29 ~). 프로세스 사망 시 모든 수집·스코어링·리포트 정지. 본 runbook 의 P0+P1 자동화로 다음을 보장한다:

- **24/7 무인 운영** — systemd auto-restart + 5분 cron liveness 이중 안전망
- **데이터 손실 방지** — 매일 03:00 KST DB 백업 + 14일 보관
- **품질 회귀 감지** — 매월 1일 backtest 재실행 + F1 회귀 자동 Issue
- **운영 가시성** — 매일 08:00 KST freshness check + stale 시 자동 Issue

## 자동화 잡 목록

### systemd 유닛 (3개)

| 유닛 | 기능 | Restart |
|------|------|---------|
| `uis-scheduler.service` | APScheduler 8 잡 (L1·L2·L3·AUX 수집, scoring, reports, KCDC) | on-failure 15s |
| `uis-backend.service` | FastAPI :8001 (REST API + SSE) | on-failure 10s |
| `uis-frontend.service` | Next.js :3000 (production build) | on-failure 10s |

### crontab 잡 (9건)

| 우선순위 | 시각 (KST) | 잡 | 영향 |
|---|---|---|---|
| **P0** | `*/5 * * * *` | scheduler liveness — 죽으면 systemctl restart | 데이터 수집 단절 0초 보장 |
| **P0** | `0 3 * * *` | `pg_dump → backups/uis-YYYY-MM-DD.sql.gz` (14d 보관) | 손상 시 24h 이내 복구 가능 |
| **P0** | `0 8 * * *` | `freshness_alert.sh` — stale 시 GitHub Issue | 품질 가시성 |
| **P1** | `0 11 * * mon` | L1·L3 수집 실패 재시도 (월 09:00 후 2시간 buffer) | 주간 데이터 누락 방지 |
| **P1** | `0 12 * * tue` | KOWAS 다운로드 실패 백업 | L2 누락 방지 |
| **P1** | `0 3 * * sun` | 로그 회전 (7d 압축, 30d 삭제) | 디스크 누수 방지 |
| **P1** | `0 2 1 * *` | TFT 재학습 (26주 누적) | 모델 신선도 |
| **P1** | `0 3 1 * *` | 17 지역 backtest 재실행 | 성능 추적 |
| **P1** | `30 3 1 * *` | F1 회귀 감지 — Δ ≤ -0.05 시 P0 Issue | 모델 드리프트 조기 탐지 |

## 설치

```bash
# 1) 미리보기 (안전, 권장 첫 실행)
bash scripts/setup_cron.sh --dry-run

# 2) 실제 설치 (sudo 필요)
bash scripts/setup_cron.sh --install

# 3) 점검
sudo systemctl status uis-scheduler uis-backend uis-frontend
crontab -l | grep -A1 "UIS"
```

## 검증

```bash
# 5분 후 liveness cron 동작 확인
journalctl --user -u uis-scheduler -f --since "10 minutes ago"

# DB 백업 잡 수동 트리거
pg_dump -d urban_immune | gzip > backups/uis-test.sql.gz
ls -lh backups/

# Freshness alert 수동 실행 (Issue 생성 테스트 — 실제 Issue 만들지 않으려면 GH_REPO 미설정)
bash scripts/freshness_alert.sh

# F1 회귀 시뮬레이션 (BASELINE_F1 임의 상향)
BASELINE_F1=0.95 bash scripts/check_f1_regression.sh
```

## 제거 / 롤백

```bash
bash scripts/setup_cron.sh --uninstall
```

systemd 유닛 정지·삭제 + crontab UIS 라인 제거. DB 백업본은 보존됨.

## 운영 리스크 / 알려진 이슈

| 리스크 | 완화책 |
|---|---|
| sudo 권한 없는 사용자가 cron `systemctl restart` 실행 | sudoers `wlsdud5035 ALL=(ALL) NOPASSWD: /bin/systemctl restart uis-*` 추가 (별도 PR) |
| GCP ephemeral IP 변경 (2026-04-29 1회 발생) | static IP reserve 권장 — `gcloud compute addresses create uis-prod` |
| `next build` 실패 시 frontend 재시작 무한 루프 | `RestartSec=10` + `Restart=on-failure` 로 일정 buffer. 5회 연속 실패 시 systemd 자동 차단 |
| TFT 재학습 GPU 메모리 OOM | `train_real.py` D-5 안정화 설정 (hidden_size 32) 로 CPU 가능. epoch 50 ≈ 30분 (e2-standard-2) |
| F1 베이스라인 시간에 따라 자연 변동 | 분기별 `BASELINE_F1` 재설정 + Decisions Log 기록 |

## ISMS-P 관련

- **2.7.1 시스템 운영**: systemd `NoNewPrivileges`, `ProtectSystem=full`, `PrivateTmp=true` 적용
- **2.9.1 변경 관리**: cron 변경은 `git log scripts/setup_cron.sh` 로 추적
- **2.6.1 백업·복구**: pg_dump 14일 보관 + 분기별 복원 테스트 권장
- **3.4.1 개인정보 파기**: 백업 14일 자동 삭제 (`find -mtime +14 -delete`)

## 참고 파일

- `infra/systemd/uis-scheduler.service` (기존)
- `infra/systemd/uis-backend.service` (신규)
- `infra/systemd/uis-frontend.service` (신규)
- `scripts/setup_cron.sh` (신규)
- `scripts/freshness_alert.sh` (신규)
- `scripts/check_f1_regression.sh` (신규)
- `scripts/check_data_freshness.sh` (PR #39, 기존)
- `pipeline/collectors/scheduler.py` (APScheduler, 변경 없음)

## 변경 이력

| 일자 | 내용 | 담당 |
|---|---|---|
| 2026-05-03 | 초기 작성 (P0+P1 9건 + systemd 3 유닛) | 박진영 |
| 2026-05-08 (예정) | 실서버 적용 (`--install`) | 박진영 |
| 2026-06-01 (예정) | 첫 자동 재학습 + backtest 실행 결과 검토 | 박진영 |
