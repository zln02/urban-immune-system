#!/usr/bin/env bash
# 팀원 온보딩 환경 검증 스크립트
# 사용법: bash scripts/verify_onboarding.sh
# (본인 PC 가 아닌 **서버에서** 실행)

set +e

echo "🔍 Urban Immune System 환경 검증"
echo "=================================="

# 색상
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✅ $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }

echo ""
echo "1️⃣  서버 기본"
[ "$(whoami)" = "wlsdud5035" ] && pass "SSH 접속 성공 (wlsdud5035)" || fail "잘못된 사용자"
[ -d ~/urban-immune-system ] && pass "프로젝트 디렉토리 존재" || fail "프로젝트 없음 → git clone 필요"
cd ~/urban-immune-system || exit 1

echo ""
echo "2️⃣  Git"
git remote -v | grep -q "zln02" && pass "GitHub remote 연결" || fail "git remote 확인"
BRANCH=$(git branch --show-current)
echo "  현재 브랜치: $BRANCH"
git fetch origin -q && pass "원격 fetch OK" || fail "GitHub 접근 불가 (gh auth login?)"

echo ""
echo "3️⃣  Python venv"
[ -d .venv ] && pass "venv 존재" || fail "venv 없음 → python3.11 -m venv .venv"
source .venv/bin/activate 2>/dev/null
PYVER=$(python --version 2>&1)
[[ "$PYVER" == *"3.11"* ]] && pass "$PYVER" || warn "Python 3.11 권장"
python -c "import fastapi, streamlit, sqlalchemy" 2>/dev/null && pass "핵심 패키지 import OK" || fail "pip install -e '.[all,dev]'"

echo ""
echo "4️⃣  Docker 서비스"
if sudo docker compose ps --format '{{.Names}}' 2>/dev/null | grep -q uis-kafka; then
  pass "Docker Compose 실행 중"
  for svc in uis-kafka uis-timescaledb uis-qdrant; do
    STATUS=$(sudo docker inspect --format '{{.State.Health.Status}}' $svc 2>/dev/null)
    if [ "$STATUS" = "healthy" ]; then
      pass "$svc: healthy"
    elif [ "$STATUS" = "unhealthy" ]; then
      warn "$svc: unhealthy (기능은 OK)"
    else
      warn "$svc: $STATUS"
    fi
  done
else
  fail "Docker 안 떠있음 → sudo docker compose up -d"
fi

echo ""
echo "5️⃣  서비스 포트"
ss -tlnp 2>/dev/null | grep -q ":8501" && pass "Streamlit 8501 리스닝" || warn "Streamlit 미기동"
ss -tlnp 2>/dev/null | grep -q ":8000" && pass "Backend 8000 리스닝" || warn "Backend 미기동 (uvicorn 실행 필요)"
ss -tlnp 2>/dev/null | grep -q ":5432" && pass "TimescaleDB 5432" || fail "DB 미기동"
ss -tlnp 2>/dev/null | grep -q ":9092" && pass "Kafka 9092" || fail "Kafka 미기동"

echo ""
echo "6️⃣  환경변수 (.env)"
if [ -f .env ]; then
  pass ".env 존재"
  grep -q "^NAVER_CLIENT_ID=.\+" .env && pass "NAVER_CLIENT_ID 값 있음" || warn "NAVER_CLIENT_ID 비어있음"
  grep -q "^OPENAI_API_KEY=.\+" .env && pass "OPENAI_API_KEY 값 있음" || warn "OPENAI_API_KEY 비어있음"
else
  fail ".env 없음 → cp .env.example .env 후 박진영에게 키 요청"
fi

echo ""
echo "7️⃣  Claude Code"
command -v claude >/dev/null && pass "claude 명령어 설치됨" || fail "npm install -g @anthropic-ai/claude-code"
[ -d ~/.claude/hooks ] && pass "Claude hooks 폴더 존재" || warn "~/.claude/hooks 없음 (에이전트 배지 안 뜰 수 있음)"

echo ""
echo "8️⃣  DB 데이터 상태 (참고용)"
ROWS=$(sudo docker exec uis-timescaledb psql -U uis_user -d urban_immune -tAc "SELECT count(*) FROM layer_signals;" 2>/dev/null || echo "N/A")
echo "  layer_signals row: $ROWS"
[ "$ROWS" = "0" ] && warn "DB 비어있음 (이우형 Consumer 완성 시 증가)" || pass "DB row $ROWS 건"

echo ""
echo "9️⃣  테스트 통과 확인 (선택)"
.venv/bin/pytest tests/ -q --no-header 2>&1 | tail -2

echo ""
echo "🔟  본인 담당 이슈 (GitHub)"
gh issue list --assignee @me --repo zln02/urban-immune-system 2>/dev/null | head -5 || warn "gh auth login 필요 or 본인에게 배정된 이슈 없음"

echo ""
echo "=================================="
echo "검증 완료. 문제 있으면 Discord #uis-help 에 스크롤 전체 붙여넣기."
