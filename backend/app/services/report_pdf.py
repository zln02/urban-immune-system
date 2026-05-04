"""감염병 조기경보 PDF 리포트 생성기 (KDCA 주간 포맷 준수).

ReportLab + matplotlib 로 5~6페이지 구성:
  1) 표지 — ISO 주차, 지역, 위험 등급 색상 띠
  2) 핵심 지표 + 전주 대비 표 (증감 ▲▼)
  3) 3계층 시계열 — OTC / 하수 / 검색 (최근 12주 약 84일)
  4) 17개 시·도 현황 + Top 5 위험 지역 (신규)
  5) AI 분석 본문 + RAG 인용
  6) 면책 + 데이터 출처

폰트: NanumGothic (시스템 설치 가정 — 캡스톤 GCP VM에 기본 포함)
"""
# ruff: noqa: E501  -- ReportLab Paragraph 한국어 본문은 한 줄 유지가 가독성에 유리
from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── 폰트 등록 ─────────────────────────────────────────────────────
# CI / 폰트 미설치 환경(우분투 기본)에서도 import 가능하도록 모든 단계 fallback.
_NANUM_REG = "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"
_NANUM_BOLD = "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf"
if not Path(_NANUM_BOLD).exists():
    _NANUM_BOLD = "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"

if Path(_NANUM_REG).exists():
    try:
        pdfmetrics.registerFont(TTFont("NanumKR", _NANUM_REG))
        pdfmetrics.registerFont(TTFont("NanumKR-Bold", _NANUM_BOLD))
        _FONT = "NanumKR"
        _FONT_B = "NanumKR-Bold"
    except Exception as exc:
        logger.warning("나눔폰트 등록 실패: %s — Helvetica 폴백", exc)
        _FONT = _FONT_B = "Helvetica"
else:
    logger.warning("나눔폰트 미설치 (%s) — Helvetica 폴백", _NANUM_REG)
    _FONT = _FONT_B = "Helvetica"

# matplotlib 한글 — 폰트 있을 때만 적용
if Path(_NANUM_REG).exists():
    font_manager.fontManager.addfont(_NANUM_REG)
    plt.rcParams["font.family"] = "NanumBarunGothic"
plt.rcParams["axes.unicode_minus"] = False

# 색상 팔레트 (대시보드와 통일)
C_PHARMACY = "#be185d"
C_SEWAGE = "#047857"
C_SEARCH = "#1d4ed8"
C_PRIMARY = "#1e3a8a"
C_RED = "#dc2626"
C_ORANGE = "#ea580c"
C_YELLOW = "#facc15"
C_GREEN = "#16a34a"
C_YELLOW_OLD = "#d97706"  # 기존 색상 (지표 표시용)

LEVEL_COLOR = {
    "GREEN": C_GREEN,
    "YELLOW": C_YELLOW_OLD,
    "ORANGE": C_ORANGE,
    "RED": C_RED,
}
LEVEL_LABEL_KO = {
    "GREEN": "정상",
    "YELLOW": "주의",
    "ORANGE": "경계",
    "RED": "심각",
}

# 분석 산출물 경로 (정적 JSON)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LEAD_PATH = _PROJECT_ROOT / "analysis" / "outputs" / "lead_time_summary.json"
_BACKTEST_PATH = _PROJECT_ROOT / "analysis" / "outputs" / "backtest_17regions.json"


def _load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── ISO 주차 헬퍼 ────────────────────────────────────────────────
def _iso_week_label(dt: datetime) -> tuple[str, str]:
    """ISO 8601 주차 레이블 반환.

    Returns:
        (short_label, long_label) 예: ("2026-W18", "2026년 W18 (4월 27일 ~ 5월 3일)")
    """
    iso_year, iso_week, _ = dt.isocalendar()
    monday = dt - timedelta(days=dt.weekday())
    sunday = monday + timedelta(days=6)
    short = f"{iso_year}-W{iso_week:02d}"
    long = f"{iso_year}년 W{iso_week:02d} ({monday.strftime('%-m월 %-d일')} ~ {sunday.strftime('%-m월 %-d일')})"
    return short, long


