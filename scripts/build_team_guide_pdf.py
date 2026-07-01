"""팀원 실행 가이드 PDF 생성 스크립트.

Usage:
    python scripts/build_team_guide_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── 폰트 ──────────────────────────────────────────────────────────────────────
_NANUM_REG = "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"
_NANUM_BOLD = "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf"

if Path(_NANUM_REG).exists():
    pdfmetrics.registerFont(TTFont("NanumKR", _NANUM_REG))
    pdfmetrics.registerFont(TTFont("NanumKR-Bold", _NANUM_BOLD))
    FONT = "NanumKR"
    FONT_B = "NanumKR-Bold"
else:
    FONT = FONT_B = "Helvetica"

# ── 색상 ──────────────────────────────────────────────────────────────────────
C_PRIMARY = "#1e3a8a"
C_ACCENT = "#dc2626"
C_WARN = "#d97706"
C_BG_LIGHT = "#f0f4ff"
C_BG_WARN = "#fff7ed"
C_BORDER = "#e5e7eb"
C_GREEN = "#166534"
C_BG_GREEN = "#f0fdf4"

# ── 스타일 ────────────────────────────────────────────────────────────────────
def _styles():
    base_style = getSampleStyleSheet()["Normal"]
    base = ParagraphStyle("base", parent=base_style, fontName=FONT, fontSize=9.5,
                          leading=15, textColor=colors.HexColor("#111827"))
    return {
        "cover_title": ParagraphStyle("cover_title", parent=base, fontName=FONT_B,
                                      fontSize=22, leading=30, textColor=colors.HexColor(C_PRIMARY),
                                      spaceAfter=6),
        "cover_sub": ParagraphStyle("cover_sub", parent=base, fontName=FONT,
                                    fontSize=13, leading=18, textColor=colors.HexColor("#374151")),
        "cover_meta": ParagraphStyle("cover_meta", parent=base, fontName=FONT,
                                     fontSize=10, leading=14, textColor=colors.HexColor("#6b7280")),
        "h1": ParagraphStyle("h1", parent=base, fontName=FONT_B, fontSize=16,
                             leading=22, textColor=colors.HexColor(C_PRIMARY),
                             spaceBefore=16, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base, fontName=FONT_B, fontSize=12,
                             leading=17, textColor=colors.HexColor("#1f2937"),
                             spaceBefore=10, spaceAfter=5),
        "h3": ParagraphStyle("h3", parent=base, fontName=FONT_B, fontSize=10.5,
                             leading=15, textColor=colors.HexColor("#374151"),
                             spaceBefore=7, spaceAfter=4),
        "body": base,
        "bullet": ParagraphStyle("bullet", parent=base, fontName=FONT,
                                 leftIndent=14, firstLineIndent=0, spaceAfter=2),
        "warn": ParagraphStyle("warn", parent=base, fontName=FONT_B, fontSize=10,
                               leading=15, textColor=colors.HexColor(C_ACCENT)),
        "code": ParagraphStyle("code", parent=base, fontName="Courier", fontSize=8.5,
                               leading=13, textColor=colors.HexColor("#1e3a8a"),
                               leftIndent=10),
        "small": ParagraphStyle("small", parent=base, fontName=FONT, fontSize=8,
                                leading=12, textColor=colors.HexColor("#6b7280")),
        "footer": ParagraphStyle("footer", parent=base, fontName=FONT, fontSize=7.5,
                                 textColor=colors.HexColor("#9ca3af")),
    }


def _table_style(header_color=C_PRIMARY):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_B),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(C_BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ])


def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#9ca3af"))
    canvas.drawString(20 * mm, 12 * mm, "Urban Immune System — 팀원 실행 가이드 (2026-05-10) | 비공개")
    canvas.drawRightString(190 * mm, 12 * mm, f"p.{doc.page}")
    canvas.restoreState()


def build(output_path: Path):
    S = _styles()
    W, _ = A4
    content_w = W - 40 * mm

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
    )

    story = []

    # ── 표지 ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("Urban Immune System", S["cover_title"]))
    story.append(Paragraph("팀원 실행 가이드", S["cover_title"]))
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(C_PRIMARY)))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("개발 점검 · 특허 출원 · 전문가 검증", S["cover_sub"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("작성일: 2026-05-10 (중간발표 D+3)", S["cover_meta"]))
    story.append(Paragraph("작성자: 박진영 (PM / ML Lead)", S["cover_meta"]))
    story.append(Paragraph("수신: 윤재영(Data Engineer/Backend) · 정욱현(Frontend)", S["cover_meta"]))
    story.append(Spacer(1, 6 * mm))

    # 경고 박스
    warn_data = [["⚠️  특허 공지 예외 기간 경고",
                  "공모전 수상(2026-03) + 중간발표(2026-05-07)로 12개월 시계가 이미 작동 중.\n"
                  "이번 주 안에 발명 공개 신고서 5명 서명 완료 필수."]]
    warn_table = Table(warn_data, colWidths=[45 * mm, content_w - 45 * mm])
    warn_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#fef2f2")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(C_BG_WARN)),
        ("FONTNAME", (0, 0), (0, 0), FONT_B),
        ("FONTNAME", (1, 0), (1, 0), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor(C_ACCENT)),
        ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#fca5a5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(warn_table)
    story.append(PageBreak())

    # ── 1부: 개발 현황 ─────────────────────────────────────────────────────────
    story.append(Paragraph("1부. 현재 개발 현황 및 담당자별 과제", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(C_BORDER)))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("전체 완성도 (2026-05-10 기준)", S["h2"]))
    status_data = [
        ["모듈", "담당", "완성도", "핵심 미완 사항"],
        ["ML", "박진영", "75%", "TFT-real 데이터 누적 후 재학습"],
        ["Backend", "윤재영", "80%", "advisory_pdf·report_pdf 테스트 0%, ML fallback 없음"],
        ["Pipeline", "윤재영", "65%", "KOWAS Selenium 자동화, kafka 테스트 0%, scorer 31%"],
        ["Frontend", "정욱현", "85%", "slides-animated 삭제 미커밋, 단위 테스트 없음"],
        ["Infra / QA", "박진영", "70%", "커버리지 39%(목표 70%), systemd 미기동"],
    ]
    status_table = Table(status_data, colWidths=[28 * mm, 22 * mm, 18 * mm, content_w - 68 * mm])
    status_table.setStyle(_table_style())
    story.append(status_table)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("즉시 처리 P0 — 오늘", S["h2"]))
    for item in [
        "git push origin develop — 로컬 1커밋이 origin 대비 ahead 방치 중",
        "frontend/public/slides-animated/ 13개 삭제 파일 + docs/STATUS.md · docs/layer_specs.md 커밋",
        "FastAPI backend(:8001), Next.js frontend(:3000) 서비스 기동 확인",
    ]:
        story.append(Paragraph(f"• {item}", S["bullet"]))
    story.append(Spacer(1, 4 * mm))

    # 팀원별 과제
    for member, role, tasks_dev, tasks_patent, tasks_verify in [
        (
            "윤재영 (Backend)",
            "Backend",
            [
                "advisory_pdf.py 테스트 작성 (커버리지 0% → 50%+)",
                "report_pdf.py 테스트 보강 (16% → 50%+)",
                "prediction_service.py ML 서비스 미실행 시 fallback 로직 추가",
                "alert_service.py 커버리지 40% → 70%",
                "auth.py 커버리지 78% → 90%+",
            ],
            ["발명 공개 신고서에 이름·소속·서명 제출 (이번 주 필수)"],
            ["Swagger/OpenAPI 스크린샷 → docs/business/advisory/ 추가", "p95 응답시간 측정 리포트 작성"],
        ),
        (
            "정욱현 (Frontend)",
            "Frontend",
            [
                "frontend/public/slides-animated/ 13개 deleted 파일 커밋 (오늘)",
                "frontend/src/lib/api.ts 분산된 fetch 호출 통합",
                "README.md Next.js 버전 표기 수정 (15 → 14.2.3)",
                "컴포넌트 스모크 테스트 최소 1개 추가",
            ],
            ["발명 공개 신고서에 이름·소속·서명 제출 (이번 주 필수)"],
            ["역학 전문가 데모용 5분 시연 스크립트 작성", "대시보드 화면 녹화 (경보 SSE 흐름 포함)"],
        ),
        (
            "박진영 (DevOps / QA)",
            "DevOps/QA",
            [
                "kafka_producer.py 테스트 신규 작성 (현재 0%)",
                "pipeline/kowas_parser.py 테스트 신규 작성 (현재 0%)",
                "pipeline/kowas_loader.py 테스트 신규 작성 (현재 0%)",
                "CI gate 36% → 45%로 상향",
                "uis-backend.service, uis-frontend.service systemd 기동",
                "K8s ingress·service YAML 작성 (Phase 4 GKE 준비)",
                "tests/integration/test_e2e_rag_report.py unskip",
            ],
            [
                "【오늘 필수】github.com/zln02/urban-immune-system PUBLIC 여부 확인",
                "최초 커밋 날짜 기록 → 12개월 특허 마감일 계산",
                "KIPRIS 선행기술 조사 실시",
                "발명 공개 신고서에 이름·소속·서명 제출",
            ],
            [
                "시스템 SLA 리포트 (30일 uptime, 응답시간, 에러율)",
                "ISMS-P 점검 완료 리포트 작성",
                "감사 로그 샘플 → advisory 패키지 추가",
            ],
        ),
    ]:
        story.append(Paragraph(member, S["h2"]))
        task_rows = [["구분", "세부 과제"]]
        for t in tasks_dev:
            task_rows.append(["개발", t])
        for t in tasks_patent:
            task_rows.append(["특허", t])
        for t in tasks_verify:
            task_rows.append(["검증", t])

        col_w = [22 * mm, content_w - 22 * mm]
        t = Table(task_rows, colWidths=col_w)
        ts = _table_style()
        ts.add("FONTNAME", (0, 1), (0, -1), FONT_B)
        t.setStyle(ts)
        story.append(t)
        story.append(Spacer(1, 5 * mm))

    story.append(PageBreak())

    # ── 2부: 특허 가이드 ────────────────────────────────────────────────────────
    story.append(Paragraph("2부. 특허 출원 가이드", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(C_BORDER)))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("우리 프로젝트 특허 가능성 판단", S["h2"]))
    story.append(Paragraph(
        "결론: 출원 가능하다. 핵심 청구 대상은 pipeline/scorer.py의 교차검증 게이트(게이트 B) 로직이다.",
        S["body"]))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("핵심 특허 청구 대상", S["h3"]))
    claim_text = (
        '"비의료 이종 신호(약국 OTC구매·하수 바이러스농도·검색트렌드) N개 이상이 동시에 기준값을 초과할 때에만 '
        '감염병 조기경보를 발령하는 방법 및 시스템"\n\n'
        '→ 게이트 B는 오경보율(FAR)을 65.8% 감소시켰으며, 기존 CDC/WHO 시스템은 이 구조를 구현하지 않는다.'
    )
    story.append(Paragraph(claim_text, S["code"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("⚠️ 공지 예외 기간 경고 (한국 특허법 제30조)", S["warn"]))
    patent_timeline = [
        ["공개 행위", "날짜", "특허 마감일"],
        ["한국능률협회 AI 공모전 수상", "2026-03 (정확한 날짜 확인 필요)", "2027-03 이전"],
        ["GitHub 저장소 공개 (PUBLIC인 경우)", "최초 커밋 날짜 확인 필요", "커밋일 + 12개월"],
        ["중간 점검 발표", "2026-05-07", "2027-05-07"],
    ]
    pt = Table(patent_timeline, colWidths=[55 * mm, 60 * mm, content_w - 115 * mm])
    pts = _table_style(C_ACCENT)
    pts.add("FONTNAME", (0, 3), (-1, 3), FONT_B)
    pts.add("TEXTCOLOR", (0, 3), (-1, 3), colors.HexColor(C_ACCENT))
    pt.setStyle(pts)
    story.append(pt)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Step 1. 발명 공개 신고서 작성 — 이번 주 필수", S["h2"]))
    story.append(Paragraph("팀원 3명 전원이 서명해야 한다. 아래 항목을 문서로 작성한다.", S["body"]))
    story.append(Spacer(1, 2 * mm))

    form_rows = [
        ["항목", "내용"],
        ["발명의 명칭(국문)", "비의료 이종 신호 교차검증 기반 감염병 조기경보 시스템 및 방법"],
        ["발명의 명칭(영문)", "Infectious Disease Early Warning System Based on\nCross-validation of Heterogeneous Non-medical Signals"],
        ["발명자", "박진영·윤재영·정욱현 (동신대학교 AI학과)"],
        ["발명 요약", "3계층 비의료 신호(OTC·하수·검색)를 XGBoost+Autoencoder로 앙상블하여\n임상 확진 평균 6.47주 선행 경보 발령.\n교차검증 게이트로 오경보율 65.8% 감소."],
        ["공지 경위", "①2026-03 AI 공모전 수상  ②GitHub 최초 공개일(확인 필요)\n③2026-05-07 중간 점검 발표"],
        ["서명란", "발명자 3명 서명·날인 / 작성일: 2026-05-10"],
    ]
    form_t = Table(form_rows, colWidths=[38 * mm, content_w - 38 * mm])
    form_t.setStyle(_table_style())
    story.append(form_t)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Step 2. 산학협력단(TLO) 발명 신고 — 2주 이내", S["h2"]))
    for line in [
        "신고 기관: 동신대학교 산학협력단 / 지식재산팀",
        "제출 서류: ①발명 공개 신고서 ②발명 설명서(advisory_pdf 활용) ③공지 증거(공모전 확인서·발표자료)",
        "기대 효과: 출원비(약 52만원) 대학 부담 가능 + 직무발명 권리 귀속 협의",
    ]:
        story.append(Paragraph(f"• {line}", S["bullet"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Step 3. KIPRIS 선행기술 조사 — 2주 이내 (박진영 담당)", S["h2"]))
    story.append(Paragraph("사이트: https://www.kipris.or.kr (한국특허정보원)", S["body"]))
    story.append(Spacer(1, 1 * mm))
    search_data = [
        ["검색 언어", "키워드"],
        ["국문 (KIPRIS)", "감염병 조기경보 비의료 신호 / 하수 감시 인플루엔자 / OTC 구매 트렌드 감염병"],
        ["영문 (Google Patents)", "wastewater surveillance influenza early warning / multi-layer ensemble alert gate"],
        ["이미 알려진 선행기술", "Lee et al. 2023(Nature) / Deng et al. 2025(Frontiers) / CDC NWSS"],
    ]
    st = Table(search_data, colWidths=[38 * mm, content_w - 38 * mm])
    st.setStyle(_table_style())
    story.append(st)
    story.append(PageBreak())

    # ── 3부: 전문가 검증 가이드 ───────────────────────────────────────────────
    story.append(Paragraph("3부. 전문가 검증 가이드", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(C_BORDER)))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("검증 준비 현황", S["h2"]))
    strength_data = [
        ["구분", "내용", "위치"],
        ["강점 ✓", "시드 고정 1줄 재현 스크립트", "ml/reproduce_validation.py"],
        ["강점 ✓", "Hugging Face 표준 Model Card", "ml/model_card.md"],
        ["강점 ✓", "17지역 walk-forward 백테스트 리포트", "docs/business/advisory/20_walk_forward_backtest.pdf"],
        ["강점 ✓", "DPIA 초안", "docs/business/advisory/22_dpia_draft.md"],
        ["강점 ✓", "KDCA 자문 공문 초안", "docs/business/advisory/10_kdca_request_letter.md"],
    ]
    sd = Table(strength_data, colWidths=[22 * mm, 85 * mm, content_w - 107 * mm])
    sd.setStyle(_table_style(C_GREEN))
    story.append(sd)
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("전문가가 반드시 물어볼 취약점 — 선제 대응 준비", S["h3"]))
    weak_data = [
        ["질문", "우리 답변"],
        ["왜 26주 단일 시즌?", "2025-2026 시즌 1회. Phase 3에서 2시즌 이상 누적 계획."],
        ["L1·L3가 전국 단일값인데\n왜 17개 지역 경보?", "Phase 3에서 HIRA OpenAPI 지역 분리 예정.\n현재는 보수적 전국 기준 broadcast."],
        ["L2 Granger p=0.267이면\n유의하지 않나?", "단독은 미유의, 3계층 composite p=0.021로 유의.\n이것이 교차검증 게이트의 근거."],
    ]
    wd = Table(weak_data, colWidths=[45 * mm, content_w - 45 * mm])
    wd.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(C_WARN)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_B),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fffbeb")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(C_BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(wd)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("검증 기관 및 신청 방법", S["h2"]))
    agency_data = [
        ["기관", "담당 부서 / 연락처", "신청 방법", "우선순위"],
        ["질병관리청(KDCA)\n역학조사과",
         "감염병감시과\n043-719-7700",
         "10_kdca_request_letter.md 출력·날인\n이메일 또는 우편 발송\n비공개 자문 요청 명시",
         "★★★"],
        ["국립감염병연구소\n(NIID, 오송)",
         "KDCA 산하\n실험·역학 전문",
         "지도교수 통한 공동연구 제안서 제출\n'비의료 신호 AI 모델 역학적 타당성 검토'",
         "★★"],
        ["전남대 의과대학\n감염내과/예방의학교실",
         "교수진 직접 이메일",
         "자문 요청\nsurveillance_bulletin.pdf + model_card.md 첨부",
         "★★★ (가장 빠름)"],
        ["WHO 서태평양\n협력센터",
         "서울대병원\nWHO 협력센터 통해",
         "최종발표 이후 권고\n현 단계 우선순위 낮음",
         "★"],
    ]
    ad = Table(agency_data, colWidths=[35 * mm, 40 * mm, 65 * mm, content_w - 140 * mm])
    ad.setStyle(_table_style())
    story.append(ad)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("전문가 검증 시 비밀유지 절차 (특허 출원 전)", S["h3"]))
    for line in [
        "공문에 '비공개 자문 요청' 문구 명시 — 발명 공개 신고서 작성 후 진행",
        "핵심 알고리즘 코드(scorer.py, model.py)는 발송 자료에서 제외",
        "성능 수치·방법론 개요만 포함. 구두 설명 가능, 소스코드 공유 금지",
        "자문 대상자로부터 비밀유지 확인 구두 또는 서면 수령",
    ]:
        story.append(Paragraph(f"• {line}", S["bullet"]))
    story.append(PageBreak())

    # ── 4부: 타임라인 ────────────────────────────────────────────────────────
    story.append(Paragraph("4부. 타임라인 요약", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(C_BORDER)))
    story.append(Spacer(1, 3 * mm))

    timeline_data = [
        ["시점", "담당", "해야 할 일"],
        ["오늘 (5/10)", "박진영", "GitHub PUBLIC/PRIVATE 확인, develop push, 삭제 파일 커밋"],
        ["오늘 (5/10)", "윤재영·정욱현", "backend·frontend systemd 서비스 기동 확인"],
        ["이번 주 (5/14까지)", "전원", "발명 공개 신고서 3명 서명 완료"],
        ["2주 이내 (5/24까지)", "박진영", "산학협력단 발명 신고, KIPRIS 선행기술 조사"],
        ["2주 이내 (5/24까지)", "박진영", "KDCA 자문 공문 발송 (비공개 명시)"],
        ["5월 내", "박진영", "네이버 API 약관 서면 확인"],
        ["5월 내", "박진영", "커버리지 CI gate 45% 달성"],
        ["최종발표 전 (6월 초)", "전원", "커버리지 60%, 전문가 검증 피드백 반영"],
        ["납품 목표", "전원", "커버리지 70%, K8s 배포 완료, ISMS-P 점검 완료"],
    ]
    tl = Table(timeline_data, colWidths=[38 * mm, 32 * mm, content_w - 70 * mm])
    tls = _table_style()
    tls.add("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fef2f2"))
    tls.add("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fef2f2"))
    tls.add("FONTNAME", (0, 1), (-1, 2), FONT_B)
    tl.setStyle(tls)
    story.append(tl)
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(C_BORDER)))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "본 문서는 박진영(PM)이 작성하였으며 팀원 전원에게 공유됩니다. "
        "특허 관련 사항은 변리사 또는 산학협력단과 최종 확인 후 진행하세요.",
        S["small"]))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    print(f"PDF 생성 완료: {output_path}")


if __name__ == "__main__":
    out = Path("docs/guides/team_action_guide_2026-05-10.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out)
