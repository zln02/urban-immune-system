"""docs/portfolio/ 마크다운을 단일 HTML 로 빌드.

실행:
    python scripts/build_portfolio.py
    → docs/portfolio/portfolio.html

종속성: markdown (표준), 없으면 인라인 렌더러로 fallback.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "docs" / "portfolio"
OUT = PF / "portfolio.html"

SECTIONS = [
    ("decisions", "🏛 Decisions (ADR)"),
    ("troubleshooting", "🔧 Troubleshooting"),
    ("milestones", "🏁 Milestones"),
    ("retrospectives", "🔁 Retrospectives"),
]


def md_to_html(md: str) -> str:
    try:
        import markdown

        return markdown.markdown(md, extensions=["tables", "fenced_code"])
    except ImportError:
        out = html.escape(md)
        out = re.sub(r"^### (.+)$", r"<h3>\1</h3>", out, flags=re.M)
        out = re.sub(r"^## (.+)$", r"<h2>\1</h2>", out, flags=re.M)
        out = re.sub(r"^# (.+)$", r"<h1>\1</h1>", out, flags=re.M)
        out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
        out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
        out = out.replace("\n\n", "</p><p>")
        return f"<p>{out}</p>"


def collect(section: str) -> list[tuple[str, str]]:
    dirp = PF / section
    if not dirp.exists():
        return []
    items = []
    for f in sorted(dirp.glob("*.md")):
        if f.name.startswith("_template"):
            continue
        items.append((f.stem, f.read_text(encoding="utf-8")))
    return items


def build() -> None:
    timeline_md = (PF / "timeline.md").read_text(encoding="utf-8") if (PF / "timeline.md").exists() else ""
    readme_md = (PF / "README.md").read_text(encoding="utf-8") if (PF / "README.md").exists() else ""

    parts = [
        "<!doctype html>",
        '<html lang="ko"><head><meta charset="utf-8">',
        "<title>Urban Immune System — Portfolio</title>",
        "<style>",
        "body{font-family:-apple-system,'Segoe UI','Nanum Gothic',sans-serif;margin:0;background:#f7f8fb;color:#222}",
        "header{background:#1f2d5b;color:#fff;padding:32px 40px}",
        "header h1{margin:0;font-size:28px}",
        "header p{margin:4px 0 0;opacity:.85}",
        "nav{background:#fff;padding:12px 40px;border-bottom:1px solid #e5e7eb;position:sticky;top:0;z-index:10}",
        "nav a{margin-right:16px;color:#1f2d5b;text-decoration:none;font-weight:600}",
        "nav a:hover{color:#e63b3b}",
        "main{max-width:1100px;margin:0 auto;padding:32px 40px}",
        "section{background:#fff;padding:24px 28px;border-radius:8px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.06)}",
        "section h2{margin-top:0;color:#1f2d5b;border-bottom:3px solid #e63b3b;padding-bottom:8px;display:inline-block}",
        "article{border-left:3px solid #e5e7eb;padding:8px 16px;margin:16px 0}",
        "article h3{margin:0 0 8px;color:#1f2d5b}",
        "article:hover{border-left-color:#e63b3b}",
        "code{background:#f2f4f7;padding:2px 6px;border-radius:3px;font-size:.9em}",
        "pre{background:#f2f4f7;padding:12px;border-radius:4px;overflow:auto}",
        "table{border-collapse:collapse;width:100%;margin:8px 0}",
        "th,td{border:1px solid #e5e7eb;padding:6px 10px;text-align:left}",
        "th{background:#f2f4f7}",
        "footer{text-align:center;padding:20px;color:#888;font-size:13px}",
        ".empty{color:#999;font-style:italic}",
        "</style></head><body>",
        "<header>",
        "<h1>Urban Immune System — Team Portfolio</h1>",
        f"<p>감염병 조기경보 AI · 캡스톤 · B2G · 마지막 빌드 {datetime.now().strftime('%Y-%m-%d %H:%M KST')}</p>",
        "</header>",
        "<nav>",
        '<a href="#timeline">Timeline</a>',
    ]
    for key, _ in SECTIONS:
        parts.append(f'<a href="#{key}">{key.title()}</a>')
    parts.append('<a href="#readme">README</a>')
    parts.append("</nav><main>")

    # Timeline
    parts.append('<section id="timeline"><h2>⏱ Timeline</h2>')
    parts.append(md_to_html(timeline_md) if timeline_md.strip() else '<p class="empty">아직 세션 기록 없음.</p>')
    parts.append("</section>")

    # Sections
    for key, title in SECTIONS:
        items = collect(key)
        parts.append(f'<section id="{key}"><h2>{title}</h2>')
        if not items:
            parts.append('<p class="empty">아직 항목 없음.</p>')
        else:
            for name, content in items:
                parts.append(f'<article><h3>{html.escape(name)}</h3>')
                parts.append(md_to_html(content))
                parts.append("</article>")
        parts.append("</section>")

    # README
    parts.append('<section id="readme"><h2>📖 README</h2>')
    parts.append(md_to_html(readme_md))
    parts.append("</section>")

    parts.append("</main><footer>Urban Immune System © Capstone Team · built by scripts/build_portfolio.py</footer>")
    parts.append("</body></html>")

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"✅ {OUT.relative_to(ROOT)} 빌드 ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
