#!/usr/bin/env python3
"""Markdown → PDF 변환기 (fpdf2 + python-markdown + NanumGothic).

사용법:
    python scripts/reports_to_pdf.py <paths...>
    python scripts/reports_to_pdf.py docs/weekly-reports/guides/

각 .md 파일을 동일 경로의 .pdf 로 변환한다. 순수 Python 의존성만 사용 (Java 불필요).
"""
from __future__ import annotations

import sys
from pathlib import Path

import markdown
from fpdf import FPDF

NANUM_REG = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
NANUM_BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
NANUM_MONO = "/usr/share/fonts/truetype/nanum/NanumGothicCoding.ttf"
NANUM_MONO_B = "/usr/share/fonts/truetype/nanum/NanumGothicCodingBold.ttf"


class MDPdf(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(16, 18, 16)
        self.add_font("Nanum", "", NANUM_REG)
        self.add_font("Nanum", "B", NANUM_BOLD)
        self.add_font("Nanum", "I", NANUM_REG)  # italic fallback
        self.add_font("Nanum", "BI", NANUM_BOLD)
        self.add_font("NanumMono", "", NANUM_MONO)
        self.add_font("NanumMono", "B", NANUM_MONO_B)
        self.add_font("NanumMono", "I", NANUM_MONO)
        self.add_font("NanumMono", "BI", NANUM_MONO_B)
        self.set_font("Nanum", size=10)
        self.add_page()

    def render_html(self, html: str):
        self.write_html(
            html,
            font_family="Nanum",
            pre_code_font="NanumMono",
            table_line_separators=True,
        )


import re

_CELL_RE = re.compile(r"<(td|th)(\s[^>]*)?>(.*?)</\1>", flags=re.DOTALL)
_INNER_TAG_RE = re.compile(r"<(?!/?(td|th|tr|table|tbody|thead)\b)[^>]+>")


def _strip_cell_inner_tags(m: re.Match) -> str:
    tag, attrs, inner = m.group(1), m.group(2) or "", m.group(3)
    cleaned = _INNER_TAG_RE.sub("", inner)
    return f"<{tag}{attrs}>{cleaned}</{tag}>"


def md_to_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    html = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    html = html.replace("<hr />", "<hr>")
    # fpdf2 write_html 은 <td> 안의 중첩 태그를 지원하지 않으므로 스트립
    html = _CELL_RE.sub(_strip_cell_inner_tags, html)
    return html


def convert_one(md_path: Path) -> Path:
    pdf = MDPdf()
    pdf.render_html(md_to_html(md_path))
    out = md_path.with_suffix(".pdf")
    pdf.output(str(out))
    return out


def collect_md(paths: list[str]) -> list[Path]:
    result: list[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            result.extend(sorted(pp.rglob("*.md")))
        elif pp.suffix == ".md":
            result.append(pp)
    return result


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    md_files = collect_md(argv)
    if not md_files:
        print("변환할 .md 파일 없음", file=sys.stderr)
        return 1
    print(f"변환 대상 {len(md_files)}개")
    ok, fail = 0, 0
    for md in md_files:
        try:
            pdf = convert_one(md)
            print(f"✅ {md.name} → {pdf.name}")
            ok += 1
        except Exception as e:
            print(f"❌ {md.name}: {e}", file=sys.stderr)
            fail += 1
    print(f"\n완료: {ok}개 성공, {fail}개 실패")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
