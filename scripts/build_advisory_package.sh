#!/usr/bin/env bash
# 외부 자문 패키지 빌드 — KDCA · KISA 발송용 zip 생성
# 사용: bash scripts/build_advisory_package.sh
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
ADV_DIR="$ROOT/docs/business/advisory"
OUT_ZIP="$ROOT/docs/business/uis-advisory-package-W18.zip"

echo "[1/5] 핵심 코드 스냅샷 (40_code_snapshot.tar.gz)"
tar -czf "$ADV_DIR/40_code_snapshot.tar.gz" \
    --transform 's,^,uis-code-snapshot/,' \
    pipeline/scorer.py \
    pipeline/collectors/normalization.py \
    pipeline/collectors/otc_collector.py \
    pipeline/collectors/kowas_parser.py \
    pipeline/collectors/search_collector.py \
    ml/xgboost/model.py \
    ml/tft/train_real.py \
    ml/anomaly/autoencoder.py \
    ml/rag/report_generator.py \
    ml/reproduce_validation.py \
    backend/app/config.py \
    backend/app/api/alerts.py \
    backend/app/services/alert_service.py \
    infra/db/init.sql 2>/dev/null || true

echo "[2/5] 검증 리포트 PDF 복사 (최신 → archive 순으로 탐색)"
PDF_CANDIDATES=(
    "$ROOT/docs/slides/검증리포트_최신.pdf"
    "$ROOT/docs/slides/archive/2026-04-30_v1/2026-04-30_중간발표_검증리포트.pdf"
)
for cand in "${PDF_CANDIDATES[@]}"; do
    if [ -f "$cand" ]; then
        cp "$cand" "$ADV_DIR/20_walk_forward_backtest.pdf"
        echo "  ✓ $cand"
        break
    fi
done
if [ ! -f "$ADV_DIR/20_walk_forward_backtest.pdf" ]; then
    echo "  ⚠ 검증 리포트 PDF 없음 — 'python scripts/build_review_pdf.py' 먼저 실행하세요"
fi

echo "[3/5] 백테스트 JSON 결과 첨부"
mkdir -p "$ADV_DIR/data"
cp -f "$ROOT/analysis/outputs/backtest_17regions.json" "$ADV_DIR/data/" 2>/dev/null || true
cp -f "$ROOT/analysis/outputs/lead_time_summary.json"  "$ADV_DIR/data/" 2>/dev/null || true
cp -f "$ROOT/ml/outputs/validation.json"               "$ADV_DIR/data/" 2>/dev/null || true
cp -f "$ROOT/ml/outputs/tft_real_metrics.json"         "$ADV_DIR/data/" 2>/dev/null || true

echo "[4/5] zip 압축 (Python zipfile)"
rm -f "$OUT_ZIP"
python3 - <<PYEOF
import os, zipfile
adv = "$ADV_DIR"
out = "$OUT_ZIP"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(adv):
        for f in files:
            if f == ".DS_Store" or "__pycache__" in root: continue
            full = os.path.join(root, f)
            arc = os.path.relpath(full, os.path.dirname(adv))
            z.write(full, arc)
print(f"OK · {out}")
PYEOF

echo "[5/5] 결과"
echo "  생성: $OUT_ZIP"
ls -lh "$OUT_ZIP"
echo ""
echo "  포함 파일:"
python3 -c "
import zipfile
with zipfile.ZipFile('$OUT_ZIP') as z:
    for n in z.namelist():
        info = z.getinfo(n)
        print(f'    {info.file_size:>9,}  {n}')
"

echo ""
echo "발송 다음 단계:"
echo "  KDCA: docs/business/advisory/10_kdca_request_letter.md → 우편 등기 + 이메일"
echo "  KISA: docs/business/advisory/11_kisa_consult_application.md → 사전 컨설팅 신청 시스템"
echo "  공통 첨부: $OUT_ZIP"
