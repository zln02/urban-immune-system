#!/usr/bin/env bash
# GitHub labels 일괄 생성/갱신 — 박진영이 1회 실행
set -euo pipefail

REPO="zln02/urban-immune-system"

# "label|color|desc" 형식으로 통일 (bash 4 associative array 호환성 회피)
LABELS=(
  "priority:critical|B10B10|캡스톤 발표 직전 블로커"
  "priority:high|D93F0B|이번 주 반드시"
  "priority:medium|FBCA04|다음 주까지"
  "priority:low|C5DEF5|여유 있을 때"
  "type:feat|0E8A16|새 기능"
  "type:fix|D73A4A|버그 수정"
  "type:docs|0075CA|문서"
  "type:refactor|5319E7|리팩토링"
  "type:test|1D76DB|테스트"
  "type:chore|FEF2C0|잡일"
  "module:backend|1D76DB|backend/"
  "module:pipeline|2EA44F|pipeline/"
  "module:ml|BFD4F2|ml/"
  "module:src|F9D0C4|src/ Streamlit"
  "module:frontend|C5DEF5|frontend/ Next.js"
  "module:infra|0052CC|infra/, .github/"
  "module:docs|5319E7|docs/"
  "owner:박진영|B10B10|PM/ML Lead"
  "owner:이경준|0E8A16|Backend"
  "owner:이우형|5319E7|Data Engineer"
  "owner:김나영|F9D0C4|Frontend"
  "owner:박정빈|FBCA04|DevOps/QA"
  "status:blocked|B60205|블로커 있음"
  "status:in-review|FBCA04|리뷰 중"
  "status:ready|0E8A16|작업 가능"
  "b2g:isms-p|D93F0B|ISMS-P 영향"
  "b2g:pricing|FBCA04|가격·수익 영향"
  "b2g:compliance|D93F0B|법무 검토 필요"
  "capstone:mid-presentation|B10B10|4/30 중간발표 관련"
  "capstone:final-presentation|B10B10|기말발표 관련"
)

echo "📛 GitHub labels 생성/갱신: $REPO"
for entry in "${LABELS[@]}"; do
  IFS='|' read -r name color desc <<< "$entry"
  if gh label create "$name" --color "$color" --description "$desc" --repo "$REPO" 2>/dev/null; then
    echo "  ✅ created: $name"
  else
    gh label edit "$name" --color "$color" --description "$desc" --repo "$REPO" >/dev/null 2>&1 && \
      echo "  🔄 updated: $name" || echo "  ⚠️  skip:    $name"
  fi
done

echo ""
echo "📋 총 $(gh label list --repo "$REPO" --limit 100 | wc -l) 개 label 등록"
