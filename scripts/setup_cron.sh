#!/usr/bin/env bash
# UIS 운영 자동화 일괄 설치 — systemd 3 유닛 + crontab P0/P1 잡 9건.
#
# 사용:
#   bash scripts/setup_cron.sh --dry-run   # 적용 미리보기 (안전)
#   bash scripts/setup_cron.sh --install   # 실제 등록 (sudo 필요)
#   bash scripts/setup_cron.sh --uninstall # 제거
#
# 권장 적용 시점: 2026-05-08 (중간발표 다음날)
# 사전 조건:
#   - /home/wlsdud5035/urban-immune-system/.env 가 prod 자격증명으로 채워짐
#   - .venv 활성화된 적 있음 (pip install -e ".[all]" 1회 완료)
#   - PostgreSQL urban_immune DB 가동 중

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
UNITS=(uis-scheduler.service uis-backend.service uis-frontend.service)

MODE="${1:---dry-run}"

# ── crontab 라인 생성 ──────────────────────────────────────────
generate_cron_lines() {
    cat <<EOF
# === UIS 운영 자동화 (P0+P1) — 자동 생성, 수동 편집 금지 ===
# P0: 5분마다 scheduler liveness — 죽으면 자동 재기동
*/5 * * * * pgrep -f "pipeline.collectors.scheduler" >/dev/null || sudo systemctl restart uis-scheduler

# P0: 매일 03:00 KST DB 백업 (14일 보관)
0 3 * * * pg_dump -d urban_immune | gzip > $REPO_ROOT/backups/uis-\$(date +\\%F).sql.gz && find $REPO_ROOT/backups/ -name "uis-*.sql.gz" -mtime +14 -delete

# P0: 매일 08:00 KST 데이터 신선도 점검 + stale 시 GitHub Issue
0 8 * * * bash $REPO_ROOT/scripts/freshness_alert.sh >> $REPO_ROOT/logs/freshness.log 2>&1

# P1: 매주 월 11:00 KST L1·L3 수집 실패 재시도 (월 09:00 후 2시간 buffer)
0 11 * * mon bash $REPO_ROOT/scripts/check_data_freshness.sh || (cd $REPO_ROOT && .venv/bin/python -m pipeline.collectors.naver_backfill --weeks 1)

# P1: 매주 화 12:00 KST KOWAS 다운로드 실패 백업
0 12 * * tue bash $REPO_ROOT/scripts/check_data_freshness.sh || (cd $REPO_ROOT && .venv/bin/python -m pipeline.collectors.kowas_downloader --weeks 4)

# P1: 매주 일 03:00 KST 로그 회전 (7d 압축, 30d 삭제)
0 3 * * sun find $REPO_ROOT/logs -name "*.log" -mtime +7 -exec gzip -f {} \\; && find $REPO_ROOT/logs -name "*.gz" -mtime +30 -delete

# P1: 매월 1일 02:00 KST TFT 재학습 (26주 누적 데이터 기반)
0 2 1 * * cd $REPO_ROOT && .venv/bin/python -m ml.tft.train_real --weeks 26 --epochs 50 >> $REPO_ROOT/logs/tft_retrain.log 2>&1

# P1: 매월 1일 03:00 KST 17지역 backtest 재실행
0 3 1 * * cd $REPO_ROOT && .venv/bin/python -m analysis.backtest_17regions >> $REPO_ROOT/logs/backtest.log 2>&1

# P1: 매월 1일 03:30 KST F1 회귀 감지 (베이스라인 0.841 대비 -0.05 이상 하락 시 Issue)
30 3 1 * * bash $REPO_ROOT/scripts/check_f1_regression.sh >> $REPO_ROOT/logs/f1_regression.log 2>&1
# === UIS 끝 ===
EOF
}

