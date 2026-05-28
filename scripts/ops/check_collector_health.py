#!/usr/bin/env python3
"""
UIS Collector Silent-Fail Detector — ntfy.sh + GitHub Issue dual alert.
Runs every 6h via cron. Dual safety net (mobile push + persistent record).

실제 schema 반영: 신호는 layer_signals 단일 테이블의 layer 컬럼(otc/wastewater/search)
으로 구분되고, 신선도 기준 컬럼은 time 이다. DB는 docker(uis-timescaledb)가
localhost:5432 로 노출. DATABASE_URL(asyncpg) 을 psycopg2 DSN 으로 변환해 사용한다.
"""
import os
import sys
import subprocess
import psycopg2
import requests
from datetime import datetime, timezone
from pathlib import Path

# Load .env
env_file = Path("/home/wlsdud5035/urban-immune-system/.env")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
# asyncpg URL -> psycopg2 DSN
DB_DSN = os.getenv("DATABASE_URL", "postgresql://uis_user:CHANGE_ME@localhost:5432/urban_immune").replace("+asyncpg", "")
GH_REPO = "zln02/urban-immune-system"

# layer_signals.layer 값 기준 신선도 임계(시간). L2 KOWAS 는 T-7~10 lag 반영.
THRESHOLDS = {
    'otc':        72,
    'wastewater': 336,
    'search':     72,
}

def check_layer(layer, threshold_hours):
    try:
        conn = psycopg2.connect(DB_DSN)
        cur = conn.cursor()
        cur.execute("SELECT MAX(time) FROM layer_signals WHERE layer = %s", (layer,))
        last = cur.fetchone()[0]
        conn.close()
        if last is None:
            return None, threshold_hours, True, "no rows for layer"
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        return elapsed, threshold_hours, elapsed > threshold_hours, last.isoformat()
    except Exception as e:
        return None, threshold_hours, True, f"db error: {e}"

def send_ntfy(title, msg):
    if not NTFY_TOPIC:
        print("[WARN] NTFY_TOPIC not set", file=sys.stderr)
        return False
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=msg.encode("utf-8"),
            headers={"Title": (title.encode("ascii", "ignore").decode().strip() or "UIS Alert"), "Priority": "high", "Tags": "warning,uis"},
            timeout=10,
        )
        return True
    except Exception as e:
        print(f"[ERROR] ntfy.sh send failed: {e}", file=sys.stderr)
        return False

def create_github_issue(title, body):
    try:
        # 24h 내 동일 라벨 open 이슈 있으면 중복 생성 방지
        result = subprocess.run(
            ["gh", "issue", "list", "--repo", GH_REPO, "--label", "silent-fail",
             "--state", "open", "--limit", "5", "--json", "title,createdAt"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip() not in ("", "[]"):
            print("[INFO] Recent silent-fail issue exists, skipping duplicate")
            return True
        subprocess.run(
            ["gh", "issue", "create", "--repo", GH_REPO, "--title", title,
             "--body", body, "--label", "silent-fail,P0-critical,infra"],
            check=True, timeout=15,
        )
        return True
    except Exception as e:
        print(f"[ERROR] GitHub Issue creation failed: {e}", file=sys.stderr)
        return False

def main():
    alerts, healthy = [], []
    for layer, threshold in THRESHOLDS.items():
        elapsed, thresh, is_stale, info = check_layer(layer, threshold)
        if is_stale:
            if elapsed is not None:
                alerts.append(f"⚠️ {layer}: {elapsed:.1f}h stale (threshold {thresh}h)")
            else:
                alerts.append(f"❌ {layer}: {info}")
        else:
            healthy.append(f"✅ {layer}: {elapsed:.1f}h (within {thresh}h)")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if alerts:
        ntfy_msg = "Silent-fail detected:\n\n" + "\n".join(alerts)
        if healthy:
            ntfy_msg += "\n\nHealthy:\n" + "\n".join(healthy)
        gh_title = f"[Silent-fail] Collector stale detected at {timestamp}"
        gh_body = f"## Detected at\n{timestamp}\n\n## Alerts\n" + "\n".join(f"- {a}" for a in alerts)
        gh_body += "\n\n## Healthy\n" + "\n".join(f"- {h}" for h in healthy)
        gh_body += "\n\n## Auto-detected by\n`scripts/ops/check_collector_health.py`"
        gh_body += "\n\n## Action\nInvestigate collector logs (uis-scheduler) and restart if needed."
        ntfy_ok = send_ntfy("🚨 UIS Silent-Fail", ntfy_msg)
        gh_ok = create_github_issue(gh_title, gh_body)
        print(f"{timestamp}: ALERT — ntfy={'OK' if ntfy_ok else 'FAIL'} / github={'OK' if gh_ok else 'FAIL'}")
        sys.exit(1)
    else:
        print(f"{timestamp}: All {len(THRESHOLDS)} layers healthy")
        sys.exit(0)

if __name__ == "__main__":
    main()
