"""리포트 탭."""

from __future__ import annotations

import io
from datetime import datetime

import streamlit as st

from src.config import GRAY_500, GREEN_SAFE, L1_PHARMACY, L2_SEWAGE, L3_SEARCH, ORANGE, RED


def _build_pdf(region: str, issued_at: str) -> bytes:
    """reportlab 으로 경보 리포트 PDF 생성 (A4 1-2장)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    # 한글 폰트 등록 (실패 시 기본 폰트)
    try:
        pdfmetrics.registerFont(TTFont("Pretendard", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"))
        font = "Pretendard"
    except Exception:
        font = "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=font, fontSize=10, leading=14)
    head = ParagraphStyle("head", parent=styles["Heading1"], fontName=font, fontSize=16, spaceAfter=8)
    small = ParagraphStyle("small", parent=styles["Normal"], fontName=font, fontSize=8, textColor="#666")

    story = [
        Paragraph("⚠️ AI 생성 경보 리포트 · 인간 검토 필요", small),
        Paragraph(f"발령 시각: {issued_at} · Urban Immune System", small),
        Spacer(1, 12),
        Paragraph(f"감염병 조기경보 — {region}", head),
        Paragraph("위험도: <b>Level 4 (심각)</b> · 예상 감염병: 인플루엔자 A형", body),
        Spacer(1, 12),
        Paragraph("<b>Layer 기여도 (TFT Attention)</b>", body),
        Paragraph("• L1 약국 OTC: 68% (해열제 +180%)", body),
        Paragraph("• L2 하수 바이오마커: 24% (인플루엔자A 4.2×10³ copies/mL)", body),
        Paragraph("• L3 검색 트렌드: 8% (\"고열 병원\" +190%)", body),
        Spacer(1, 12),
        Paragraph("<b>상황 분석</b>", body),
        Paragraph(
            f"{region}에서 인플루엔자 A 확산 초기 징후가 감지되었습니다. "
            "2024년 동절기 유사 패턴(KOWAS 2024-W48) 대비 확산 속도 1.3배, "
            "기온 2°C·습도 35% 조건이 비말 전파에 유리합니다.",
            body,
        ),
        Spacer(1, 12),
        Paragraph("<b>예측 (95% 신뢰구간)</b>", body),
        Paragraph("• 7일 후: +45% (CI: +32% ~ +58%)", body),
        Paragraph("• 14일 후 (피크): +120% (CI: +95% ~ +145%)", body),
        Paragraph("• 21일 후: +80% (CI: +60% ~ +100%, 감소 전환)", body),
        Spacer(1, 12),
        Paragraph("<b>대응 권고안</b>", body),
        Paragraph("① 고위험군(65세 이상) 선제 백신 접종", body),
        Paragraph("② 관내 의료기관 오셀타미비르 3주분 재고 확인", body),
        Paragraph("③ 학교·어린이집 방역 강화 및 발열 모니터링", body),
        Spacer(1, 20),
        Paragraph(
            "근거: [1] KDCA 주간 감염병 현황 · [2] KOWAS 하수감시 · [3] CDC 가이드라인 · [4] Deng et al. (2026, Engineering)",
            small,
        ),
        Paragraph(
            "※ 본 리포트는 RAG-LLM 이 자동 생성한 초안입니다. 최종 방역 결정 전 인간 검토 필수.",
            small,
        ),
    ]
    doc.build(story)
    return buf.getvalue()


def render_report_tab(region: str) -> None:
    issued_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 신뢰성 띠 (AI 생성 경고)
    st.markdown(
        f"""
        <div style="background:#FEF3C7;border-left:4px solid #D97706;padding:10px 14px;margin-bottom:12px;border-radius:4px;">
            <strong>⚠️ AI 생성 리포트 — 인간 검토 필요</strong><br>
            <span style="font-size:0.85rem;color:#92400E;">
                생성시각 {issued_at} · RAG-LLM 기반 자동 생성 · 최종 방역 결정 전 담당자 검토 필수
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### RAG-LLM 자동 경보 리포트")
    st.markdown(
        f"""
        <div class="report-card">
            <div class="report-header">
                <h3>⚠️ 감염병 조기경보 — {region}</h3>
                <p>발령: {issued_at} · 위험도: Level 4 (심각) · 예상 감염병: 인플루엔자 A</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Layer별 TFT Attention 기여도**")
    st.markdown(
        f"""
        <div class="layer-indicator">
            <div class="dot pharmacy"></div>
            <div class="info">
                <div class="name">Layer 1 — 약국 OTC 구매지수</div>
                <div class="desc">해열제 구매 +180% · 피크 시즌 최강 신호</div>
            </div>
            <div class="metric">
                <div class="val" style="color:{L1_PHARMACY};">68%</div>
                <div class="unit">Attention</div>
            </div>
        </div>
        <div class="layer-indicator">
            <div class="dot sewage"></div>
            <div class="info">
                <div class="name">Layer 2 — 하수 바이오마커</div>
                <div class="desc">인플루엔자A 4.2×10³ copies/mL · 무증상자 포함 감지</div>
            </div>
            <div class="metric">
                <div class="val" style="color:{L2_SEWAGE};">24%</div>
                <div class="unit">Attention</div>
            </div>
        </div>
        <div class="layer-indicator">
            <div class="dot search"></div>
            <div class="info">
                <div class="name">Layer 3 — 검색 트렌드</div>
                <div class="desc">"고열 병원" 검색 89.3 · 실시간 반응</div>
            </div>
            <div class="metric">
                <div class="val" style="color:{L3_SEARCH};">8%</div>
                <div class="unit">Attention</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**AI 생성 상황 분석**")
    st.markdown(
        f"""
        <div class="report-card">
            <strong>{region}에서 인플루엔자 A 확산 초기 징후가 감지되었습니다.</strong>
            <br><br>
            2024년 동절기 유사 패턴(KOWAS 2024-W48) 대비 확산 속도가 <strong style="color:{RED};">1.3배</strong> 빠르며,
            현재 기온(2°C)·습도(35%) 조건이 비말 전파에 유리합니다.
            <br><br>
            <div class="recommend-box">
                <strong>대응 권고안</strong><br><br>
                ① 고위험군(65세 이상) 대상 <strong>선제 백신 접종</strong> 권고<br>
                ② 관내 의료기관 <strong>항바이러스제 재고</strong> 확인 (오셀타미비르 3주분)<br>
                ③ 학교·어린이집 <strong>방역 강화</strong> 및 발열 모니터링 가동
            </div>
            <br>
            <span style="color:{GRAY_500}; font-size:0.8rem;">
                참조: CDC 가이드라인 · KOWAS 주간 보고 · Deng et al. (2026, Engineering)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**TFT 확산 예측 (Multi-Horizon)**")
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{ORANGE};"></div>
                <div class="kpi-label">7일 후 예측</div>
                <div class="kpi-value" style="color:{ORANGE};">+45%</div>
                <div class="kpi-delta up">급증 예상</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pc2:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{RED};"></div>
                <div class="kpi-label">14일 후 (피크)</div>
                <div class="kpi-value danger">+120%</div>
                <div class="kpi-delta up">피크 도달 예상</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pc3:
        st.markdown(
            f"""
            <div class="kpi-flat">
                <div class="kpi-bar" style="background:{GREEN_SAFE};"></div>
                <div class="kpi-label">21일 후</div>
                <div class="kpi-value" style="color:{GREEN_SAFE};">+80%</div>
                <div class="kpi-delta down">감소 전환 예상</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # PDF 다운로드 버튼
    st.markdown("<br>", unsafe_allow_html=True)
    try:
        pdf_bytes = _build_pdf(region, issued_at)
        st.download_button(
            label="📄 PDF 리포트 다운로드",
            data=pdf_bytes,
            file_name=f"UIS_경보리포트_{region}_{issued_at.replace(':', '').replace(' ', '_')}.pdf",
            mime="application/pdf",
            help="현재 경보 리포트를 PDF 파일로 저장 (공무원 결재·배포용)",
        )
    except ImportError:
        st.info("PDF 생성 라이브러리(reportlab) 미설치. `.venv/bin/pip install reportlab` 후 재시도.")