# ── 색상 띠 + 푸터 (Canvas 직접 그리기) ───────────────────────────
class _UISDocTemplate(SimpleDocTemplate):
    """페이지 하단 푸터 + 표지 색상 띠 자동 삽입."""

    def __init__(self, *args, total_pages: int = 6, level: str = "GREEN",
                 generated_kst: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._total_pages = total_pages
        self._level = level
        self._generated_kst = generated_kst
        self._page_num = 0

    def handle_pageBegin(self) -> None:  # type: ignore[override]
        super().handle_pageBegin()
        self._page_num += 1

    def afterPage(self) -> None:
        """모든 페이지 하단에 "Page X / Y · UIS · 생성일" 푸터 삽입."""
        c = self.canv
        w, h = A4
        c.saveState()
        c.setFont(_FONT if _FONT != "Helvetica" else "Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#6b7280"))
        footer_text = f"Page {self._page_num} / {self._total_pages}  ·  UIS (Urban Immune System)  ·  생성일 {self._generated_kst}"
        c.drawCentredString(w / 2, 8 * mm, footer_text)
        c.restoreState()


def _alert_band_canvas(canvas, level: str) -> None:
    """표지 상단에 위험 등급 색상 띠를 그림 (Page 1 전용)."""
    band_color_map = {
        "GREEN": C_GREEN,
        "YELLOW": "#d97706",
        "ORANGE": C_ORANGE,
        "RED": C_RED,
    }
    c = band_color_map.get(level, C_GREEN)
    w, _ = A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(c))
    canvas.rect(0, A4[1] - 14 * mm, w, 14 * mm, fill=1, stroke=0)
    canvas.setFont(_FONT_B if _FONT_B != "Helvetica" else "Helvetica-Bold", 10)
    canvas.setFillColor(colors.white)
    label_ko = LEVEL_LABEL_KO.get(level, level)
    canvas.drawCentredString(w / 2, A4[1] - 9 * mm, f"위험 등급: {level}  ({label_ko})")
    canvas.restoreState()


