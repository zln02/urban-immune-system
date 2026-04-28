#!/usr/bin/env bash
# ============================================================
# UIS FastAPI 부하테스트 실행 스크립트
# 조달청 공공SW 기준: p95 < 500ms
# 사용법: bash tests/load/run_load_test.sh
# ============================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="${PROJECT_ROOT}/.venv"
RESULTS_DIR="${PROJECT_ROOT}/tests/load"
HOST="http://localhost:8001"

# ── 사전 검사 ──────────────────────────────────────────────
echo "[1/4] 백엔드 헬스체크..."
if ! curl -sf "${HOST}/api/v1/alerts/regions" > /dev/null; then
    echo "ERROR: uvicorn :8001 미응답. 먼저 백엔드를 가동하세요."
    echo "       uvicorn backend.app.main:app --port 8001 &"
    exit 1
fi
echo "  → 응답 확인"

# ── locust 설치 여부 확인 ─────────────────────────────────
echo "[2/4] locust 확인..."
LOCUST="${VENV}/bin/locust"
if ! "${LOCUST}" --version 2>/dev/null; then
    echo "  locust 미설치 → 설치 중..."
    "${VENV}/bin/pip" install "locust>=2.24" --quiet
fi
echo "  → $("${LOCUST}" --version)"

# ── 부하테스트 실행 ────────────────────────────────────────
echo "[3/4] 부하테스트 시작 (총 6분, 최대 50 동시 사용자)..."
"${LOCUST}" \
    -f "${RESULTS_DIR}/locustfile.py" \
    --host "${HOST}" \
    --headless \
    --users 50 \
    --spawn-rate 2 \
    --run-time 6m \
    --csv "${RESULTS_DIR}/results" \
    --html "${RESULTS_DIR}/results_report.html"

# ── 결과 분석 ──────────────────────────────────────────────
echo "[4/4] 결과 분석..."
python3 - <<'PY'
import csv, json, pathlib, sys
from datetime import datetime

results_csv = pathlib.Path("tests/load/results_stats.csv")
if not results_csv.exists():
    print("ERROR: results_stats.csv 없음. locust 실행 실패?")
    sys.exit(1)

rows = list(csv.DictReader(open(results_csv, encoding="utf-8")))
output = {"generated_at": datetime.now().isoformat(), "endpoints": [], "summary": {}}
fail_threshold = 500  # p95 < 500ms 목표

all_pass = True
for r in rows:
    name = r.get("Name", "")
    if name in ("Aggregated", ""):
        continue
    p50  = float(r.get("50%", 0) or 0)
    p95  = float(r.get("95%", 0) or 0)
    p99  = float(r.get("99%", 0) or 0)
    rps  = float(r.get("Requests/s", 0) or 0)
    fail = int(r.get("Failure Count", 0) or 0)
    total= int(r.get("Request Count", 0) or 1)
    fail_rate = round(fail / total * 100, 2) if total else 0.0
    pass_p95 = p95 < fail_threshold

    if not pass_p95:
        all_pass = False

    endpoint_result = {
        "endpoint": name,
        "p50_ms": p50, "p95_ms": p95, "p99_ms": p99,
        "rps": round(rps, 2),
        "failure_count": fail,
        "failure_rate_pct": fail_rate,
        "p95_pass": pass_p95,
        "p95_target_ms": fail_threshold,
    }
    output["endpoints"].append(endpoint_result)
    status = "PASS" if pass_p95 else "FAIL"
    print(f"  {status:4s} {name}")
    print(f"       p50={p50:.0f}ms  p95={p95:.0f}ms  p99={p99:.0f}ms  "
          f"RPS={rps:.1f}  실패율={fail_rate:.1f}%")

output["summary"]["all_p95_pass"] = all_pass
output["summary"]["overall_verdict"] = "PASS" if all_pass else "FAIL"

out_path = pathlib.Path("analysis/outputs/load_test_results.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n결과 저장: {out_path}")
print(f"종합 판정: {'PASS — 모든 엔드포인트 p95 < 500ms' if all_pass else 'FAIL — 일부 엔드포인트 p95 >= 500ms'}")
PY