# ── dry-run 출력 ────────────────────────────────────────────────
do_dry_run() {
    echo "════════════════════════════════════════════════════════════"
    echo "  UIS 운영 자동화 — DRY RUN (실제 변경 없음)"
    echo "  대상 사용자: $USER"
    echo "  REPO_ROOT:   $REPO_ROOT"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "── systemd 유닛 (sudo cp → $SYSTEMD_DIR/) ──"
    for u in "${UNITS[@]}"; do
        if [[ -f "$REPO_ROOT/infra/systemd/$u" ]]; then
            echo "  ✓ $u"
        else
            echo "  ✗ MISSING: infra/systemd/$u"
        fi
    done
    echo ""
    echo "── 로그 파일 생성 (sudo touch /var/log/uis-*.log) ──"
    for u in "${UNITS[@]}"; do
        echo "  /var/log/${u%.service}.log"
    done
    echo ""
    echo "── 백업 디렉터리 ──"
    echo "  mkdir -p $REPO_ROOT/backups (chmod 750)"
    echo ""
    echo "── crontab 추가될 라인 ──"
    generate_cron_lines
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  실제 적용: bash scripts/setup_cron.sh --install"
    echo "════════════════════════════════════════════════════════════"
}

# ── 실제 설치 ──────────────────────────────────────────────────
do_install() {
    echo "[install] systemd 유닛 복사 (sudo)"
    for u in "${UNITS[@]}"; do
        if [[ ! -f "$REPO_ROOT/infra/systemd/$u" ]]; then
            echo "ERROR: infra/systemd/$u 없음" >&2
            exit 1
        fi
        sudo cp "$REPO_ROOT/infra/systemd/$u" "$SYSTEMD_DIR/$u"
    done

    echo "[install] 로그 파일 생성 + 소유권"
    for u in "${UNITS[@]}"; do
        local log="/var/log/${u%.service}.log"
        sudo touch "$log"
        sudo chown "$USER:$USER" "$log"
    done

    echo "[install] 백업 디렉터리"
    mkdir -p "$REPO_ROOT/backups"
    chmod 750 "$REPO_ROOT/backups"

    echo "[install] systemd reload + enable + start"
    sudo systemctl daemon-reload
    sudo systemctl enable "${UNITS[@]}"
    sudo systemctl start "${UNITS[@]}"

    echo "[install] crontab merge (기존 UIS 라인 제거 후 재삽입)"
    local tmp
    tmp=$(mktemp)
    crontab -l 2>/dev/null | sed '/=== UIS 운영 자동화/,/=== UIS 끝 ===/d' > "$tmp"
    generate_cron_lines >> "$tmp"
    crontab "$tmp"
    rm -f "$tmp"

    echo ""
    echo "✓ 설치 완료. 점검 명령:"
    echo "    sudo systemctl status ${UNITS[*]}"
    echo "    crontab -l | grep -A1 UIS"
}

# ── 제거 ───────────────────────────────────────────────────────
do_uninstall() {
    echo "[uninstall] systemd 유닛 정지 + disable"
    sudo systemctl stop "${UNITS[@]}" 2>/dev/null || true
    sudo systemctl disable "${UNITS[@]}" 2>/dev/null || true
    for u in "${UNITS[@]}"; do
        sudo rm -f "$SYSTEMD_DIR/$u"
    done
    sudo systemctl daemon-reload

    echo "[uninstall] crontab 라인 제거"
    local tmp
    tmp=$(mktemp)
    crontab -l 2>/dev/null | sed '/=== UIS 운영 자동화/,/=== UIS 끝 ===/d' > "$tmp"
    crontab "$tmp"
    rm -f "$tmp"

    echo "✓ 제거 완료."
}

case "$MODE" in
    --dry-run) do_dry_run ;;
    --install) do_install ;;
    --uninstall) do_uninstall ;;
    *)
        cat >&2 <<EOF
사용: $0 [--dry-run|--install|--uninstall]

  --dry-run    적용될 변경 사항 미리보기 (기본값, 권장 첫 실행)
  --install    실제 등록 (sudo systemctl + crontab 변경)
  --uninstall  모든 설정 제거

5/8 (중간발표 다음날) 적용 권장.
EOF
        exit 1
        ;;
esac
