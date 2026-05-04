#!/usr/bin/env bash
# 데이터 신선도 점검 — 마지막 layer_signals 레코드와 ML metrics 갱신 시각 확인.
#
# 정상 종료 (0): 모든 데이터가 STALE_HOURS (기본 72시간) 이내
# 비정상 종료 (1): 1개 이상 stale → cron 호출 시 logs/freshness.log 기록 + 운영자 알림 후크
#
# 사용:
#   bash scripts/check_data_freshness.sh                       # 표준 검사
#   STALE_HOURS=24 bash scripts/check_data_freshness.sh         # 임계 강화
#   bash scripts/check_data_freshness.sh --json                  # JSON 출력 (모니터링 통합)
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

STALE_HOURS="${STALE_HOURS:-72}"
JSON_OUT=0
[[ "${1:-}" == "--json" ]] && JSON_OUT=1

# .env 로드 (DATABASE_URL 등)
if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

now_kst=$(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S KST')
exit_code=0
declare -a alerts

# ── 1. ML metrics 파일 mtime ─────────────────────────────────────
check_file_mtime() {
    local path="$1"
    local label="$2"
    if [[ ! -f "$path" ]]; then
        alerts+=("MISSING:${label}=${path}")
        exit_code=1
        return
    fi
    local mtime now age_h
    mtime=$(stat -c %Y "$path")
    now=$(date +%s)
    age_h=$(( (now - mtime) / 3600 ))
    if (( age_h > STALE_HOURS )); then
        alerts+=("STALE:${label}=${age_h}h")
        exit_code=1
    else
        alerts+=("OK:${label}=${age_h}h")
    fi
}

check_file_mtime "ml/outputs/tft_real_metrics.json"     "tft_metrics"
check_file_mtime "ml/outputs/anomaly_metrics.json"      "anomaly_metrics"
check_file_mtime "analysis/outputs/backtest_17regions.json" "backtest"

# ── 2. KOWAS 최신 PDF (수집 파이프라인 작동 신호) ─────────────────
latest_kowas=$(find pipeline/data/kowas -maxdepth 1 -name "kowas_*.pdf" -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | head -1 | cut -d' ' -f2)
if [[ -n "${latest_kowas:-}" ]]; then
    check_file_mtime "$latest_kowas" "kowas_pdf"
else
    alerts+=("MISSING:kowas_pdf=pipeline/data/kowas/")
    exit_code=1
fi

# ── 3. Backend API 응답 (실행 중일 때만) ───────────────────────────
api_status="not-running"
api_url="${BACKEND_URL:-http://localhost:8001}/api/v1/signals/latest"
if command -v curl >/dev/null && curl -s -m 3 -o /dev/null -w "%{http_code}" "$api_url" 2>/dev/null | grep -q "200"; then
    api_status="200-ok"
    alerts+=("OK:backend_api=$api_status")
else
    alerts+=("WARN:backend_api=$api_status")
fi

# ── 출력 ────────────────────────────────────────────────────────
if (( JSON_OUT == 1 )); then
    printf '{"checked_at":"%s","stale_hours_threshold":%d,"exit_code":%d,"items":[' \
        "$now_kst" "$STALE_HOURS" "$exit_code"
    for i in "${!alerts[@]}"; do
        [[ $i -gt 0 ]] && printf ','
        printf '"%s"' "${alerts[$i]}"
    done
    printf ']}\n'
else
    echo "[$now_kst] UIS data freshness check (threshold=${STALE_HOURS}h)"
    for line in "${alerts[@]}"; do
        if [[ "$line" == OK:* ]]; then
            echo "  ✓ $line"
        else
            echo "  ✗ $line"
        fi
    done
    if (( exit_code == 0 )); then
        echo "결과: 모든 데이터 최신 (≤ ${STALE_HOURS}h)"
    else
        echo "결과: STALE 항목 있음 — pipeline/collectors/scheduler.py 실행 또는 수동 수집 필요"
    fi
fi

exit $exit_code