# ── 차트 생성 ────────────────────────────────────────────────────
def _chart_three_layer(
    composite: list[tuple],
    l1: list[tuple],
    l2: list[tuple],
    l3: list[tuple],
    days: int = 84,
) -> bytes:
    """4계층 시계열 (composite + L1/L2/L3) + alert_level 음영. 최근 12주(84일) 기준."""
    fig, axes = plt.subplots(4, 1, figsize=(8.0, 8.0), sharex=True)
    fig.subplots_adjust(hspace=0.38, top=0.94, bottom=0.07, left=0.10, right=0.96)

    datasets = [
        (axes[0], composite, C_PRIMARY, "Composite (종합 위험도)"),
        (axes[1], l1, C_PHARMACY, "L1 약국 OTC (Naver 쇼핑인사이트)"),
        (axes[2], l2, C_SEWAGE, "L2 하수 바이오마커 (KOWAS)"),
        (axes[3], l3, C_SEARCH, "L3 검색 트렌드 (Naver DataLab)"),
    ]

    for ax, data, color, label in datasets:
        if data:
            xs = [d[0] for d in data]
            ys = [d[1] for d in data]
            ax.plot(xs, ys, color=color, lw=1.6)
            ax.fill_between(xs, ys, alpha=0.14, color=color)
        ax.set_title(label, fontsize=9.5, loc="left", color="#111827", weight="bold")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="both", labelsize=7.5)
        # alert_level 음영 (YELLOW/ORANGE/RED)
        ax.axhspan(55, 70, alpha=0.06, color=C_YELLOW_OLD, label="YELLOW")
        ax.axhspan(70, 85, alpha=0.06, color=C_ORANGE, label="ORANGE")
        ax.axhspan(85, 100, alpha=0.06, color=C_RED, label="RED")

    axes[3].set_xlabel(f"주차 (최근 {days}일 / 약 12주)", fontsize=8.5)
    fig.suptitle("3계층 신호 + 종합 시계열 (정규화 0–100)", fontsize=11.5, weight="bold", y=0.995)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _chart_top5_regions(regions_data: list[dict]) -> bytes:
    """Top 5 위험 지역 수평 막대차트."""
    top5 = sorted(regions_data, key=lambda x: x.get("composite", 0), reverse=True)[:5]
    labels = [r["region"] for r in top5]
    vals = [r.get("composite", 0) for r in top5]
    level_colors = [LEVEL_COLOR.get(r.get("level", "GREEN"), C_GREEN) for r in top5]

    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    bars = ax.barh(labels[::-1], vals[::-1], color=level_colors[::-1], height=0.55)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 0.8, b.get_y() + b.get_height() / 2, f"{v:.1f}",
                va="center", fontsize=9, weight="bold", color="#111827")
    ax.set_xlim(0, 100)
    ax.set_title("Top 5 위험 지역 (composite score)", fontsize=10.5, weight="bold", loc="left")
    ax.set_xlabel("composite score", fontsize=9)
    ax.axvline(55, ls="--", color=C_YELLOW_OLD, lw=1, alpha=0.7, label="YELLOW 55")
    ax.axvline(70, ls="--", color=C_ORANGE, lw=1, alpha=0.7, label="ORANGE 70")
    ax.axvline(85, ls="--", color=C_RED, lw=1, alpha=0.7, label="RED 85")
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _chart_lead_time(lead: dict) -> bytes:
    """선행시간 (주) 막대그래프."""
    weeks = lead.get("signal_lead_weeks", {})
    ccf = lead.get("ccf_max", {})
    granger = lead.get("granger_p", {})
    keys = ["l1_otc", "l2_wastewater", "l3_search", "composite"]
    labels = ["L1 OTC", "L2 하수", "L3 검색", "Composite"]
    colors_ = [C_PHARMACY, C_SEWAGE, C_SEARCH, C_PRIMARY]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.0, 3.4))

    # 선행 주
    vals = [weeks.get(k, 0) for k in keys]
    bars = ax1.bar(labels, vals, color=colors_)
    ax1.set_title("KCDC 임상 peak 대비 선행 주", fontsize=10, weight="bold", loc="left")
    ax1.set_ylabel("주 (weeks)", fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.3)
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.1, f"{v}주",
                 ha="center", fontsize=9, weight="bold")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Granger p + CCF
    p_vals = [granger.get(k, 1.0) for k in keys]
    ccf_vals = [ccf.get(k, 0.0) for k in keys]
    x = range(len(keys))
    width = 0.38
    ax2.bar([i - width / 2 for i in x], p_vals, width, label="Granger p", color="#374151")
    ax2.bar([i + width / 2 for i in x], ccf_vals, width, label="CCF max", color="#9ca3af")
    ax2.axhline(0.05, ls="--", color=C_RED, lw=1, alpha=0.7, label="α=0.05")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_title("인과성 검정 (Granger p < 0.05 = 유의)", fontsize=10, weight="bold", loc="left")
    ax2.legend(fontsize=7, loc="upper right")
    ax2.set_ylim(0, 1.0)
    ax2.grid(axis="y", linestyle="--", alpha=0.3)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _chart_backtest(backtest: dict) -> bytes:
    """17지역 백테스트 결과."""
    summary = backtest.get("summary", {})
    metrics = {
        "Recall": summary.get("mean_recall", 0),
        "Precision": summary.get("mean_precision", 0),
        "F1": summary.get("mean_f1", 0),
        "FAR": summary.get("mean_far_with_gate", 0),
    }
    targets = {"Recall": 0.85, "Precision": 0.5, "F1": 0.70, "FAR": 0.55}

    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    labels = list(metrics.keys())
    vals = list(metrics.values())
    colors_ = [C_GREEN if k != "FAR" else C_RED for k in labels]

    bars = ax.barh(labels, vals, color=colors_, height=0.55)
    for k, b, v in zip(labels, bars, vals):
        t = targets[k]
        ax.axvline(t, ymin=(b.get_y() - ax.get_ylim()[0]) / (ax.get_ylim()[1] - ax.get_ylim()[0]),
                   color="#6b7280", lw=0.8, ls=":", alpha=0.6)
        ax.text(v + 0.015, b.get_y() + b.get_height() / 2, f"{v:.3f}",
                va="center", fontsize=9, weight="bold")
    ax.set_xlim(0, 1.0)
    ax.set_title("17개 시·도 백테스트 결과 (2025-W40 ~ 2026-W08)",
                 fontsize=10.5, weight="bold", loc="left")
    ax.set_xlabel("score", fontsize=9)
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.invert_yaxis()

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# ── 데이터 조회 ────────────────────────────────────────────────
async def _fetch_layer_series(db: AsyncSession, region: str, layer: str, days: int = 84) -> list[tuple]:
    rows = (await db.execute(
        text(f"""
            SELECT time, value FROM layer_signals
            WHERE region = :region AND layer = :layer
              AND time >= NOW() - INTERVAL '{int(days)} days'
            ORDER BY time
        """),
        {"region": region, "layer": layer},
    )).all()
    return [(r[0], float(r[1])) for r in rows]


