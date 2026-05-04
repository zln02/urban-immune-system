"""중간발표 24장 슬라이드 검증 리포트 PDF 생성기.

slides outline.md + 코드/산출물(json) 대조 결과를 PDF로 출력한다.
한글 폰트는 fonts/NanumGothic*.ttf 사용.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).parent.parent
FONT_DIR = ROOT / "fonts"
OUT = ROOT / "docs" / "slides" / "2026-04-30_중간발표_검증리포트.pdf"

pdfmetrics.registerFont(TTFont("Nanum", str(FONT_DIR / "NanumGothic.ttf")))
pdfmetrics.registerFont(TTFont("NanumBold", str(FONT_DIR / "NanumGothicBold.ttf")))

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="NanumBold",
                   fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"),
                   spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="NanumBold",
                   fontSize=13, leading=17, textColor=colors.HexColor("#1e3a8a"),
                   spaceBefore=10, spaceAfter=4)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="NanumBold",
                   fontSize=11, leading=14, textColor=colors.HexColor("#334155"),
                   spaceBefore=6, spaceAfter=2)
P = ParagraphStyle("P", parent=ss["BodyText"], fontName="Nanum",
                  fontSize=9.5, leading=13, alignment=TA_LEFT, spaceAfter=3)
PSmall = ParagraphStyle("PS", parent=P, fontSize=8.5, leading=11,
                       textColor=colors.HexColor("#475569"))
PASS = ParagraphStyle("PASS", parent=P, textColor=colors.HexColor("#15803d"),
                     fontName="NanumBold", fontSize=9)
WARN = ParagraphStyle("WARN", parent=P, textColor=colors.HexColor("#b45309"),
                     fontName="NanumBold", fontSize=9)
FAIL = ParagraphStyle("FAIL", parent=P, textColor=colors.HexColor("#b91c1c"),
                     fontName="NanumBold", fontSize=9)

doc = SimpleDocTemplate(
    str(OUT), pagesize=A4,
    leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm,
    title="중간발표 24장 검증 리포트",
)

flow = []

# ---------------------------------------------------------- 표지
flow += [
    Paragraph("Urban Immune System", H1),
    Paragraph("중간발표 24장 슬라이드 — 검증·정합성 리포트", H2),
    Paragraph("대조 자료: <b>2026-04-30_중간발표_outline.md</b> ↔ "
             "코드(scorer.py / kowas_parser.py / xgboost.model) "
             "+ 산출물(backtest_17regions.json / lead_time_summary.json / validation.json)", P),
    Paragraph("작성일: 2026-04-29 · 발표일: 2026-04-30 (D-1)", PSmall),
    Spacer(1, 6),
]

# ---------------------------------------------------------- 요약
flow += [
    Paragraph("요약 — 한 줄 결론", H2),
    Paragraph("✅ <b>전체 24장 코드·산출물 정합 + WARN/NOTE 2건 모두 v2 PPTX에서 라벨 오버레이로 해소.</b> "
             "발표 가능 상태.", P),
    Paragraph("산출물:", H3),
    Paragraph("· <b>2026-04-30_중간발표_v2.pptx</b> — Slide 3·16에 회색 캡션 텍스트박스 오버레이 추가본 (원본 보존)", P),
    Paragraph("· <b>2026-04-30_중간발표_v2.pdf</b> — LibreOffice headless export PDF", P),
    Paragraph("· <b>2026-04-30_중간발표_outline.md</b> — 동일 라벨 텍스트 단일 출처 동기화 완료", P),
]

summary_data = [
    ["구분", "건수", "내용"],
    ["PASS", "22 / 24", "코드·산출물 수치와 일치"],
    ["WARN→FIXED", "1", "Slide 3 합성가정 라벨 추가 (v2 PPTX 오버레이 적용)"],
    ["NOTE→FIXED", "1", "Slide 16 KCDC 2025-W49 출처 라벨 추가 (v2 PPTX 오버레이 적용)"],
    ["INFO", "1", "원본 PPTX는 슬라이드 전체가 단일 이미지(Gamma/Tome export)라 텍스트 직접 편집 불가"],
]
t = Table(summary_data, colWidths=[22*mm, 22*mm, 120*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, -1), "Nanum"),
    ("FONTNAME", (0, 0), (-1, 0), "NanumBold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
]))
flow += [t, Spacer(1, 8)]

# ---------------------------------------------------------- 핵심 수치 매트릭스
flow += [
    Paragraph("핵심 수치 — 슬라이드 ↔ 산출물 매칭", H2),
]
fact_rows = [
    ["슬라이드", "주장", "출처 산출물", "검증"],
    ["S8 / S12 / S15", "F1 = 0.841", "backtest_17regions.json → summary.mean_f1 = 0.841", "✅"],
    ["S12 / S15", "Precision = 0.960", "summary.mean_precision = 0.96", "✅"],
    ["S12 / S15", "Recall = 0.768", "summary.mean_recall = 0.768", "✅"],
    ["S12 / S15 / S21", "FAR = 0.162 (gate ON)", "summary.mean_far_with_gate = 0.162", "✅"],
    ["S15 / S21", "FAR 0.538 (gate OFF) → 0.162", "mean_far_no_gate=0.538, far_delta=-0.376", "✅"],
    ["S12 / S15", "Lead time 5.9주", "lead_time_summary 17지역 평균(README 명시)", "✅"],
    ["S12", "Granger composite p = 0.021", "lead_time_summary.granger_p.composite = 0.0209", "✅"],
    ["S12", "Granger L3 검색 p = 0.007", "lead_time_summary.granger_p.l3_search = 0.0073", "✅"],
    ["S8 / S14", "synthetic_hardened F1 = 0.667", "validation.json → cv_mean_f1 = 0.6667", "✅"],
    ["S8 / S14", "walk-forward n_splits=5, gap=4", "TimeSeriesSplit(n_splits=5, gap=4) — xgboost.model:210", "✅"],
    ["S13", "가중치 w1=0.35/w2=0.40/w3=0.25", "scorer._load_weights() / config.py", "✅"],
    ["S13", "TFT hidden=64, heads=4, encoder=24", "ml/configs/model_config.yaml + tft.model", "✅"],
    ["S7 / S9", "L2 KOWAS 차트 픽셀 분석", "kowas_parser.py PATHOGEN_COLOR_RANGES + parse_chart()", "✅"],
    ["S7 / S15", "Gate B (2계층 30+ 강제)", "scorer.determine_alert_level() L141-159", "✅"],
    ["S15", "Gate A 폐기(DISCARD)", "scorer.py L40-44 주석 + l2_gate_sweep.json", "✅"],
    ["S10 / S23", "다중 병원체 — flu/covid/noro 컬럼 분리", "init.sql layer_signals.pathogen DEFAULT 'influenza'", "✅"],
    ["S17", "재현 4-line 명령", "kowas_loader / naver_backfill / scorer / backtest 4개 CLI 존재", "✅"],
    ["S18", "RAG → Claude SSE", "rag/report_generator.py + alerts SSE 라우터", "✅"],
    ["S21", "멱등성 DELETE→INSERT", "db_writer.delete_signal_range() + naver_backfill.backfill_layer()", "✅"],
    ["S3", "약국 -2주 / 하수 -3주 / 검색 -1주", "이는 <b>합성데이터 모델링 가정</b>(xgboost.generate_synthetic_data lead_l1=2, lead_l2=3, lead_l3=1)", "⚠"],
    ["S12 / README", "L1=8주 / L2=2주 / L3=3주 (실측)", "lead_time_summary.signal_lead_weeks", "⚠ S3와 출처 분리 필요"],
    ["S16", "12/07 피크 231K, per_100k 447", "confirmed_cases 테이블 — 슬라이드에 'KCDC 2025-W49' 출처 라벨 권고", "ℹ"],
]
ft = Table(fact_rows, colWidths=[28*mm, 52*mm, 70*mm, 14*mm])
ft.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, -1), "Nanum"),
    ("FONTNAME", (0, 0), (-1, 0), "NanumBold"),
    ("FONTSIZE", (0, 0), (-1, -1), 7.8),
    ("LEADING", (0, 0), (-1, -1), 10),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
]))
flow += [ft, PageBreak()]

# ---------------------------------------------------------- 슬라이드별 검증
flow += [Paragraph("슬라이드별 검증 (24장)", H1)]

slides_review = [
    (1, "표지", "PASS",
     "팀 5인·수상 콜아웃·발표일 정상. 한국능률협회 명시 OK.",
     "디자인만 확인 — 코드 검증 대상 아님."),
    (2, "문제 정의", "PASS",
     "코로나 첫 보고까지 3주 — 일반화된 사실. 누적 14일 시각화는 발표용 시뮬.",
     "교수 질문 대비: '14일 출처?' → 보고체계 ①~④ 단계는 KCDC 감염병 신고체계 표준 절차."),
    (3, "해법 3-Layer", "WARN",
     "선행시간 -2/-3/-1주는 <b>합성데이터 모델링 가정값</b>. 실측 lead_time_summary는 8/2/3주.",
     "권고: '모델 가정' 또는 '교과서 추정' 라벨 추가. 또는 실측값(8/2/3)으로 통일. "
     "Slide 12에서 '5.9주'가 등장하는 순간 청중 머릿속에 모순 발생 가능."),
    (4, "교차검증·선행연구", "PASS",
     "GFT 2배 과대예측·선행연구 3건(Deng/Lee/Lim) 모두 README와 일치.",
     "교수 질문 대비: 'Deng et al. 2-Layer와 차별점?' → 우리는 3-Layer + Gate B 강제."),
    (5, "용어집", "PASS",
     "6개 용어 정의 정확. Granger p=0.007은 lead_time_summary.granger_p.l3_search=0.0073 일치.",
     "—"),
    (6, "시스템 구조", "PASS",
     "Frontend/Backend/Pipeline/ML/LLM/Infra 스택 모두 실파일 존재.",
     "주의: Kafka는 '운영 단계 예정'으로 명시 — 현재는 cron+DB 직접 INSERT (db_writer.py)."),
    (7, "5대 결정사항", "PASS",
     "L2 픽셀파싱·교차검증 게이트·RAG 인용·pathogen 컬럼 — 모두 코드로 구현 확인.",
     "—"),
    (8, "데이터셋·라벨 분리", "PASS",
     "synthetic_hardened F1=0.667 ↔ 17지역 real F1=0.841 분리 표기 정직.",
     "교수 질문: '왜 합성·실데이터 갭?' → ml/CLAUDE.md QA 스니펫 그대로 답변."),
    (9, "KOWAS 픽셀 파서", "PASS",
     "RGB 범위 코로나 파랑/인플루엔자 주황/노로 노랑 — kowas_parser.PATHOGEN_COLOR_RANGES 일치. 952건 자동 추출.",
     "교수 질문: 'OCR 왜 안 씀?' → KDCA가 raw 수치 텍스트 노출 안 함, 차트만 존재."),
    (10, "L1·L3 + 다중병원체", "PASS",
     "카테고리 ID 50000167·SYMPTOM_KEYWORDS 5개 — naver_backfill.py와 일치. influenza 1074행/covid 34행/noro 34행.",
     "RSV·결핵·HIV 한계 정직 명시 OK."),
    (11, "데모 — 대시보드", "PASS",
     "Next.js 15·Deck.gl·17 KoreaMap. 부산 78.3 / 대전 60.8 / 서울 48.3 시연 시점 명시.",
     "권고: 데모 백업 영상 준비 (네트워크 사고 대비)."),
    (12, "실측 성능", "PASS",
     "F1 0.841 / Prec 0.960 / Rec 0.768 / FAR 0.162 — backtest_17regions.json summary와 100% 일치. "
     "Granger p=0.021/0.007 — lead_time_summary와 일치.",
     "Slide 3과 lead time 출처 분리(WARN 1) 외 완벽."),
    (13, "모델·하이퍼·XAI", "PASS",
     "가중치 0.35/0.40/0.25·TFT hidden=64/heads=4/encoder=24 — config 일치. "
     "XAI top1 confirmed_future_center에 'positional encoding, 외부 누설 아님' 면책 표기 정직.",
     "교수 질문: 'top1이 confirmed_future_center인데 leakage?' → 슬라이드 면책문 그대로 답변."),
    (14, "Walk-forward 검증", "PASS",
     "TimeSeriesSplit(5, gap=4)·서울 단독 fold 4 결과 TP=8/FP=8/TN=5/FN=0 — validation.json fold_scores과 정합.",
     "교수 질문: '왜 fold 1~3 NaN?' → 양성 클래스 부재(겨울 시즌 미포함). 슬라이드에 명시 권고."),
    (15, "17지역 일반화", "PASS",
     "박스플롯 5수치 + 엄격라벨 0.621 → 정직라벨 0.841 비교 — 백테스트 산출물과 일치. "
     "Gate A DISCARD 정직 표기.",
     "★ 발표 핵심 강점 슬라이드. 교수 도전 가장 적게 받을 부분."),
    (16, "경보·확진자 정합성", "NOTE",
     "Recall 17/17·Precision 17/20·F1 0.92 — risk_scores 시뮬 결과. 오경보 3건 시즌 경계 명시 OK.",
     "권고: '12/07 피크 231K (per_100k 447)' 옆에 '출처: KCDC 2025-W49 confirmed_cases' 라벨 추가."),
    (17, "재현 4-line", "PASS",
     "4개 명령 모두 실파일 존재. 952건/969행/884행 risk_scores 수치는 산출물 일치.",
     "★ 발표장에서 실행 시연 권고 (60초 내 끝나는 명령은 backtest 1건만)."),
    (18, "RAG + SSE", "PASS",
     "Qdrant epidemiology_docs·multilingual MiniLM 384-dim·Claude SSE — 코드 일치.",
     "첫 바이트 < 500ms 주장 — load_test_results.json 추가 인용 권고."),
    (19, "로드맵 Phase 1~5", "PASS",
     "가격 모델 2000~6000만원/1~3억원 — docs/business/pricing-model.md 정렬 가정.",
     "교수 질문: '지자체 가격 근거?' → 비슷한 GIS·역학 SaaS 시장가. 변호 가능."),
    (20, "벤치마크 시장 갭", "PASS",
     "GFT/CDC NWSS/BlueDot/HealthMap 포지셔닝 정확.",
     "★ 우리만 우상단 — 발표 시 '저희가 아는 한' 면책 한마디 추가 권고."),
    (21, "엔지니어링 인사이트 5", "PASS",
     "5건 모두 실코드 라인 확인 가능 (scorer.py:104-161 등 라인 정확).",
     "—"),
    (22, "특허·전문가 자문", "PASS",
     "자체 신규성 평가만·변리사 미완 면책 정직.",
     "교수 질문: '특허 신규성 어떻게 검증?' → 5월 변리사 자문 1순위 — 그대로 답."),
    (23, "시·군·구 226개 확장", "PASS",
     "광역 17 → 226 확장 모식도. HIRA 1~2주/KOWAS 4~6주 협상 일정 명시 OK.",
     "교수 질문: '226개 데이터 비용?' → HIRA 무료, KOWAS 협상 단계."),
    (24, "팀·Q&A", "PASS",
     "팀 5인 역할 README 일치. 리스크 3·운영 발견·해결 정직 표기.",
     "Q&A 5분 — Q&A 카드(다음 페이지) 준비."),
]

for n, title, status, body, advice in slides_review:
    if status == "PASS":
        badge = "✅ PASS"
        color = colors.HexColor("#15803d")
    elif status == "WARN":
        badge = "⚠ WARN"
        color = colors.HexColor("#b45309")
    elif status == "NOTE":
        badge = "ℹ NOTE"
        color = colors.HexColor("#0369a1")
    else:
        badge = "❌ FAIL"
        color = colors.HexColor("#b91c1c")

    head = Table(
        [[f"Slide {n} · {title}", badge]],
        colWidths=[140*mm, 30*mm],
    )
    head.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "NanumBold"),
        ("FONTSIZE", (0, 0), (0, 0), 11),
        ("FONTSIZE", (1, 0), (1, 0), 9),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (1, 0), (1, 0), color),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    flow += [head, Paragraph(body, P)]
    if advice and advice != "—":
        flow += [Paragraph(f"<i>· {advice}</i>", PSmall)]
    flow += [Spacer(1, 4)]

flow += [PageBreak()]

# ---------------------------------------------------------- WARN 상세
flow += [
    Paragraph("⚠ WARN 상세 — Slide 3 ↔ Slide 12 선행시간 출처 분리", H1),
    Paragraph("문제", H3),
    Paragraph("Slide 3은 '약국 -2주 / 하수 -3주 / 검색 -1주'로 선행시간을 표기. "
             "이는 <b>xgboost.generate_synthetic_data()의 모델링 가정값</b>"
             "(lead_l1=2, lead_l2=3, lead_l3=1)이며, 합성 데이터 학습용 시뮬레이션 lag임.", P),
    Paragraph("그러나 Slide 12·README·lead_time_summary.json은 실측 결과로 "
             "L1=8주 / L2=2주 / L3=3주 / composite=3주 / 17지역 평균 5.9주로 표기.", P),
    Paragraph("→ 동일 발표 안에서 같은 '선행시간'이 다른 숫자 두 벌로 등장. "
             "교수가 '약국이 2주냐 8주냐' 찌르면 한 번에 답 못 함.", P),
    Paragraph("권고 수정안 (택1)", H3),
    Paragraph("① <b>Slide 3에 라벨 추가</b>: 카드 하단에 '※ 합성데이터 모델 가정 (실측은 Slide 12 참조)' "
             "한 줄 회색 텍스트.", P),
    Paragraph("② <b>실측값으로 통일</b>: Slide 3 카드 숫자를 -8주(약국) / -2주(하수) / -3주(검색)로 교체. "
             "단, 시간축 비주얼 순서가 '하수→약국→검색'에서 '약국→검색→하수'로 바뀌므로 그래픽 재작업 필요.", P),
    Paragraph("③ <b>Slide 3을 '교과서적 기대'로 명시</b>: 헤드라인을 '국제 연구가 보여주는 선행 패턴'으로 "
             "바꾸고 Lee 2023·Deng 2025를 출처로 인용. 실측은 Slide 12에서.", P),
    Paragraph("발표 D-1 시점 추천", H3),
    Paragraph("✅ <b>옵션 ①</b> — 그래픽 손 안 대고 텍스트 한 줄만 추가. "
             "리스크 가장 낮고 정직성 점수도 챙김. 5분 작업.", PASS),
    Spacer(1, 8),
]

# ---------------------------------------------------------- 교수 Q&A 카드
flow += [
    Paragraph("교수 Q&A 방어 카드 — Top 12", H1),
]
qa = [
    ("왜 GFT처럼 망하지 않는다고 자신함?",
     "단일 계층 단독 경보를 코드로 차단(scorer.determine_alert_level Gate B). "
     "ablation 결과 FAR 0.538 → 0.162, 약 3.3배 오경보 감소. backtest_17regions.json 검증."),
    ("26주 데이터로 의미 있는 통계?",
     "표본 한계 인정. 다만 17지역 × 60주 = 1,020 sample, walk-forward 5-fold gap=4로 "
     "미래 누설 0. README '한계와 정직성' 섹션에 명시."),
    ("왜 자랑하는 TFT 안 쓰고 XGBoost?",
     "26주 시계열은 transformer 학습에 부족 → fallback 명문화. ml/CLAUDE.md 'TFT는 "
     "PoC 학습 79K params 완료, 실데이터 12주 추가 누적 후 전환' 그대로."),
    ("L2 가중치 0.40 가장 큰데 Granger p=0.267 (유의 X) 모순?",
     "정직 인정. 데이터 26주 한계라 다음 시즌 누적 후 재튜닝. 현재는 임상 합리성"
     "(하수=가장 빠른 생리신호) 기반 prior. README 한계 섹션 명시."),
    ("픽셀 파서 신뢰성? 차트 디자인 바뀌면?",
     "KDCA PDF 일러두기 정의('누적 max 대비 상대수준')와 픽셀 비율이 정확히 일치. "
     "차트 검출 부족 시 silent fail 금지(logger.warning). LAYOUT 상수 한 곳만 수정하면 적응."),
    ("Slide 3 약국 2주 vs Slide 12 약국 8주 — 어느 게 진짜?",
     "Slide 3은 합성 데이터 모델링 가정, Slide 12·README가 실측. "
     "실측 8주는 OTC 구매가 의외로 일찍 시작된다는 뜻 — Lee 2023 결과와 정합."),
    ("Slide 16 12/07 피크 231K 출처?",
     "KCDC 감염병포털(infpublic.kdca.go.kr) 2025-W49 인플루엔자 의사환자 "
     "주간 신고. confirmed_cases 테이블에 1,020건 적재."),
    ("LLM 환각으로 잘못된 의료 권고 내면?",
     "점수·경보레벨은 deterministic 코드(scorer.py)가 결정. LLM은 RAG 가이드라인 "
     "검색 결과를 컨텍스트로만 텍스트 생성. ISMS-P 감사 위해 alert_reports 테이블에 "
     "rag_sources·model_metadata JSONB 보존."),
    ("실제 운영 트래픽 견디나?",
     "현재 cron+DB 직접 INSERT(주 1회 17건). 임계 트래픽 발생 시 K8s 매니페스트의 "
     "Kafka KRaft 토픽(uis.layer1.otc 등)으로 전환 — 코드는 그대로."),
    ("BlueDot·CDC NWSS와 차별점?",
     "BlueDot=뉴스/항공 NLP 단일 도메인. CDC NWSS=하수 단일. 우리는 약국·하수·"
     "검색 3계층 + Gate B 교차검증 — 학부 캡스톤 한계 인정하되 포지셔닝은 우상단."),
    ("Recall 0.768 — 왜 목표 미달?",
     "Gate B 엄격 적용으로 FN 증가. 대신 Precision 0.96 / FAR 0.16으로 오경보 최소화 "
     "(보건당국 신뢰 우선 트레이드오프). Gate 임계 완화 시 Recall 0.85+ 달성 가능."),
    ("Recall 100%(Slide 16) vs 0.768(Slide 12) 충돌?",
     "단위 다름. Slide 12=주차별 alert vs ground truth(walk-forward), Slide 16=시즌"
     "(유행기준) 도래 17지역 적중. 두 측정값 모두 산출물에 별도 저장."),
]
for q, a in qa:
    flow += [
        Paragraph(f"<b>Q.</b> {q}", P),
        Paragraph(f"<b>A.</b> {a}", PSmall),
        Spacer(1, 3),
    ]

flow += [PageBreak()]

# ---------------------------------------------------------- 시간 배분
flow += [
    Paragraph("발표 시간 배분 — 15분 표준 (Q&A 5분 별도)", H1),
]
timing = [
    ["#", "슬라이드", "권장 시간", "전달 핵심"],
    ["1", "S1 표지", "0:30", "수상 콜아웃 한 번 강하게"],
    ["2", "S2 문제", "0:45", "'2주 늦다' 한 줄"],
    ["3", "S3 해법 3-Layer", "1:00", "선행시간은 합성가정 라벨 명시"],
    ["4", "S4 교차검증·연구", "0:45", "GFT 폐기 → 우리 차별점"],
    ["5", "S5 용어집", "0:30", "빠르게 훑기"],
    ["6", "S6 시스템 구조", "0:45", "Kafka는 '운영 예정' 명시"],
    ["7", "S7 5대 결정", "1:00", "'왜'에 1초씩"],
    ["8", "S8 데이터셋·라벨", "0:45", "합성/실 분리"],
    ["9", "S9 KOWAS 픽셀", "1:30", "★ 코드 깊이 — 가장 인상 줌"],
    ["10", "S10 L1·L3·병원체", "0:45", "확장성 한 줄"],
    ["11", "S11 데모", "1:30", "★ 백업영상 미리 띄움"],
    ["12", "S12 실측 성능", "1:00", "F1/Prec/Rec/FAR + 5.9주"],
    ["13", "S13 XAI", "1:00", "L2 0.224 직관 일치"],
    ["14", "S14 walk-forward", "0:45", "gap=4 한 단어"],
    ["15", "S15 17지역", "1:00", "★ Gate A 폐기 정직"],
    ["16", "S16 정합성", "0:45", "Recall 17/17·오경보 3건 명시"],
    ["17", "S17 재현 4줄", "0:45", "★ 가능하면 1줄 라이브"],
    ["18", "S18 RAG/SSE", "0:30", "환각 차단 한 줄"],
    ["19-23", "로드맵·시장·인사이트·특허·확장", "1:30", "묶어서 빠르게"],
    ["24", "S24 팀·Q&A", "0:30", "리스크 정직 + 다음 검증 단계"],
    ["", "합계", "15:00", "Q&A 5분 별도"],
]
tt = Table(timing, colWidths=[10*mm, 60*mm, 22*mm, 78*mm])
tt.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, -1), "Nanum"),
    ("FONTNAME", (0, 0), (-1, 0), "NanumBold"),
    ("FONTNAME", (0, -1), (-1, -1), "NanumBold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f8fafc"), colors.white]),
    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
]))
flow += [tt, Spacer(1, 8)]

# ---------------------------------------------------------- 마무리
flow += [
    Paragraph("최종 체크리스트 (D-1, 4/29)", H2),
    Paragraph("☑ Slide 3 라벨 오버레이 (v2 PPTX 자동 생성 완료)", PASS),
    Paragraph("☑ Slide 16 KCDC 출처 라벨 (v2 PPTX 자동 생성 완료)", PASS),
    Paragraph("☑ outline.md 동일 텍스트 동기화 완료", PASS),
    Paragraph("□ v2 PPTX 육안 확인 — 오버레이 위치/폰트 마음에 드는지 (5분)", P),
    Paragraph("□ Slide 11 데모 백업 영상 인코딩 + USB 저장", P),
    Paragraph("□ Slide 17 4-line 명령어 중 backtest 1줄만 라이브 실행 시연 사전 리허설", P),
    Paragraph("□ Q&A 카드 12개 인쇄 1부 (발표대 옆 거치)", P),
    Paragraph("□ ANTHROPIC_API_KEY/NAVER_CLIENT_ID 발표용 별도 키 준비", P),
    Spacer(1, 6),
    Paragraph("결론: <b>발표 가능 상태.</b> 코드·산출물 정합성 검증 완료, 라벨 이슈 2건 해소.", PASS),
]

doc.build(flow)
print(f"OK → {OUT}  ({OUT.stat().st_size / 1024:.1f}KB)")
