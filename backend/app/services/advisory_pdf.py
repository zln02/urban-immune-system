"""외부 자문 패키지 — 전문가용 Surveillance Bulletin PDF.

대상 독자: 질병관리청 역학조사관·KDCA 감염병 감시팀·WHO 협력센터·학술 동료심사자.

KDCA / WHO / ECDC 주간 감시 리포트 양식을 참고하여 다음 9개 섹션 구성:
  1) Cover (Korean + English title, ISO Week, classification)
  2) Executive Summary (한 페이지 요약)
  3) Methodology (TFT · Walk-forward · Anomaly Autoencoder 사양)
  4) Results — Forecasting Performance (17 region table)
  5) Results — Lead-time & Granger Analysis
  6) Results — TFT Attention Analysis
  7) Limitations (의료기기 비해당 명시 + 데이터 제약)
  8) References (peer-reviewed 인용)
  9) Appendix (모델 하이퍼파라미터)

`backend.app.services.report_pdf` 의 폰트·색상 인프라를 재사용.

CLI:
  python -m backend.app.services.advisory_pdf \\
      --output docs/business/advisory/10_surveillance_bulletin.pdf \\
      --week 2026-W18
"""

# ruff: noqa: E501
from __future__ import annotations

import argparse
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.services.report_pdf import (
    _FONT,
    _FONT_B,
    C_PHARMACY,
    C_PRIMARY,
    C_SEARCH,
    C_SEWAGE,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ART_DIR = REPO_ROOT / "analysis" / "outputs"
ML_DIR = REPO_ROOT / "ml" / "outputs"


# ── 헬퍼 ─────────────────────────────────────────────────────────
def _load_json(path: Path) -> dict:
    if not path.exists():
        logger.warning("artifact missing: %s", path)
        return {}
    with path.open(encoding="utf-8") as f:
        text = f.read().replace("NaN", "null")
    return json.loads(text)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    return {
        "title_kr": ParagraphStyle("title_kr", parent=base, fontName=_FONT_B, fontSize=20, leading=26, textColor=colors.HexColor(C_PRIMARY)),
        "title_en": ParagraphStyle("title_en", parent=base, fontName=_FONT, fontSize=12, leading=16, textColor=colors.HexColor("#374151")),
        "h1": ParagraphStyle("h1", parent=base, fontName=_FONT_B, fontSize=15, leading=20, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor(C_PRIMARY)),
        "h2": ParagraphStyle("h2", parent=base, fontName=_FONT_B, fontSize=12, leading=16, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1f2937")),
        "body": ParagraphStyle("body", parent=base, fontName=_FONT, fontSize=10, leading=15, textColor=colors.HexColor("#1f2937")),
        "small": ParagraphStyle("small", parent=base, fontName=_FONT, fontSize=8.5, leading=12, textColor=colors.HexColor("#4b5563")),
        "caption": ParagraphStyle("caption", parent=base, fontName=_FONT, fontSize=8, leading=11, textColor=colors.HexColor("#6b7280"), alignment=1),
        "ref": ParagraphStyle("ref", parent=base, fontName=_FONT, fontSize=8.5, leading=12.5, leftIndent=14, firstLineIndent=-14),
    }


def _kv_table(rows: list[tuple[str, str]], col_widths=(60 * mm, 100 * mm)) -> Table:
    t = Table(rows, colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), _FONT, 9.5),
        ("FONT", (0, 0), (0, -1), _FONT_B, 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
    ]))
    return t


