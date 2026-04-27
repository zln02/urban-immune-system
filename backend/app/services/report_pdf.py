"""감염병 조기경보 PDF 리포트 생성기.

ReportLab + matplotlib 로 4페이지 구성:
  1) 표지 — 지역, alert_level, composite, AI 요약 박스
  2) 3계층 시계열 — OTC / 하수 / 검색 (90일)
  3) 분석 근거 — 선행시간 / Granger / CCF / 17지역 백테스트 metric
  4) AI 리포트 본문 + RAG 인용

폰트: NanumGothic (시스템 설치 가정 — 캡스톤 GCP VM에 기본 포함)
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
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
_NANUM_REG = "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"
_NANUM_BOLD = "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf"
if not Path(_NANUM_BOLD).exists():
    _NANUM_BOLD = "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"

try:
    pdfmetrics.registerFont(TTFont("NanumKR", _NANUM_REG))
    pdfmetrics.registerFont(TTFont("NanumKR-Bold", _NANUM_BOLD))
    _FONT = "NanumKR"
    _FONT_B = "NanumKR-Bold"
except Exception as exc:
    logger.warning("나눔폰트 등록 실패: %s", exc)
    _FONT = _FONT_B = "Helvetica"

# matplotlib 한글
font_manager.fontManager.addfont(_NANUM_REG)
plt.rcParams["font.family"] = "NanumBarunGothic"
plt.rcParams["axes.unicode_minus"] = False

# 색상 팔레트 (대시보드와 통일)
C_PHARMACY = "#be185d"
C_SEWAGE = "#047857"
C_SEARCH = "#1d4ed8"
C_PRIMARY = "#1e3a8a"
C_RED = "#dc2626"
C_YELLOW = "#d97706"
C_GREEN = "#059669"

LEVEL_COLOR = {"GREEN": C_GREEN, "YELLOW": C_YELLOW, "ORANGE": "#ea580c", "RED": C_RED}

# 분석 산출물 경로 (정적 JSON)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LEAD_PATH = _PROJECT_ROOT / "analysis" / "outputs" / "lead_time_summary.json"
_BACKTEST_PATH = _PROJECT_ROOT / "analysis" / "outputs" / "backtest_17regions.json"


def _load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── 차트 생성 ────────────────────────────────────────────────────
def _chart_three_layer(otc: list[tuple], sewage: list[tuple], search: list[tuple]) -> bytes:
    """3계층 시계열 (3 stacked subplots)."""
    fig, axes = plt.subplots(3, 1, figsize=(8.0, 6.5), sharex=True)
    fig.subplots_adjust(hspace=0.35, top=0.95, bottom=0.08, left=0.10, right=0.96)

    for ax, data, color, label in [
        (axes[0], otc, C_PHARMACY, "L1 약국 OTC (Naver 쇼핑인사이트)"),
        (axes[1], sewage, C_SEWAGE, "L2 하수 바이오마커 (KOWAS)"),
        (axes[2], search, C_SEARCH, "L3 검색 트렌드 (Naver DataLab)"),
    ]:
        if data:
            xs = [d[0] for d in data]
            ys = [d[1] for d in data]
            ax.plot(xs, ys, color=color, lw=1.6)
            ax.fill_between(xs, ys, alpha=0.14, color=color)
        ax.set_title(label, fontsize=10, loc="left", color="#111827", weight="bold")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="both", labelsize=8)

    axes[2].set_xlabel("주차 (최근 90일)", fontsize=9)
    fig.suptitle("3계층 신호 시계열 (정규화 0–100)", fontsize=12, weight="bold", y=0.995)

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
async def _fetch_layer_series(db: AsyncSession, region: str, layer: str, days: int = 90) -> list[tuple]:
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


# ── PDF 빌드 ─────────────────────────────────────────────────────
async def build_alert_pdf(region: str, db: AsyncSession) -> bytes:
    """region 에 대한 4페이지 PDF 리포트를 bytes 로 반환."""
    risk = await _fetch_latest_risk(db, region) or {}
    rep = await _fetch_latest_report(db, region) or {}
    otc = await _fetch_layer_series(db, region, "otc")
    sew = await _fetch_layer_series(db, region, "wastewater", days=180)
    sea = await _fetch_layer_series(db, region, "search")

    lead = _load_json(_LEAD_PATH)
    backtest = _load_json(_BACKTEST_PATH)

    chart3 = _chart_three_layer(otc, sew, sea)
    chartLead = _chart_lead_time(lead)
    chartBT = _chart_backtest(backtest)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"UIS 감염병 조기경보 — {region}",
    )

    styles = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=styles["Normal"], fontName=_FONT, fontSize=10, leading=15, textColor=colors.HexColor("#111827"))
    h1 = ParagraphStyle("h1", parent=base, fontName=_FONT_B, fontSize=22, leading=28, textColor=colors.HexColor(C_PRIMARY), spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base, fontName=_FONT_B, fontSize=14, leading=20, textColor=colors.HexColor(C_PRIMARY), spaceBefore=6, spaceAfter=4)
    h3 = ParagraphStyle("h3", parent=base, fontName=_FONT_B, fontSize=11, leading=16, textColor=colors.HexColor("#1f2937"), spaceBefore=4)
    small = ParagraphStyle("small", parent=base, fontSize=8.5, leading=12, textColor=colors.HexColor("#6b7280"))

    story: list = []

    # ─── Page 1 — 표지
    story.append(Paragraph("Urban Immune System", h2))
    story.append(Paragraph("감염병 조기경보 리포트", h1))
    story.append(Spacer(1, 4 * mm))
    now_kst = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    composite = risk.get("composite_score", 0) or 0
    level = risk.get("alert_level") or rep.get("alert_level") or "GREEN"
    level_color = LEVEL_COLOR.get(level, "#374151")

    summary_table = Table(
        [
            [Paragraph("<b>지역</b>", base), Paragraph(region, base),
             Paragraph("<b>발령 시점</b>", base), Paragraph(now_kst, base)],
            [Paragraph("<b>경보 레벨</b>", base),
             Paragraph(f'<font color="{level_color}"><b>{level}</b></font>', base),
             Paragraph("<b>composite score</b>", base),
             Paragraph(f"<b>{float(composite):.2f}</b> / 100", base)],
            [Paragraph("<b>L1 OTC</b>", base), Paragraph(f"{float(risk.get('l1_score') or 0):.2f}", base),
             Paragraph("<b>L2 하수</b>", base), Paragraph(f"{float(risk.get('l2_score') or 0):.2f}", base)],
            [Paragraph("<b>L3 검색</b>", base), Paragraph(f"{float(risk.get('l3_score') or 0):.2f}", base),
             Paragraph("<b>모델</b>", base), Paragraph(rep.get("model_used") or "fallback ensemble", base)],
        ],
        colWidths=[28 * mm, 50 * mm, 28 * mm, 64 * mm],
    )
    summary_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f9fafb")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f9fafb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("AI 요약 (Claude RAG)", h2))
    summary_text = (rep.get("summary") or "alert_reports DB에 해당 지역 리포트가 없습니다. /api/v1/alerts/stream 호출 후 다시 시도하세요.").strip()
    # 요약은 첫 600자 미리보기 — 전체는 4페이지에 다시
    preview = summary_text[:600] + ("…" if len(summary_text) > 600 else "")
    for para in preview.split("\n"):
        if para.strip():
            story.append(Paragraph(para.replace("**", "").replace("*", "•"), base))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "* 본 리포트는 AI가 자동 생성한 요약이며 임상 의사결정에 활용 시 인간 전문가 검토가 필수입니다 (ISMS-P 2.9 / EU AI Act human-in-the-loop).",
        small))
    story.append(PageBreak())

    # ─── Page 2 — 3계층 시계열
    story.append(Paragraph("1. 3계층 신호 시계열", h2))
    story.append(Paragraph(
        "각 계층은 0–100 정규화 후 단독 경보 발령 금지 (Google Flu Trends 과대예측 교훈). YELLOW 이상 경보는 2개 이상 계층이 30 초과 시 발령.",
        small))
    story.append(Spacer(1, 3 * mm))
    story.append(Image(io.BytesIO(chart3), width=170 * mm, height=130 * mm))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"데이터 수집: OTC {len(otc)}점 · 하수 {len(sew)}점 · 검색 {len(sea)}점 (TimescaleDB 하이퍼테이블)",
        small))
    story.append(PageBreak())

    # ─── Page 3 — 분석 근거
    story.append(Paragraph("2. 선행성·인과성 분석", h2))
    story.append(Paragraph(
        f"분석 윈도우: {lead.get('window', 'N/A')} · 분석 일자: {lead.get('analysis_date', 'N/A')} · KCDC peak 주차: {lead.get('confirmed_peak_week', 'N/A')}",
        small))
    story.append(Spacer(1, 3 * mm))
    story.append(Image(io.BytesIO(chartLead), width=170 * mm, height=72 * mm))
    story.append(Spacer(1, 4 * mm))
    claim = lead.get("one_sentence_claim", "")
    if claim:
        story.append(Paragraph(f"<b>핵심 결론</b>", h3))
        story.append(Paragraph(claim, base))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("3. 17개 시·도 백테스트", h3))
    story.append(Image(io.BytesIO(chartBT), width=170 * mm, height=70 * mm))
    s = backtest.get("summary", {})
    story.append(Paragraph(
        f"전체 17개 시·도 평균 — Recall {s.get('mean_recall', 0):.3f}, "
        f"Precision {s.get('mean_precision', 0):.3f}, F1 {s.get('mean_f1', 0):.3f}, "
        f"FAR {s.get('mean_far_with_gate', 0):.3f}. "
        f"점선은 캡스톤 목표 임계값. F1≥0.70 미달 — Phase 2 (실데이터 30주 + HIRA OpenAPI 지역해상도 확보) 후 재측정 예정.",
        small))
    story.append(PageBreak())

    # ─── Page 4 — AI 리포트 본문
    story.append(Paragraph("4. AI 분석 리포트 (전문)", h2))
    story.append(Paragraph(f"모델: {rep.get('model_used') or '-'} · 생성 시각: {rep.get('created_at') or '-'}", small))
    story.append(Spacer(1, 4 * mm))

    for raw_para in summary_text.split("\n"):
        line = raw_para.strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
            continue
        if line.startswith("# "):
            story.append(Paragraph(line[2:].strip(), h2))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:].strip(), h3))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:].strip(), h3))
        else:
            # **bold** → <b>
            html = line.replace("**", "§§")
            parts = html.split("§§")
            rebuilt = ""
            for i, p in enumerate(parts):
                rebuilt += f"<b>{p}</b>" if i % 2 == 1 else p
            # bullet 정규화
            if rebuilt.startswith("- ") or rebuilt.startswith("* "):
                rebuilt = "• " + rebuilt[2:]
            story.append(Paragraph(rebuilt, base))

    rag = rep.get("rag_sources")
    if rag:
        if isinstance(rag, str):
            try:
                rag = json.loads(rag)
            except Exception:
                rag = []
        if rag:
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph("참고 가이드라인 (Qdrant RAG)", h3))
            for c in rag[:5]:
                src = c.get("source", "") if isinstance(c, dict) else str(c)
                url = c.get("url", "") if isinstance(c, dict) else ""
                line = f"• <b>{c.get('topic', '')}</b> — {src}"
                if url:
                    line += f' · <font color="{C_PRIMARY}">{url}</font>'
                story.append(Paragraph(line, small))

    doc.build(story)
    return buf.getvalue()