async def _fetch_composite_series(db: AsyncSession, region: str, days: int = 84) -> list[tuple]:
    """composite_score 시계열 (risk_scores 테이블)."""
    rows = (await db.execute(
        text(f"""
            SELECT time, composite_score FROM risk_scores
            WHERE region = :region
              AND time >= NOW() - INTERVAL '{int(days)} days'
            ORDER BY time
        """),
        {"region": region},
    )).all()
    return [(r[0], float(r[1])) for r in rows]


async def _fetch_latest_risk(db: AsyncSession, region: str) -> dict | None:
    row = (await db.execute(
        text("""
            SELECT time, composite_score, l1_score, l2_score, l3_score, alert_level
            FROM risk_scores WHERE region = :region
            ORDER BY time DESC LIMIT 1
        """),
        {"region": region},
    )).mappings().first()
    return dict(row) if row else None


async def _fetch_prev_risk(db: AsyncSession, region: str) -> dict | None:
    """전주 위험도 (최신에서 2번째 row)."""
    row = (await db.execute(
        text("""
            SELECT time, composite_score, l1_score, l2_score, l3_score, alert_level
            FROM risk_scores WHERE region = :region
            ORDER BY time DESC LIMIT 1 OFFSET 1
        """),
        {"region": region},
    )).mappings().first()
    return dict(row) if row else None


async def _fetch_all_regions_latest(db: AsyncSession) -> list[dict]:
    """17개 시·도 최신 composite 점수 조회."""
    rows = (await db.execute(
        text("""
            SELECT DISTINCT ON (region) region, composite_score, alert_level
            FROM risk_scores
            ORDER BY region, time DESC
        """),
    )).mappings().all()
    return [{"region": r["region"], "composite": float(r["composite_score"] or 0),
             "level": str(r["alert_level"] or "GREEN")} for r in rows]


async def _fetch_latest_report(db: AsyncSession, region: str) -> dict | None:
    row = (await db.execute(
        text("""
            SELECT region, alert_level, summary, recommendations, model_used, created_at, rag_sources
            FROM alert_reports WHERE region = :region
            ORDER BY created_at DESC LIMIT 1
        """),
        {"region": region},
    )).mappings().first()
    return dict(row) if row else None


# ── 증감 화살표 포맷 ─────────────────────────────────────────────
def _delta_str(current: float, previous: float | None) -> str:
    if previous is None:
        return "-"
    diff = current - previous
    if abs(diff) < 0.01:
        return "±0.0%"
    arrow = "▲" if diff > 0 else "▼"
    pct = abs(diff / previous * 100) if previous != 0 else abs(diff)
    return f"{arrow}{pct:.1f}%"


def _delta_color(current: float, previous: float | None) -> str:
    if previous is None:
        return "#374151"
    return C_RED if current > previous else C_GREEN


# ── 마크다운 → Paragraph 변환 ────────────────────────────────────
def _md_to_paragraphs(text_md: str, base: ParagraphStyle, h2: ParagraphStyle, h3: ParagraphStyle) -> list:
    story_parts: list = []
    for raw_para in text_md.split("\n"):
        line = raw_para.strip()
        if not line:
            story_parts.append(Spacer(1, 2 * mm))
            continue
        if line.startswith("# "):
            story_parts.append(Paragraph(line[2:].strip(), h2))
        elif line.startswith("## "):
            story_parts.append(Paragraph(line[3:].strip(), h3))
        elif line.startswith("### "):
            story_parts.append(Paragraph(line[4:].strip(), h3))
        else:
            html = line.replace("**", "§§")
            parts = html.split("§§")
            rebuilt = ""
            for i, p in enumerate(parts):
                rebuilt += f"<b>{p}</b>" if i % 2 == 1 else p
            if rebuilt.startswith("- ") or rebuilt.startswith("* "):
                rebuilt = "• " + rebuilt[2:]
            story_parts.append(Paragraph(rebuilt, base))
    return story_parts