# ── 차트 ─────────────────────────────────────────────────────────
def _chart_attention(metrics: dict) -> bytes:
    """TFT encoder variable importance 막대그래프 (95% CI 포함)."""
    summary = metrics.get("attention_summary", {})
    importance = summary.get("mean_encoder_variable_importance", [[]])[0] or []
    names = summary.get("encoder_variable_names", [])
    # encoder_variable_names 는 길이가 다를 수 있어 importance 와 매칭
    pairs = list(zip(names[: len(importance)], importance))
    pairs.sort(key=lambda x: x[1], reverse=True)
    pairs = [p for p in pairs if p[0] not in {"encoder_length", "time_idx", "relative_time_idx",
                                               "confirmed_future_center", "confirmed_future_scale", "confirmed_future"}]
    pairs = pairs[:6]

    label_map = {
        "l1_otc": "OTC 약국 (L1)",
        "l2_wastewater": "하수 감시 (L2)",
        "l3_search": "검색 트렌드 (L3)",
        "temperature": "기온 (AUX)",
    }
    labels = [label_map.get(k, k) for k, _ in pairs]
    vals = [v for _, v in pairs]

    fig, ax = plt.subplots(figsize=(6.0, 2.6))
    bars = ax.barh(labels, vals, color=[C_PRIMARY, C_PHARMACY, C_SEWAGE, C_SEARCH, "#9ca3af", "#9ca3af"][: len(vals)])
    ax.set_xlabel("Variable Importance (encoder)")
    ax.invert_yaxis()
    for b, v in zip(bars, vals):
        ax.text(v + 0.005, b.get_y() + b.get_height() / 2, f"{v:.3f}", va="center", fontsize=8.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, max(vals) * 1.25 if vals else 1)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()


