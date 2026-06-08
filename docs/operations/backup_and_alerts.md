# UIS Backup + Silent-Fail Alert System

> 실제 인프라 반영: DB는 docker 컨테이너(uis-timescaledb), 신호는 layer_signals
> 단일 테이블의 layer 컬럼(otc/wastewater/search)으로 구분.

## Backup (Daily, 03:00 KST)
- Script:    `scripts/ops/backup_daily.sh`
- Method:    `docker exec uis-timescaledb pg_dump -U uis_user urban_immune | gzip`
- Target:    `~/backups/` (db_*.sql.gz · config_*.tar.gz · systemd_*.tar.gz)
- Retention: 14 days local
- Log:       `~/backups/backup.log`
- 실패 시 ntfy.sh 알람 (Priority: high)

## Silent-Fail Alert (every 6h)
- Script:    `scripts/ops/check_collector_health.py`
- Source:    layer_signals 의 layer 별 `MAX(time)` 신선도
- Channels:  Dual safety net
  1. ntfy.sh      — 모바일 push (즉시)
  2. GitHub Issue — 영구 incident 기록 (zln02/urban-immune-system, label `silent-fail`)
     · 동일 라벨 open 이슈가 있으면 중복 생성 방지
- Thresholds:
  - L1 otc:        72h
  - L2 wastewater: 336h (KOWAS T-7~10 lag 반영)
  - L3 search:     72h
- Log:       `~/backups/health_check.log`
- exit 0 = healthy / exit 1 = alert 발사

## ntfy.sh Setup
- Topic은 `.env` 의 `NTFY_TOPIC` 변수에 저장 (gitignore — 커밋 안 함)
- 모바일 앱(iOS/Android): "ntfy" 설치 후 해당 topic 구독
- 주의: HTTP 헤더(Title)는 ASCII 만 허용 — 이모지는 본문(body)에만

## Recovery
```bash
# DB 복원 (docker)
gunzip -c ~/backups/db_YYYYMMDD_HHMMSS.sql.gz | docker exec -i uis-timescaledb psql -U uis_user urban_immune

# Config(.env + 모델 체크포인트) 복원
tar -xzf ~/backups/config_YYYYMMDD_HHMMSS.tar.gz -C /home/wlsdud5035/

# systemd 유닛 복원
sudo tar -xzf ~/backups/systemd_YYYYMMDD_HHMMSS.tar.gz -C /
```

## Future (Phase 2)
- External backup storage (DigitalOcean Spaces / GitHub Releases)
- Encrypted backups
- Prometheus + Grafana
