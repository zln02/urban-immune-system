#!/bin/bash
# UIS Daily Backup — TimescaleDB(docker) + critical configs (14-day retention)
# 실제 인프라: DB는 docker 컨테이너(uis-timescaledb)라 docker exec pg_dump 사용.
set -e
BACKUP_DIR=/home/wlsdud5035/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG=$BACKUP_DIR/backup.log
ENV=/home/wlsdud5035/urban-immune-system/.env
mkdir -p $BACKUP_DIR

if docker exec uis-timescaledb pg_dump -U uis_user urban_immune 2>/dev/null | gzip > $BACKUP_DIR/db_$TIMESTAMP.sql.gz && [ -s $BACKUP_DIR/db_$TIMESTAMP.sql.gz ]; then
  echo "$(date '+%F %T') [OK] DB: $(du -h $BACKUP_DIR/db_$TIMESTAMP.sql.gz | cut -f1)" >> $LOG
else
  echo "$(date '+%F %T') [FAIL] DB backup failed" >> $LOG
  NTFY=$(grep "^NTFY_TOPIC=" $ENV | cut -d= -f2)
  [ -n "$NTFY" ] && curl -s -d "🚨 UIS daily backup FAILED at $(date '+%F %T')" "https://ntfy.sh/$NTFY" -H "Priority: high" >/dev/null
  exit 1
fi

# config(.env + 모델 체크포인트) + systemd 유닛 아카이브 (실패해도 DB백업은 유지)
tar -czf $BACKUP_DIR/config_$TIMESTAMP.tar.gz -C /home/wlsdud5035 \
  urban-immune-system/.env urban-immune-system/ml/checkpoints/ 2>/dev/null || true
sudo tar -czf $BACKUP_DIR/systemd_$TIMESTAMP.tar.gz /etc/systemd/system/uis-*.service 2>/dev/null || true
echo "$(date '+%F %T') [OK] Config + systemd archived" >> $LOG

find $BACKUP_DIR -name "*.gz" -mtime +14 -delete
echo "$(date '+%F %T') [STATS] Total: $(du -sh $BACKUP_DIR | cut -f1)" >> $LOG
