#!/usr/bin/env bash
# ================================================================
# UIS 부하테스트 전체 파이프라인 (브랜치 → 실행 → 분석 → 커밋)
# 실행: bash tests/load/run_full_pipeline.sh
# ================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

VENV="${PROJECT_ROOT}/.venv"
LOCUST="${VENV}/bin/locust"
PYTHON="${VENV}/bin/python"
HOST="http://localhost:8001"
RESULTS_DIR="${PROJECT_ROOT}/tests/load"

# ── Step 1: 브랜치 ──────────────────────────────────────────
echo "=== Step 1: 브랜치 생성 ==="
git checkout develop 2>/dev/null || git checkout -b develop
git checkout -b feat/load-testing 2>/dev/null || {
    echo "  feat/load-testing 이미 존재 → checkout"
    git checkout feat/load-testing
}

# ── Step 2: locust 확인 ──────────────────────────────────────
echo "=== Step 2: locust 확인 ==="
if ! "${LOCUST}" --version 2>/dev/null; then
    echo "  locust 미설치 → pip install locust"
    "${VENV}/bin/pip" install "locust>=2.24" --quiet
fi
echo "  locust: $("${LOCUST}" --version)"

# ── Step 3: 백엔드 헬스체크 ─────────────────────────────────
echo "=== Step 3: 백엔드 헬스체크 ==="
if ! curl -sf "${HOST}/api/v1/alerts/regions" -o /dev/null; then
    echo "ERROR: ${HOST} 미응답. uvicorn :8001 먼저 가동 필요."
    echo "       uvicorn backend.app.main:app --port 8001"
    exit 1
fi
echo "  → 응답 확인"

# ── Step 4: 부하테스트 실행 ─────────────────────────────────
echo "=== Step 4: 부하테스트 (50 users, 6m) ==="
"${LOCUST}" \
    -f "${RESULTS_DIR}/locustfile.py" \
    --host "${HOST}" \
    --headless \
    --users 50 \
    --spawn-rate 2 \
    --run-time 6m \
    --csv "${RESULTS_DIR}/results" \
    --html "${RESULTS_DIR}/results_report.html"
echo "  → 완료: ${RESULTS_DIR}/results_stats.csv"

# ── Step 5: 결과 분석 ───────────────────────────────────────
echo "=== Step 5: 결과 분석 ==="
"${PYTHON}" "${RESULTS_DIR}/analyze_results.py" \
    --csv "${RESULTS_DIR}/results_stats.csv" \
    --output-json "analysis/outputs/load_test_results.json" \
    --output-chart "analysis/outputs/load_test_summary.png"

# ── Step 6: 커밋 ────────────────────────────────────────────
echo "=== Step 6: git 커밋 ==="
git add \
    tests/load/locustfile.py \
    tests/load/__init__.py \
    tests/load/run_load_test.sh \
    tests/load/run_full_pipeline.sh \
    tests/load/analyze_results.py \
    analysis/outputs/load_test_results.json \
    docs/load-testing.md

# PNG는 있을 때만 추가
if [ -f "analysis/outputs/load_test_summary.png" ]; then
    git add analysis/outputs/load_test_summary.png
fi

git commit -m "$(cat <<'EOF'
feat(tests): FastAPI 부하테스트 추가 — 조달청 p95 < 500ms 검증

- tests/load/locustfile.py: locust 시나리오 (50 동시 사용자, 4개 엔드포인트)
- tests/load/analyze_results.py: CSV → JSON + matplotlib bar chart 분석기
- tests/load/run_load_test.sh: 원스텝 실행 스크립트
- analysis/outputs/load_test_results.json: 측정 결과 (p50/p95/p99/RPS/실패율)
- docs/load-testing.md: 실행 방법 + 측정값 + 병목 대응 가이드
EOF
)"

echo ""
echo "=== 완료 ==="
echo "커밋 SHA: $(git rev-parse --short HEAD)"
git diff --stat HEAD~1
