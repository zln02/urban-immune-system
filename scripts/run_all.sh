#!/usr/bin/env bash
# Urban Immune System — Docker 없이 로컬/외부 가동 (vanilla PostgreSQL)
#   백엔드 FastAPI :18001 · Next.js 대시보드 :13000 (외부 0.0.0.0)
#   Streamlit(Phase1) 은 메모리 여유 있을 때만: ./run_all.sh --streamlit
# 사전조건: .venv 설치 완료, PostgreSQL(urban_immune) 가동, seed_demo_db.py 적재 완료
set -uo pipefail
ROOT="/home/ubuntu/urban-immune-system"
cd "$ROOT"
VENV="$ROOT/.venv/bin"
LOG="$ROOT/.run-logs"; mkdir -p "$LOG"
export PYTHONPATH="$ROOT"

# 기존 인스턴스 정리
pkill -9 -f "uvicorn backend.app.main" 2>/dev/null
pkill -9 -f "$ROOT/frontend.*next" 2>/dev/null
sleep 2

echo "[1/2] FastAPI backend → 0.0.0.0:18001 (torch 지연 import, 첫 기동 ~30-60s)"
setsid bash -c "PYTHONPATH=$ROOT $VENV/uvicorn backend.app.main:app --host 0.0.0.0 --port 18001 > $LOG/backend.log 2>&1" </dev/null >/dev/null 2>&1 &
disown

echo "[2/2] Next.js dashboard → 0.0.0.0:13000 (백엔드 프록시 UIS_API_INTERNAL_URL)"
setsid bash -c "cd $ROOT/frontend && UIS_API_INTERNAL_URL=http://127.0.0.1:18001 exec ./node_modules/.bin/next dev -p 13000 -H 0.0.0.0 > $LOG/frontend.log 2>&1" </dev/null >/dev/null 2>&1 &
disown

if [ "${1:-}" = "--streamlit" ]; then
  echo "[+] Streamlit(Phase1) → 0.0.0.0:18501"
  setsid bash -c "PYTHONPATH=$ROOT $VENV/streamlit run src/app.py --server.port 18501 --server.address 0.0.0.0 --server.headless true > $LOG/streamlit.log 2>&1" </dev/null >/dev/null 2>&1 &
  disown
fi

echo "기동 완료. 로그: $LOG/*.log"
echo "외부 대시보드: http://3.34.222.103:13000/dashboard"