# ── RAG 인용 포맷 ────────────────────────────────────────────────
def _format_citation(idx: int, c: dict) -> str:
    """[번호] 저자(연도). 제목. (출처). 형식으로 포맷."""
    if isinstance(c, dict):
        author = c.get("author", "")
        year = c.get("year", "")
        title = c.get("topic", c.get("title", ""))
        source = c.get("source", "출처 미상")
        url = c.get("url", "")
        if author and year:
            cite = f"[{idx}] {author} ({year}). {title}. ({source})."
        else:
            cite = f"[{idx}] {title or source}. ({source})."
        if url:
            cite += f" URL: {url}"
    else:
        cite = f"[{idx}] {str(c)}"
    return cite


# ── 핵심 PDF 빌드 (신규 6페이지 버전) ───────────────────────────
async def _build_pdf_story(
    region: str,
    db: AsyncSession | None,
    *,
    risk: dict | None = None,
    prev_risk: dict | None = None,
    rep: dict | None = None,
    all_regions: list[dict] | None = None,
) -> tuple[list, str, str]:
    """PDF story 리스트 + 생성시각 KST + 위험등급 반환."""
    now_utc = datetime.now(timezone.utc)
    now_kst = (now_utc + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")
    iso_short, iso_long = _iso_week_label(now_utc + timedelta(hours=9))

    # DB 조회 (db가 None이면 빈 데이터 사용 — 테스트·파일 저장용)
    if db is not None:
        risk = risk or await _fetch_latest_risk(db, region) or {}
        prev_risk = prev_risk or await _fetch_prev_risk(db, region)
        rep = rep or await _fetch_latest_report(db, region) or {}
        all_regions = all_regions or await _fetch_all_regions_latest(db)
        composite_series = await _fetch_composite_series(db, region)
        l1_series = await _fetch_layer_series(db, region, "otc")
        l2_series = await _fetch_layer_series(db, region, "wastewater")
        l3_series = await _fetch_layer_series(db, region, "search")
    else:
        risk = risk or {}
        prev_risk = prev_risk
        rep = rep or {}
        all_regions = all_regions or []
        composite_series = []
        l1_series = []
        l2_series = []
        l3_series = []

    level = risk.get("alert_level") or rep.get("alert_level") or "GREEN"
    level_ko = LEVEL_LABEL_KO.get(level, level)
    level_color = LEVEL_COLOR.get(level, "#374151")
    composite = float(risk.get("composite_score") or 0)

    # 스타일 정의
    styles = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=styles["Normal"], fontName=_FONT, fontSize=10, leading=15, textColor=colors.HexColor("#111827"))
    h1 = ParagraphStyle("h1", parent=base, fontName=_FONT_B, fontSize=20, leading=26, textColor=colors.HexColor(C_PRIMARY), spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base, fontName=_FONT_B, fontSize=14, leading=20, textColor=colors.HexColor(C_PRIMARY), spaceBefore=6, spaceAfter=4)
    h3 = ParagraphStyle("h3", parent=base, fontName=_FONT_B, fontSize=11, leading=16, textColor=colors.HexColor("#1f2937"), spaceBefore=4)
    small = ParagraphStyle("small", parent=base, fontSize=8.5, leading=12, textColor=colors.HexColor("#6b7280"))
    big_level = ParagraphStyle("big_level", parent=base, fontName=_FONT_B, fontSize=28, leading=36, textColor=colors.HexColor(level_color))

    story: list = []

    # ─── Page 1 — 표지 ───────────────────────────────────────────
    # 색상 띠는 afterPage 콜백에서 처리할 수 없으므로 Spacer로 공간 확보
    story.append(Spacer(1, 16 * mm))  # 상단 색상 띠 공간 (14mm 띠 + 여백)
    story.append(Paragraph("도시 면역 시스템 — 감염병 주간 동향 보고서", h1))
    story.append(Paragraph(f"{region} (전국 17개 시·도 종합)", h2))
    story.append(Spacer(1, 4 * mm))

    # ISO 주차
    week_table = Table(
        [[Paragraph("<b>발행 주차</b>", base), Paragraph(f"<b>{iso_short}</b>", h3),
          Paragraph("<b>한국식</b>", base), Paragraph(iso_long, base)]],
        colWidths=[28 * mm, 38 * mm, 22 * mm, 82 * mm],
    )
    week_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#eff6ff")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#eff6ff")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(week_table)
    story.append(Spacer(1, 6 * mm))

    # 위험 등급 + 발행 기관
    story.append(Paragraph(f'<font color="{level_color}"><b>{level} ({level_ko})</b></font>', big_level))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"composite score: <b>{composite:.2f}</b> / 100", base))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("발행 기관: Urban Immune System (UIS) — 캡스톤 프로젝트팀", small))
    story.append(Paragraph(f"발행 일시: {now_kst}", small))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "* 본 리포트는 AI가 자동 생성한 보조 의사결정 자료이며 임상·정책 의사결정에 활용 시 인간 전문가 검토가 필수입니다 (ISMS-P 2.9).",
        small))
    story.append(PageBreak())

    # ─── Page 2 — 핵심 지표 + 전주 대비 ─────────────────────────
    story.append(Paragraph("1. 핵심 지표 — 전주 대비", h2))

    cur_l1 = float(risk.get("l1_score") or 0)
    cur_l2 = float(risk.get("l2_score") or 0)
    cur_l3 = float(risk.get("l3_score") or 0)
    prev_comp = float(prev_risk.get("composite_score") or 0) if prev_risk else None
    prev_l1 = float(prev_risk.get("l1_score") or 0) if prev_risk else None
    prev_l2 = float(prev_risk.get("l2_score") or 0) if prev_risk else None
    prev_l3 = float(prev_risk.get("l3_score") or 0) if prev_risk else None

    def _colored_delta(cur: float, prev: float | None) -> str:
        ds = _delta_str(cur, prev)
        dc = _delta_color(cur, prev)
        return f'<font color="{dc}"><b>{ds}</b></font>'

    header_style = ParagraphStyle("th", parent=base, fontName=_FONT_B, fontSize=9.5, leading=13, textColor=colors.HexColor("#1e3a8a"))
    metric_data = [
        [Paragraph("<b>지표</b>", header_style), Paragraph("<b>현주</b>", header_style),
         Paragraph("<b>전주</b>", header_style), Paragraph("<b>증감</b>", header_style), Paragraph("<b>경보레벨</b>", header_style)],
        [Paragraph("Composite", base), Paragraph(f"<b>{composite:.2f}</b>", base),
         Paragraph(f"{prev_comp:.2f}" if prev_comp is not None else "-", base),
         Paragraph(_colored_delta(composite, prev_comp), base),
         Paragraph(f'<font color="{level_color}"><b>{level}</b></font>', base)],
        [Paragraph("L1 약국 OTC", base), Paragraph(f"{cur_l1:.2f}", base),
         Paragraph(f"{prev_l1:.2f}" if prev_l1 is not None else "-", base),
         Paragraph(_colored_delta(cur_l1, prev_l1), base), Paragraph("-", base)],
        [Paragraph("L2 하수 바이오마커", base), Paragraph(f"{cur_l2:.2f}", base),
         Paragraph(f"{prev_l2:.2f}" if prev_l2 is not None else "-", base),
         Paragraph(_colored_delta(cur_l2, prev_l2), base), Paragraph("-", base)],
        [Paragraph("L3 검색 트렌드", base), Paragraph(f"{cur_l3:.2f}", base),
         Paragraph(f"{prev_l3:.2f}" if prev_l3 is not None else "-", base),
         Paragraph(_colored_delta(cur_l3, prev_l3), base), Paragraph("-", base)],
    ]
    metric_table = Table(metric_data, colWidths=[46 * mm, 28 * mm, 28 * mm, 28 * mm, 40 * mm])
    metric_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f9fafb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 4 * mm))

    # 한 줄 요약
    dominant = "L2 하수 신호" if cur_l2 >= max(cur_l1, cur_l3) else ("L1 약국 OTC" if cur_l1 >= cur_l3 else "L3 검색 트렌드")
    delta_composite_str = _delta_str(composite, prev_comp)
    story.append(Paragraph(
        f"요약: composite {delta_composite_str} 변동, {dominant} 주도 | 발행일 {now_kst}",
        ParagraphStyle("summary_line", parent=base, fontName=_FONT_B, fontSize=10, leading=14,
                       textColor=colors.HexColor(C_PRIMARY), borderColor=colors.HexColor("#bfdbfe"),
                       borderWidth=1, borderPadding=5, backColor=colors.HexColor("#eff6ff")),
    ))
    story.append(PageBreak())

    # ─── Page 3 — 시계열 차트 ────────────────────────────────────
    story.append(Paragraph("2. 3계층 신호 시계열 (최근 12주)", h2))
    story.append(Paragraph(
        "각 계층은 0–100 정규화. YELLOW(55–70) / ORANGE(70–85) / RED(85+) 음영 표시. "
        "단일 계층만으로 경보 발령 금지 (Google Flu Trends 과대예측 교훈). 2개 이상 계층 교차검증 필요.",
        small))
    story.append(Spacer(1, 3 * mm))
    chart3_bytes = _chart_three_layer(composite_series, l1_series, l2_series, l3_series)
    story.append(Image(io.BytesIO(chart3_bytes), width=170 * mm, height=150 * mm))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"데이터 포인트: composite {len(composite_series)}점 · OTC {len(l1_series)}점 · 하수 {len(l2_series)}점 · 검색 {len(l3_series)}점",
        small))
    story.append(PageBreak())

    # ─── Page 4 — 17개 시·도 현황 + Top 5 ───────────────────────
    story.append(Paragraph("3. 전국 17개 시·도 현황", h2))

    if all_regions:
        sorted_regions = sorted(all_regions, key=lambda x: x.get("composite", 0), reverse=True)
        region_header = [
            Paragraph("<b>지역</b>", header_style),
            Paragraph("<b>Composite</b>", header_style),
            Paragraph("<b>경보 레벨</b>", header_style),
        ]
        region_rows = [region_header]
        for rd in sorted_regions:
            lvl = rd.get("level", "GREEN")
            lc = LEVEL_COLOR.get(lvl, "#374151")
            region_rows.append([
                Paragraph(rd["region"], ParagraphStyle("rbase", parent=base, fontSize=8.5, leading=12)),
                Paragraph(f"{rd.get('composite', 0):.2f}", ParagraphStyle("rbase2", parent=base, fontSize=8.5, leading=12)),
                Paragraph(f'<font color="{lc}"><b>{lvl}</b></font>', ParagraphStyle("rbase3", parent=base, fontSize=8.5, leading=12)),
            ])

        region_table = Table(region_rows, colWidths=[80 * mm, 45 * mm, 45 * mm])
        region_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d1d5db")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(region_table)
        story.append(Spacer(1, 5 * mm))

        # Top 5 막대차트
        story.append(Paragraph("Top 5 위험 지역", h3))
        top5_bytes = _chart_top5_regions(all_regions)
        story.append(Image(io.BytesIO(top5_bytes), width=170 * mm, height=65 * mm))
    else:
        story.append(Paragraph("(DB 데이터 없음 — risk_scores 테이블 미입력)", small))

    story.append(PageBreak())

    # ─── Page 5 — AI 분석 본문 + RAG 인용 ───────────────────────
    story.append(Paragraph("4. AI 분석 리포트 (전문)", h2))
    story.append(Paragraph(f"모델: {rep.get('model_used') or '-'} · 생성 시각: {rep.get('created_at') or '-'}", small))
    story.append(Spacer(1, 4 * mm))

    summary_text = (rep.get("summary") or "alert_reports DB에 해당 지역 리포트가 없습니다. /api/v1/alerts/stream 호출 후 다시 시도하세요.").strip()
    story.extend(_md_to_paragraphs(summary_text, base, h2, h3))

    # RAG 인용
    rag = rep.get("rag_sources")
    if rag:
        if isinstance(rag, str):
            try:
                rag = json.loads(rag)
            except Exception:
                rag = []
        if rag:
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph("참고 문헌 (Qdrant RAG)", h3))
            for i, c in enumerate(rag[:5], 1):
                cite_line = _format_citation(i, c)
                story.append(Paragraph(cite_line, small))

    story.append(PageBreak())

    # ─── Page 6 — 면책 + 데이터 출처 ────────────────────────────
    story.append(Paragraph("5. 데이터 출처 및 면책 사항", h2))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("[데이터 출처]", h3))
    sources_data = [
        ["계층", "출처", "수집 주기"],
        ["L1 약국 OTC", "네이버 쇼핑인사이트 (Naver Shopping Insight)", "주간 (월요일)"],
        ["L2 하수 바이오마커", "KOWAS — 환경부·질병관리청 공동 운영", "주간 (화요일 발표)"],
        ["L3 검색 트렌드", "네이버 DataLab (Naver DataLab)", "주간 집계"],
        ["임상 기준", "KCDC 표본감시 (ILINet) — 질병관리청", "주간"],
    ]
    src_header_style = ParagraphStyle("srch", parent=base, fontName=_FONT_B, fontSize=9, leading=13)
    src_body_style = ParagraphStyle("srcb", parent=base, fontSize=8.5, leading=12)
    src_rows = [
        [Paragraph(cell, src_header_style if row_idx == 0 else src_body_style)
         for cell in row]
        for row_idx, row in enumerate(sources_data)
    ]
    src_table = Table(src_rows, colWidths=[42 * mm, 90 * mm, 38 * mm])
    src_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(src_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("[면책 사항]", h3))
    story.append(Paragraph(
        "본 리포트는 AI가 생성한 보조 의사결정 자료이며, 공중보건 정책 수립 시 인간 전문가(역학조사관, 보건당국)의 검토를 거쳐야 합니다. "
        "(ISMS-P 2.9 / EU AI Act 준수)",
        base))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "본 시스템의 신호는 확진 사례가 아닌 간접 지표(OTC 구매·하수 바이오마커·검색어 트렌드)에 기반하며, "
        "임상 진단 또는 처방의 대체 수단으로 사용될 수 없습니다. "
        "경보 발령은 항상 2개 이상 계층 교차검증을 전제로 합니다.",
        small))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "UIS 캡스톤 프로젝트팀 — 팀원: 박진영(PM/ML) · 이경준(Backend) · 이우형(Data Engineer) · 김나영(Frontend) · 박정빈(DevOps/QA)",
        small))
    story.append(Paragraph(f"생성 일시: {now_kst}", small))

    return story, now_kst, level


