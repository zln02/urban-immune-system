#!/usr/bin/env bash
# 발표 슬라이드 정적 자원 동기화
# docs/slides/midterm-deck/  →  frontend/public/slides/
#
# 단일 소스 정책: 슬라이드 원본은 docs/slides/midterm-deck/ 에서만 편집.
# Next.js 정적 자원은 항상 이 스크립트로 갱신해 두 위치가 어긋나지 않게 한다.
# .pptx · .pdf 같은 바이너리 원본은 복사 대상 외.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/docs/slides/midterm-deck"
DST="$ROOT/frontend/public/slides"

if [ ! -d "$SRC" ]; then
  echo "[sync-slides] 원본 없음: $SRC" >&2
  exit 1
fi

if command -v rsync >/dev/null 2>&1; then
  mkdir -p "$DST"
  rsync -a --delete \
    --exclude='*.pptx' --exclude='*.pdf' --exclude='.DS_Store' \
    "$SRC"/ "$DST"/
else
  # rsync 미설치 환경 fallback (cp + 사전 정리)
  rm -rf "$DST"
  mkdir -p "$DST"
  ( cd "$SRC" && find . \( -name '*.pptx' -o -name '*.pdf' -o -name '.DS_Store' \) -prune -o -type f -print ) \
    | while read -r f; do
        d="$DST/${f#./}"
        mkdir -p "$(dirname "$d")"
        cp "$SRC/${f#./}" "$d"
      done
fi

echo "[sync-slides] 동기화 완료: $DST"
ls "$DST"
