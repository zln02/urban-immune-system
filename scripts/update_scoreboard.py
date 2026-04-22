"""주간 기여도 스코어보드 자동 집계.

실행:
    python scripts/update_scoreboard.py W18

입력:
- git log (author 별 커밋 수·테스트 변경량)
- gh pr list --json (PR 머지/리뷰 수) — 선택 (gh 인증 필요)

출력:
- docs/weekly-reports/2026-WNN/scoreboard.json
- docs/weekly-reports/scoreboard.md (전체 주차 누적 갱신)
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# GitHub 계정 → 한글 이름 매핑 (팀원 확정 후 갱신)
GITHUB_HANDLES: dict[str, str] = {
    "zln02": "박진영",
    # "lee-kyungjun": "이경준",
    # "lee-woohyung": "이우형",
    # "kim-nayoung": "김나영",
    # "park-jungbin": "박정빈",
}


def week_bounds(year: int, week: int) -> tuple[date, date]:
    """ISO 주차(월~일) 시작·종료 날짜."""
    start = date.fromisocalendar(year, week, 1)
    end = start + timedelta(days=6)
    return start, end


def git_commits_by_author(since: str, until: str) -> dict[str, int]:
    """작성자별 커밋 수."""
    out = subprocess.run(
        ["git", "log", f"--since={since}", f"--until={until}", "--pretty=%an"],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    authors: dict[str, int] = {}
    for line in out.stdout.splitlines():
        name = line.strip()
        if not name:
            continue
        authors[name] = authors.get(name, 0) + 1
    return authors


def tests_lines_changed(since: str, until: str) -> dict[str, int]:
    """작성자별 tests/ 디렉토리 변경 LoC (추가+삭제)."""
    out = subprocess.run(
        ["git", "log", f"--since={since}", f"--until={until}",
         "--pretty=%an", "--numstat", "--", "tests/"],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    result: dict[str, int] = {}
    current_author = None
    for line in out.stdout.splitlines():
        line = line.rstrip()
        if not line:
            current_author = None
            continue
        if "\t" not in line:
            current_author = line
            continue
        if current_author is None:
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            result[current_author] = result.get(current_author, 0) + int(parts[0]) + int(parts[1])
    return result


def merged_prs(since: str, until: str) -> dict[str, int]:
    """gh CLI 로 머지된 PR 수."""
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--state", "merged", "--limit", "100",
             "--json", "author,mergedAt"],
            capture_output=True, text=True, cwd=ROOT, check=True,
        )
        prs = json.loads(out.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return {}

    count: dict[str, int] = {}
    since_dt = datetime.fromisoformat(since)
    until_dt = datetime.fromisoformat(until) + timedelta(days=1)
    for pr in prs:
        merged = pr.get("mergedAt")
        if not merged:
            continue
        merged_dt = datetime.fromisoformat(merged.replace("Z", "+00:00")).replace(tzinfo=None)
        if since_dt <= merged_dt < until_dt:
            author = pr.get("author", {}).get("login", "")
            if author:
                count[author] = count.get(author, 0) + 1
    return count


def resolve_korean_name(raw: str) -> str:
    """git author 또는 gh login → 한글 팀원명."""
    if raw in GITHUB_HANDLES:
        return GITHUB_HANDLES[raw]
    # git author 이 한글로 박혀 있으면 그대로
    for kr in GITHUB_HANDLES.values():
        if raw == kr:
            return kr
    return raw  # 매핑 없으면 원본


def compute_score(row: dict) -> float:
    return (
        row["commits"] * 1
        + row["prs_merged"] * 5
        + row["pr_reviews"] * 2
        + row["test_loc"] / 10
        + row["issues"] * 1
    )


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: update_scoreboard.py W18")
        sys.exit(1)
    week_str = sys.argv[1].lstrip("W")
    week = int(week_str)
    today = date.today()
    year = today.isocalendar()[0]
    start, end = week_bounds(year, week)

    since = start.isoformat()
    until = end.isoformat()
    print(f"집계 기간: {since} ~ {until} ({year}-W{week:02d})")

    commits_raw = git_commits_by_author(since, until)
    tests_raw = tests_lines_changed(since, until)
    prs_raw = merged_prs(since, until)

    # 한글 이름으로 통합
    members: dict[str, dict] = {}
    for name in set(commits_raw) | set(tests_raw) | set(prs_raw):
        kr = resolve_korean_name(name)
        if kr not in members:
            members[kr] = {"commits": 0, "test_loc": 0, "prs_merged": 0, "pr_reviews": 0, "issues": 0}
        members[kr]["commits"] += commits_raw.get(name, 0)
        members[kr]["test_loc"] += tests_raw.get(name, 0)
        members[kr]["prs_merged"] += prs_raw.get(name, 0)

    # 5명 자리 확보 (없어도 0 표시)
    for kr in GITHUB_HANDLES.values():
        members.setdefault(kr, {"commits": 0, "test_loc": 0, "prs_merged": 0, "pr_reviews": 0, "issues": 0})

    ranked = sorted(
        [{"member": m, **v, "score": round(compute_score(v), 1)} for m, v in members.items()],
        key=lambda r: r["score"], reverse=True,
    )

    # JSON 저장
    week_dir = ROOT / "docs" / "weekly-reports" / f"{year}-W{week:02d}"
    week_dir.mkdir(parents=True, exist_ok=True)
    (week_dir / "scoreboard.json").write_text(
        json.dumps(
            {"year": year, "week": week, "since": since, "until": until, "rows": ranked},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    # 콘솔 출력
    print(f"\n{year}-W{week:02d} 스코어보드")
    print(f"{'순위':<4} {'팀원':<10} {'커밋':>4} {'머지':>4} {'리뷰':>4} {'테스트':>6} {'이슈':>4} {'총점':>6}")
    for i, r in enumerate(ranked, 1):
        print(
            f"{i:<4} {r['member']:<10} {r['commits']:>4} {r['prs_merged']:>4} "
            f"{r['pr_reviews']:>4} {r['test_loc']:>6} {r['issues']:>4} {r['score']:>6}"
        )
    print(f"\n✅ {(week_dir / 'scoreboard.json').relative_to(ROOT)} 저장")


if __name__ == "__main__":
    main()