# ── 공개 API ────────────────────────────────────────────────────
async def build_alert_pdf(region: str, db: AsyncSession) -> bytes:
    """region에 대한 6페이지 PDF 리포트를 bytes로 반환 (기존 호출자 호환 유지)."""
    now_kst_str = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")
    risk = await _fetch_latest_risk(db, region) or {}
    level = risk.get("alert_level") or "GREEN"

    buf = io.BytesIO()
    doc = _UISDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
        title=f"UIS 감염병 주간 동향 — {region}",
        total_pages=6,
        level=level,
        generated_kst=now_kst_str,
    )

    story, now_kst, cur_level = await _build_pdf_story(region, db)

    def _on_page(canvas, doc):
        _alert_band_canvas(canvas, cur_level) if doc.page == 1 else None

    doc.build(story, onFirstPage=_on_page, onLaterPages=lambda c, d: None)
    return buf.getvalue()


async def build_pdf(
    region: str,
    output_path: str,
    db: AsyncSession | None = None,
    *,
    risk: dict | None = None,
    prev_risk: dict | None = None,
    rep: dict | None = None,
    all_regions: list[dict] | None = None,
) -> None:
    """PDF를 파일로 저장 (테스트·CLI 용도).

    db=None 이면 mock 데이터(risk/rep/all_regions)로 생성 가능.
    """
    now_kst_str = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")
    _risk = risk or {}
    level = _risk.get("alert_level") or "GREEN"

    buf = io.BytesIO()
    doc = _UISDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
        title=f"UIS 감염병 주간 동향 — {region}",
        total_pages=6,
        level=level,
        generated_kst=now_kst_str,
    )

    story, now_kst, cur_level = await _build_pdf_story(
        region, db,
        risk=risk, prev_risk=prev_risk, rep=rep, all_regions=all_regions,
    )

    def _on_page(canvas, doc_inner):
        if doc_inner.page == 1:
            _alert_band_canvas(canvas, cur_level)

    doc.build(story, onFirstPage=_on_page, onLaterPages=lambda c, d: None)
    Path(output_path).write_bytes(buf.getvalue())