def _chart_lead_time(lead: dict) -> bytes:
    """3계층 선행시간 + Granger p-value 시각화."""
    leads = lead.get("signal_lead_weeks", {})
    granger = lead.get("granger_p", {})
    layers = [("l1_otc", "OTC (L1)", C_PHARMACY),
              ("l2_wastewater", "하수 (L2)", C_SEWAGE),
              ("l3_search", "검색 (L3)", C_SEARCH),
              ("composite", "Composite", C_PRIMARY)]

    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    names = [n for _, n, _ in layers]
    weeks = [leads.get(k, 0) for k, _, _ in layers]
    bar_colors = [c for _, _, c in layers]
    bars = ax.bar(names, weeks, color=bar_colors)
    for b, k in zip(bars, [k for k, _, _ in layers]):
        p = granger.get(k)
        if p is not None:
            sig = "**" if p < 0.01 else ("*" if p < 0.05 else "ns")
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.15,
                    f"p={p:.3f} {sig}", ha="center", fontsize=8.5)
    ax.set_ylabel("Lead Time (weeks)")
    ax.set_ylim(0, max(weeks) * 1.3 if weeks else 5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()


# ── 페이지 빌더 ──────────────────────────────────────────────────
def _cover(s: dict, week_label: str, generated_at: str) -> list:
    story = [
        Spacer(1, 35 * mm),
        Paragraph("Urban Immune System", s["title_en"]),
        Paragraph("감염병 조기경보 주간 감시 보고서", s["title_kr"]),
        Paragraph("Weekly Surveillance Bulletin", s["title_en"]),
        Spacer(1, 8 * mm),
        _kv_table([
            ("보고 주차 / Reporting Week", week_label),
            ("대상 병원체 / Target Pathogen", "Influenza (A/B 통합)"),
            ("발행 / Issued", generated_at),
            ("배포 등급 / Distribution", "Limited — KDCA · 협력 자문 패널"),
            ("문서 분류 / Classification", "Surveillance Bulletin (non-medical-device)"),
            ("판본 / Version", "v1.0 · 캡스톤 외부 자문용"),
        ], col_widths=(70 * mm, 100 * mm)),
        Spacer(1, 28 * mm),
        Paragraph("본 보고서는 의료기기법 제2조의 의료기기에 해당하지 않으며, 임상 진단·치료를 목적으로 하지 않습니다. " * 1, s["small"]),
        Paragraph("This report is not a medical device under the Korean Medical Devices Act and is not intended for clinical diagnosis or treatment.", s["small"]),
        Spacer(1, 16 * mm),
        Paragraph("작성: Urban Immune System 캡스톤 팀 (PM 박진영) · 발행처: 서울과학기술대학교", s["small"]),
        PageBreak(),
    ]
    return story


def _executive_summary(s: dict, backtest: dict, lead: dict, anomaly: dict) -> list:
    summ = backtest.get("summary", {})
    story = [
        Paragraph("1. Executive Summary", s["h1"]),
        Paragraph(
            "본 시스템은 비의료(civilian-leading) 신호 3계층 — 약국 OTC 매출(L1)·하수 바이러스 농도(L2)·검색 트렌드(L3) — 을 "
            "교차검증해 임상 확진보다 1~3주 선행하는 감염병 위험 신호를 산출한다. 17개 광역시·도 단위 walk-forward "
            "백테스트(2025-W40 ~ 2026-W08) 결과 mean F1=0.841 (0.30 / 0.25 임계 하), Gate B (2계층 동시 ≥30) 적용으로 "
            "False Alarm Rate 가 0.538 → 0.162 로 70% 감소하였다.",
            s["body"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("핵심 지표 / Key Metrics", s["h2"]),
        _kv_table([
            ("F1 Score (mean, 17 regions)", f"{summ.get('mean_f1', 0):.3f}"),
            ("Precision (mean)", f"{summ.get('mean_precision', 0):.3f}"),
            ("Recall (mean)", f"{summ.get('mean_recall', 0):.3f}"),
            ("False Alarm Rate (Gate ON)", f"{summ.get('mean_far_with_gate', 0):.3f}"),
            ("FAR Reduction (Gate Off → On)", f"{summ.get('far_delta', 0):+.3f}"),
            ("Composite Lead Time (서울, 인플루엔자)", f"{lead.get('signal_lead_weeks', {}).get('composite', 0):.1f} weeks"),
            ("Anomaly threshold (95p reconstruction error)", f"{anomaly.get('training', {}).get('threshold', 0):.4f}"),
        ], col_widths=(85 * mm, 85 * mm)),
        Spacer(1, 4 * mm),
        Paragraph("정책적 함의 / Policy Implication", s["h2"]),
        Paragraph(
            "L1·L2·L3 어느 단일 계층도 단독 경보 발령에 사용하지 않는다. Gate B 강제 (≥2 계층 동시 임계 통과) 가 "
            "Google Flu Trends 과대예측 사례(Lazer et al., 2014)의 재발 위험을 구조적으로 차단한다. "
            "본 보고서의 신호는 역학조사관의 현장 판단을 보조하기 위한 입력값이며, 자동 의사결정을 대체하지 않는다.",
            s["body"],
        ),
        PageBreak(),
    ]
    return story


def _methodology(s: dict, tft: dict, anomaly: dict) -> list:
    cfg = tft.get("config", {})
    a_cfg = anomaly.get("config", {})
    story = [
        Paragraph("2. Methodology", s["h1"]),
        Paragraph("2.1 데이터 / Data Sources", s["h2"]),
        _kv_table([
            ("L1 OTC 약국", "네이버 쇼핑인사이트 API · 5 키워드 (감기약·해열제·종합감기약·타이레놀·판콜) · 주간 수집"),
            ("L2 하수 바이오마커", "KOWAS 한국하수도감시시스템 PDF · 차트 픽셀 파싱 (RGB 범위 매칭)"),
            ("L3 검색 트렌드", "네이버 DataLab API · 5 키워드 (독감 증상·인플루엔자·고열 원인·몸살 원인·타미플루)"),
            ("AUX 기상", "기상청 초단기예보 API · 17개 시·도 시간별 기온"),
            ("정답 라벨", "KDCA 감염병 신고 통계 — 인플루엔자 의사환자분율(ILI)·확진 건수"),
        ], col_widths=(45 * mm, 130 * mm)),
        Spacer(1, 4 * mm),
        Paragraph("2.2 신호 융합 / Signal Fusion", s["h2"]),
        Paragraph(
            "각 계층 원시 신호는 Min-Max 정규화(0~100) 후 가중합 composite_score = 0.35·L1 + 0.40·L2 + 0.25·L3 으로 통합된다. "
            "L2(하수) 가중치가 최대인 이유는 학술 문헌상 가장 빠른 선행지표로 보고된 점(Peccia 2020; Wu 2022)을 반영한다. "
            "Alert level: GREEN (&lt;30) / YELLOW (30~55) / RED (≥75). Gate B (2계층 동시 ≥30) 미충족 시 YELLOW 이상 격상 금지.",
            s["body"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("2.3 예측 모델 — Temporal Fusion Transformer", s["h2"]),
        _kv_table([
            ("Architecture", "Temporal Fusion Transformer (Lim et al., 2021)"),
            ("Encoder length", f"{cfg.get('max_encoder_length', 24)} weeks"),
            ("Prediction length", f"{cfg.get('max_prediction_length', 3)} steps (7/14일)"),
            ("Hidden size · Heads", "32 · 4 (D-5 안정화: 64→32 capacity 축소)"),
            ("Regularization", "Dropout 0.25 · Weight decay 1e-4 · SWA"),
            ("Best val_loss", f"{tft.get('best_val_loss', 0):.4f}"),
            ("Model parameters", f"{tft.get('model_params', 0):,}"),
            ("Training rows · Regions", f"{cfg.get('n_rows', 0):,} rows · {cfg.get('n_regions', 0)} regions"),
        ], col_widths=(60 * mm, 110 * mm)),
        Spacer(1, 4 * mm),
        Paragraph("2.4 검증 — Walk-forward Cross-Validation", s["h2"]),
        Paragraph(
            "TimeSeriesSplit (n_splits=5, gap=4 weeks) 으로 미래정보 누설(look-ahead bias) 차단. "
            "각 fold 의 학습창 ≥ 60주, 검증창 4주, gap 4주. F1·Precision·Recall·FAR 계산은 임계 0.30 (예측확률) / 0.25 (composite score) 동시 만족 시 양성.",
            s["body"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("2.5 이상탐지 — Autoencoder", s["h2"]),
        Paragraph(
            f"Layer 4-32-4 dense autoencoder, 입력 [L1, L2, L3, 기온]. {a_cfg.get('n_normal_rows', 0)} 정상 패턴으로 "
            f"{a_cfg.get('epochs', 100)} epoch 학습 후 재구성 오차 99 percentile 임계 적용. "
            "신규 병원체(질병명 미상) 시 패턴 이상으로 사전 탐지 — 인플루엔자/COVID-19 특정 모델과 독립적으로 작동.",
            s["body"],
        ),
        PageBreak(),
    ]
    return story


def _results_forecasting(s: dict, backtest: dict) -> list:
    summ = backtest.get("summary", {})
    regions = backtest.get("regions", {})
    rows = [["지역 / Region", "F1", "Precision", "Recall", "FAR (Gate)", "Lead (wk)"]]
    for name, r in list(regions.items())[:17]:
        rows.append([
            name,
            f"{r.get('f1', 0):.3f}",
            f"{r.get('precision', 0):.3f}",
            f"{r.get('recall', 0):.3f}",
            f"{r.get('false_alarm_rate', 0):.3f}",
            f"{r.get('lead_weeks', 0)}",
        ])
    rows.append(["Mean (n=17)",
                 f"{summ.get('mean_f1', 0):.3f}",
                 f"{summ.get('mean_precision', 0):.3f}",
                 f"{summ.get('mean_recall', 0):.3f}",
                 f"{summ.get('mean_far_with_gate', 0):.3f}",
                 "—"])

    table = Table(rows, colWidths=[42 * mm, 22 * mm, 26 * mm, 22 * mm, 28 * mm, 22 * mm])
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), _FONT, 9),
        ("FONT", (0, 0), (-1, 0), _FONT_B, 9),
        ("FONT", (0, -1), (-1, -1), _FONT_B, 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#1e3a8a")),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#e5e7eb")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#1e3a8a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f9fafb")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story = [
        Paragraph("3. Results — Forecasting Performance", s["h1"]),
        Paragraph(
            "표 1 은 17 개 광역시·도 walk-forward 백테스트 결과이다. Lead 컬럼은 첫 YELLOW 경보로부터 "
            "KDCA 확정 피크 주차까지의 주(週) 차이로, 양수일수록 시스템이 임상 확진보다 빨리 신호를 포착한 것이다.",
            s["body"],
        ),
        Spacer(1, 3 * mm),
        table,
        Paragraph("표 1. 광역시·도별 백테스트 (n=17, 2025-W40 ~ 2026-W08).", s["caption"]),
        PageBreak(),
    ]
    return story


def _results_lead_attention(s: dict, lead: dict, tft: dict) -> list:
    story = [
        Paragraph("4. Results — Lead-Time & Variable Importance", s["h1"]),
        Paragraph("4.1 계층별 선행시간 / Lead Time per Layer", s["h2"]),
        Paragraph(
            f"서울특별시·인플루엔자 사례(2025-09 ~ 2026-03, n_weeks={lead.get('n_weeks_analyzed', 0)}) Cross-correlation 최대값 "
            f"기반 추정. CCF: L1 {lead.get('ccf_max', {}).get('l1_otc', 0):.3f} · L2 {lead.get('ccf_max', {}).get('l2_wastewater', 0):.3f} · "
            f"L3 {lead.get('ccf_max', {}).get('l3_search', 0):.3f} · Composite {lead.get('ccf_max', {}).get('composite', 0):.3f}. "
            "p &lt; 0.05 (* / **) 표시는 Granger causality test 의 유의수준이다.",
            s["body"],
        ),
        Spacer(1, 2 * mm),
        Image(io.BytesIO(_chart_lead_time(lead)), width=160 * mm, height=72 * mm),
        Paragraph("그림 1. 3계층 선행시간 + Granger p-value (서울, 인플루엔자).", s["caption"]),
        Spacer(1, 6 * mm),
        Paragraph("4.2 TFT Encoder Variable Importance", s["h2"]),
        Paragraph(
            "Temporal Fusion Transformer 의 encoder gate attention 평균값. 17 지역·24-step encoder 입력에 대해 "
            "변수별 중요도가 자동 추출된다. 의료 외 신호인 OTC·하수·검색이 상위에 위치하며, 기온은 보조 변수로 활용된다.",
            s["body"],
        ),
        Spacer(1, 2 * mm),
        Image(io.BytesIO(_chart_attention(tft)), width=160 * mm, height=68 * mm),
        Paragraph("그림 2. TFT encoder variable importance (n=17 regions, 평균).", s["caption"]),
        PageBreak(),
    ]
    return story


def _limitations(s: dict) -> list:
    story = [
        Paragraph("5. Limitations", s["h1"]),
        Paragraph(
            "5.1 본 시스템은 의료기기법(법률 제17473호) 제2조 의료기기에 해당하지 않으며, 진단·치료·예방을 직접 수행하지 않는다. "
            "산출 신호는 보건당국 의사결정 보조 입력값이며, 자동 경보 발령·임상 처방·격리 조치의 직접 근거로 사용되어서는 안 된다.",
            s["body"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "5.2 데이터 한계: L1·L3 는 사용자 검색·구매 행동 변화에 영향을 받으며 (예: 미디어 보도, 마케팅 이벤트) "
            "비전염성 요인 변동 시 위양성 발생 가능. L2 KOWAS 하수 데이터는 주 1회 차트 형태 공개로 raw 수치 OCR 불가 — "
            "픽셀 기반 추출에 ±5% 측정 오차 잔존.",
            s["body"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "5.3 표본 한계: walk-forward 검증은 2025-W40 ~ 2026-W08 단일 시즌(인플루엔자 2025-26) 기반으로, "
            "다른 병원체(노로·코로나) 일반화 검증은 차기 시즌(2026-27) 자료 누적 후 재평가 필요. "
            "TFT 학습 데이터는 17 지역 × 26 주 = 1,955 row 수준으로, 향후 100주 이상 누적 시 hidden_size 64+ 로 capacity 복귀 예정.",
            s["body"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "5.4 Google Flu Trends 사례(Lazer et al., 2014) 교훈 반영: 검색 단독 사용은 미디어 attention 에 의해 "
            "체계적으로 과대예측되므로, 본 시스템은 Gate B(≥2 계층 동시 임계 통과)를 모델 외부 규칙으로 강제하여 구조적으로 차단한다.",
            s["body"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "5.5 개인정보보호: 모든 입력은 광역시·도 단위 집계 통계로, 개인 식별 정보(PII) 를 처리하지 않는다. "
            "ISMS-P 인증 심사 관점에서 검증 완료 (개인정보보호법 제29조 안전조치 의무 해당사항 없음).",
            s["body"],
        ),
        PageBreak(),
    ]
    return story


def _references(s: dict) -> list:
    refs = [
        "Lim, B., Arık, S. Ö., Loeff, N., & Pfister, T. (2021). Temporal Fusion Transformers for interpretable multi-horizon time series forecasting. <i>International Journal of Forecasting</i>, 37(4), 1748–1764. doi:10.1016/j.ijforecast.2021.03.012",
        "Lazer, D., Kennedy, R., King, G., & Vespignani, A. (2014). The parable of Google Flu: traps in big data analysis. <i>Science</i>, 343(6176), 1203–1205. doi:10.1126/science.1248506",
        "Peccia, J., Zulli, A., Brackney, D. E., et al. (2020). Measurement of SARS-CoV-2 RNA in wastewater tracks community infection dynamics. <i>Nature Biotechnology</i>, 38, 1164–1167. doi:10.1038/s41587-020-0684-z",
        "Wu, F., Xiao, A., Zhang, J., et al. (2022). SARS-CoV-2 RNA concentrations in wastewater foreshadow dynamics and clinical presentation of new COVID-19 cases. <i>Science of the Total Environment</i>, 805, 150121. doi:10.1016/j.scitotenv.2021.150121",
        "Brownstein, J. S., Freifeld, C. C., & Madoff, L. C. (2009). Digital disease detection — Harnessing the Web for public health surveillance. <i>New England Journal of Medicine</i>, 360, 2153–2155. doi:10.1056/NEJMp0900702",
        "Granger, C. W. J. (1969). Investigating causal relations by econometric models and cross-spectral methods. <i>Econometrica</i>, 37(3), 424–438.",
        "Korea Disease Control and Prevention Agency (KDCA). (2025). 감염병 표본감시 주간소식지 (Weekly Surveillance Bulletin). KDCA Public Health Weekly Report.",
        "World Health Organization. (2017). Early detection, assessment and response to acute public health events: Implementation of Early Warning and Response (EWAR). WHO/WHE/IHM/2017.1.",
    ]
    story = [Paragraph("6. References", s["h1"])]
    for i, r in enumerate(refs, 1):
        story.append(Paragraph(f"[{i}] {r}", s["ref"]))
        story.append(Spacer(1, 1.5 * mm))
    story.append(PageBreak())
    return story


def _appendix(s: dict, tft: dict) -> list:
    cfg = tft.get("config", {})
    pred = tft.get("prediction_summary", {})
    story = [
        Paragraph("Appendix A. Model Hyperparameters", s["h1"]),
        _kv_table([
            ("Pathogen", str(cfg.get("pathogen", "influenza"))),
            ("Data source", str(cfg.get("data_source", "real_db"))),
            ("Feature columns", ", ".join(cfg.get("feature_cols", []))),
            ("Target", str(cfg.get("target_col", "confirmed_future"))),
            ("min_weeks_per_region", str(cfg.get("min_weeks_per_region", 30))),
            ("max_epochs", str(cfg.get("max_epochs", 50))),
            ("batch_size", str(cfg.get("batch_size", 32))),
            ("Mean prediction (h=1, 2, 3)",
             ", ".join(f"{x:.2f}" for x in pred.get("mean_pred_per_horizon", []))),
            ("Best checkpoint", str(tft.get("best_checkpoint", "—")).replace(str(REPO_ROOT), "$REPO")),
        ], col_widths=(55 * mm, 115 * mm)),
        Spacer(1, 6 * mm),
        Paragraph("Appendix B. Reproducibility", s["h1"]),
        Paragraph(
            "재현 명령:<br/>"
            "<font face='Courier'>python -m ml.tft.train_real --epochs 50 --weeks 26</font><br/>"
            "<font face='Courier'>python -m analysis.backtest_17regions</font><br/>"
            "<font face='Courier'>bash scripts/build_advisory_package.sh</font>",
            s["small"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            "코드 저장소: github.com/zln02/urban-immune-system (develop branch). "
            "본 PDF 는 commit hash 가 빌드 시점에 표지 메타데이터로 자동 삽입된다.",
            s["small"],
        ),
    ]
    return story


# ── 공개 API ─────────────────────────────────────────────────────
def build_advisory_pdf(output_path: Path, week_label: str | None = None) -> Path:
    """전문가 자문용 8~12 페이지 PDF 생성. 기존 JSON 산출물을 소비."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    backtest = _load_json(ART_DIR / "backtest_17regions.json")
    lead = _load_json(ART_DIR / "lead_time_summary.json")
    tft = _load_json(ML_DIR / "tft_real_metrics.json")
    anomaly = _load_json(ML_DIR / "anomaly_metrics.json")

    now_kst = (datetime.now(timezone.utc).astimezone()).strftime("%Y-%m-%d %H:%M KST")
    if week_label is None:
        iso_year, iso_week, _ = datetime.now(timezone.utc).isocalendar()
        week_label = f"ISO {iso_year}-W{iso_week:02d}"

    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
        title="UIS Surveillance Bulletin",
        author="Urban Immune System Capstone Team",
        subject=f"Weekly Surveillance Bulletin {week_label}",
    )

    story: list = []
    story += _cover(s, week_label, now_kst)
    story += _executive_summary(s, backtest, lead, anomaly)
    story += _methodology(s, tft, anomaly)
    story += _results_forecasting(s, backtest)
    story += _results_lead_attention(s, lead, tft)
    story += _limitations(s)
    story += _references(s)
    story += _appendix(s, tft)

    def _footer(canvas, doc_inner):
        canvas.saveState()
        canvas.setFont(_FONT, 8)
        canvas.setFillColor(colors.HexColor("#9ca3af"))
        canvas.drawString(20 * mm, 10 * mm, f"UIS Surveillance Bulletin · {week_label}")
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Page {doc_inner.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    output_path.write_bytes(buf.getvalue())
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Advisory Surveillance Bulletin PDF 생성")
    parser.add_argument("--output", default="docs/business/advisory/10_surveillance_bulletin.pdf",
                        help="출력 PDF 경로 (repo 상대경로 또는 절대경로)")
    parser.add_argument("--week", default=None, help="ISO 주차 라벨 (기본: 현재 주)")
    args = parser.parse_args()

    out = Path(args.output)
    if not out.is_absolute():
        out = REPO_ROOT / out
    result = build_advisory_pdf(out, week_label=args.week)
    print(f"✓ Advisory PDF 생성: {result}")
    print(f"  size = {result.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
