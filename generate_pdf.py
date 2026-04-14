#!/usr/bin/env python3
import os

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# NanumGothic 폰트 경로
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_PATH = os.path.join(FONT_DIR, "NanumGothic.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "NanumGothicBold.ttf")

def check_fonts():
    regular = os.path.exists(FONT_PATH)
    bold = os.path.exists(FONT_BOLD_PATH)
    print(f"NanumGothic regular: {regular} ({FONT_PATH})")
    print(f"NanumGothic bold: {bold} ({FONT_BOLD_PATH})")
    return regular and bold

class PDF(FPDF):
    def header(self):
        self.set_fill_color(30, 50, 100)
        self.rect(0, 0, 210, 12, 'F')
        self.set_font("nanum", size=8)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 3)
        self.cell(0, 6, "Urban Immune System — AI 기반 감염병 조기경보 시스템 | 캡스톤 디자인 회의자료")
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("nanum", size=8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"- {self.page_no()} -", align="C")
        self.set_text_color(0, 0, 0)

    def chapter_title(self, title, level=1):
        if level == 1:
            self.set_fill_color(30, 50, 100)
            self.set_text_color(255, 255, 255)
            self.set_font("nanum_bold", size=14)
            self.ln(4)
            self.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            self.set_text_color(0, 0, 0)
            self.ln(2)
        elif level == 2:
            self.set_fill_color(230, 236, 255)
            self.set_text_color(30, 50, 100)
            self.set_font("nanum_bold", size=12)
            self.ln(3)
            self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            self.set_text_color(0, 0, 0)
            self.ln(1)
        else:
            self.set_font("nanum_bold", size=11)
            self.set_text_color(50, 80, 160)
            self.ln(2)
            self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)

    def body_text(self, text, indent=0):
        self.set_font("nanum", size=10)
        self.set_left_margin(10 + indent)
        self.set_x(10 + indent)
        self.multi_cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_left_margin(10)
        self.ln(1)

    def bullet(self, text, indent=5):
        self.set_font("nanum", size=10)
        self.set_left_margin(10 + indent)
        self.set_x(10 + indent)
        self.multi_cell(0, 6, f"• {text}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_left_margin(10)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            n = len(headers)
            w = 190 / n
            col_widths = [w] * n

        # header
        self.set_font("nanum_bold", size=9)
        self.set_fill_color(60, 80, 160)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, h, border=1, fill=True, align="C")
        self.ln()

        # rows
        self.set_font("nanum", size=9)
        self.set_text_color(0, 0, 0)
        for ri, row in enumerate(rows):
            if ri % 2 == 0:
                self.set_fill_color(245, 247, 255)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 7, str(cell), border=1, fill=True, align="C")
            self.ln()
        self.ln(3)

    def info_box(self, title, lines, color=(240, 248, 255)):
        self.set_fill_color(*color)
        self.set_font("nanum_bold", size=10)
        self.set_text_color(30, 50, 100)
        self.cell(0, 7, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, border="TB")
        self.set_font("nanum", size=9)
        self.set_text_color(40, 40, 40)
        for line in lines:
            self.set_x(14)
            self.cell(0, 6, f"  {line}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def status_badge(self, label, status):
        """인라인 상태 뱃지"""
        colors = {
            "완료": (0, 160, 80),
            "미완료": (200, 50, 50),
            "부분": (200, 140, 0),
            "검증됨": (0, 130, 180),
            "확인필요": (150, 100, 200),
        }
        color = colors.get(status, (100, 100, 100))
        self.set_font("nanum_bold", size=9)
        self.set_text_color(*color)
        self.write(6, f"[{status}]")
        self.set_text_color(0, 0, 0)
        self.set_font("nanum", size=10)
        self.write(6, f"  {label}")
        self.ln()


def build_pdf():
    has_nanum = check_fonts()
    if not has_nanum:
        print("NanumGothic 폰트 없음 — 영문 fallback 사용")

    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(10, 15, 10)
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_font("nanum", "", FONT_PATH)
    pdf.add_font("nanum_bold", "", FONT_BOLD_PATH)

    # ──────────────────────────────────────────────────────────────
    # PAGE 1: 표지
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(20, 40, 100)
    pdf.rect(0, 0, 210, 297, 'F')

    # 장식 원
    pdf.set_fill_color(40, 70, 160)
    pdf.ellipse(140, 160, 180, 180, 'F')
    pdf.set_fill_color(60, 100, 200)
    pdf.ellipse(10, 190, 160, 160, 'F')

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("nanum_bold", size=28)
    pdf.set_xy(15, 80)
    pdf.cell(0, 15, "Urban Immune System")
    pdf.set_xy(15, 98)
    pdf.set_font("nanum", size=16)
    pdf.cell(0, 10, "AI 기반 감염병 조기경보 시스템")

    pdf.set_fill_color(255, 180, 0)
    pdf.rect(15, 115, 4, 30, 'F')
    pdf.set_xy(22, 118)
    pdf.set_font("nanum_bold", size=13)
    pdf.set_text_color(255, 220, 100)
    pdf.cell(0, 8, "캡스톤 디자인 회의자료")
    pdf.set_xy(22, 128)
    pdf.set_font("nanum", size=11)
    pdf.set_text_color(200, 210, 255)
    pdf.cell(0, 7, "팀 역할 분배 | 개발 로드맵 | 아이디어 검증")

    pdf.set_xy(15, 160)
    pdf.set_font("nanum", size=10)
    pdf.set_text_color(160, 180, 230)
    pdf.cell(0, 7, "2026.03.30")

    # 수상 배지
    pdf.set_fill_color(255, 180, 0)
    pdf.rect(120, 155, 75, 22, 'F')
    pdf.set_font("nanum_bold", size=10)
    pdf.set_text_color(30, 30, 30)
    pdf.set_xy(122, 159)
    pdf.cell(71, 6, "2026 LG DX School", align="C")
    pdf.set_xy(122, 166)
    pdf.cell(71, 6, "데이터 아이디어 공모전 대상", align="C")

    pdf.set_text_color(0, 0, 0)

    # ──────────────────────────────────────────────────────────────
    # PAGE 2: 목차
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("목차", 1)
    pdf.ln(2)
    sections = [
        ("1", "프로젝트 현황 요약", "3"),
        ("2", "현재 구현 상태 — 완료/미완료 현황", "4"),
        ("3", "팀원 역할 분배 및 주차별 계획", "5"),
        ("4", "개선 필요 사항 (기술 검증 기반)", "7"),
        ("5", "벤치마킹 분석", "8"),
        ("6", "덧붙이면 좋을 기술 & 아이디어", "9"),
        ("7", "아이디어 검증 체크리스트", "10"),
        ("8", "캡스톤 발표 전략 제안", "11"),
        ("9", "8주 개발 로드맵", "12"),
        ("10", "상용화 가치 및 수익성 시나리오", "14"),
    ]
    pdf.set_font("nanum", size=11)
    for num, title, page in sections:
        pdf.set_x(15)
        pdf.set_text_color(30, 50, 100)
        pdf.set_font("nanum_bold", size=11)
        pdf.write(8, f"{num}. ")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("nanum", size=11)
        pdf.write(8, title)
        pdf.set_text_color(120, 120, 120)
        # dots
        dots = "." * max(1, 60 - len(title) - len(num) * 2)
        pdf.write(8, f" {dots} {page}")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(9)

    # ──────────────────────────────────────────────────────────────
    # PAGE 3: 프로젝트 현황 요약
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("1. 프로젝트 현황 요약", 1)

    pdf.chapter_title("1.1 핵심 아이디어", 2)
    pdf.body_text(
        "의료 데이터(확진 집계)에 의존하지 않고, 3개의 비의료 신호를 교차검증해 "
        "인플루엔자를 1~3주 선행 감지하는 AI 기반 공중보건 조기경보 시스템입니다."
    )

    pdf.chapter_title("3-Layer 신호 구성", 3)
    pdf.table(
        ["Layer", "데이터 소스", "선행시간", "수집 방법"],
        [
            ["L1: 약국 OTC", "감기약/해열제 구매량", "1~2주", "네이버 쇼핑인사이트 API"],
            ["L2: 하수 바이오마커", "인플루엔자 바이러스 농도", "2~3주 (최장)", "KOWAS (환경부) PDF"],
            ["L3: 검색어 트렌드", "독감 증상/타미플루 검색량", "1~2주", "네이버 데이터랩 API"],
        ],
        [28, 52, 30, 80]
    )

    pdf.chapter_title("1.2 검증된 성과 (2024-25 시즌, 26주 실데이터)", 2)
    pdf.table(
        ["모델", "Precision", "Recall", "F1-Score", "오경보"],
        [
            ["약국 단독", "0.00", "0.00", "0.00", "0건"],
            ["하수 단독", "1.00", "0.44", "0.62", "0건"],
            ["검색 단독", "0.67", "0.22", "0.33", "2건"],
            ["3-Layer 통합 ★", "1.00", "0.56", "0.71", "0건"],
        ],
        [50, 30, 25, 30, 25]
    )

    pdf.info_box(
        "핵심 성과 지표",
        [
            "Precision 1.00 — 오경보 0건: 보건 당국 신뢰 확보의 핵심",
            "Granger 인과검정: 3개 Layer 모두 p < 0.05 통계적 유의성 확인",
            "F1-Score 0.71: 단독 신호 대비 3-Layer 통합이 명확하게 우수",
            "L2 하수가 2~3주 최장 선행 — 가장 빠른 조기경보 신호"
        ],
        (230, 255, 230)
    )

    pdf.chapter_title("1.3 기술 스택", 2)
    pdf.table(
        ["계층", "기술"],
        [
            ["Frontend", "Streamlit (현재 프로토타입) → Next.js 14 + Deck.gl (목표)"],
            ["Backend", "FastAPI + SQLAlchemy (async)"],
            ["파이프라인", "Kafka KRaft + httpx + pdfplumber + APScheduler"],
            ["ML", "TFT (PyTorch Forecasting) + Autoencoder + RAG-LLM (GPT-4o/Claude)"],
            ["DB", "TimescaleDB (시계열) + Qdrant (벡터)"],
            ["Infra", "Docker Compose (개발) / Kubernetes GKE (배포)"],
        ],
        [40, 150]
    )

    # ──────────────────────────────────────────────────────────────
    # PAGE 4: 구현 상태
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("2. 현재 구현 상태", 1)

    pdf.chapter_title("2.1 완료된 모듈", 2)
    done_items = [
        "Streamlit 대시보드 5탭 (위험도 지도, 시계열, 상관관계, 교차검증, AI 리포트)",
        "데이터 수집기 3종 (otc_collector, wastewater, search_collector)",
        "Kafka 프로듀서 + Min-Max 정규화 (4개 토픽, 0~100 스케일)",
        "TFT 모델 정의 (7/14/21일 분위수 예측 구조)",
        "Deep Autoencoder 이상탐지 (4→64→32→16→32→64→4)",
        "RAG-LLM 경보 리포트 프롬프트 + Qdrant 클라이언트",
        "TimescaleDB 스키마 (하이퍼테이블 + 물리화 뷰)",
        "K8s 배포 매니페스트 (backend/pipeline/ml deployment)",
        "CI/CD 및 테스트 (GitHub Actions + pytest 22개)",
    ]
    for item in done_items:
        pdf.set_font("nanum", size=10)
        pdf.set_text_color(0, 150, 80)
        pdf.set_x(12)
        pdf.write(6, "[완료] ")
        pdf.set_text_color(0, 0, 0)
        pdf.write(6, item)
        pdf.ln(7)

    pdf.chapter_title("2.2 미완료 — 서비스화 필수", 2)
    pdf.table(
        ["항목", "현재 상태", "필요 작업"],
        [
            ["실제 API 키 연동", ".env.example만 존재", "네이버 API 키 발급 + 통합 테스트"],
            ["TFT 모델 학습", "코드만, 체크포인트 없음", "실데이터 학습 + walk-forward 검증"],
            ["ML 모델 서빙", "serve.py 초안 구현", "FastAPI ↔ TFT/Autoencoder 실제 추론 연동"],
            ["FastAPI 엔드포인트", "스켈레톤만 존재", "predictions, alerts 쿼리 로직 구현"],
            ["Next.js 프론트엔드", "초기 화면/컴포넌트 구현", "실데이터 연동 + 상호작용 고도화"],
            ["KOWAS PDF 자동화", "수동 추출만 가능", "Selenium 기반 자동 크롤러 개발"],
            ["Kafka Consumer", "Producer만 구현됨", "Consumer + DB 적재 배치 로직"],
            ["통합 테스트", "단위 테스트만 존재", "E2E 파이프라인 테스트 추가"],
        ],
        [50, 45, 95]
    )

    # ──────────────────────────────────────────────────────────────
    # PAGE 5~6: 팀 역할 분배
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("3. 팀원 역할 분배", 1)

    roles = [
        {
            "name": "역할 A: Backend + API",
            "desc": "FastAPI 백엔드 완성 + DB 연동",
            "tasks": [
                "FastAPI /predictions/forecast 엔드포인트 구현",
                "FastAPI /alerts/current, /alerts/generate 구현",
                "TimescaleDB 시계열 쿼리 최적화",
                "Kafka Consumer 구현 (토픽 → DB 적재)",
                "API 인증/인가 (JWT 또는 API Key)",
                "Swagger 문서 자동 생성 유지",
            ],
            "skills": "Python, FastAPI, SQLAlchemy, PostgreSQL",
            "files": "backend/, infra/db/init.sql",
            "color": (230, 240, 255),
        },
        {
            "name": "역할 B: 데이터 파이프라인",
            "desc": "실제 데이터 수집 파이프라인 완성 + 자동화",
            "tasks": [
                "네이버 쇼핑인사이트 API 연동 (L1 OTC)",
                "네이버 데이터랩 API 연동 (L3 검색)",
                "KOWAS PDF 자동 크롤링 구현 (난이도 최고)",
                "기상청 API 연동 (보조 데이터)",
                "APScheduler 주간 스케줄링 안정화",
                "데이터 검증 + 결측치 처리 로직",
            ],
            "skills": "Python, httpx, Kafka, Selenium/pdfplumber",
            "files": "pipeline/",
            "color": (255, 240, 225),
        },
        {
            "name": "역할 C: ML / AI 엔진",
            "desc": "TFT 모델 학습 + Autoencoder + RAG 고도화",
            "tasks": [
                "TFT 모델 실데이터 학습 (26주+ 데이터 필요)",
                "walk-forward 학습 파이프라인 자동화",
                "Autoencoder threshold 튜닝",
                "RAG 역학 문서 임베딩 (논문/가이드 10~20편)",
                "모델 서빙 (ml/serve.py) 구현",
                "모델 성능 모니터링 지표 설계",
            ],
            "skills": "PyTorch, pytorch_forecasting, scikit-learn, LangChain",
            "files": "ml/",
            "color": (230, 255, 235),
        },
        {
            "name": "역할 D: Frontend",
            "desc": "Next.js 대시보드 구축 + UX 설계",
            "tasks": [
                "Next.js 14 App Router 셋업",
                "Deck.gl 기반 인터랙티브 위험도 지도",
                "Recharts 시계열 차트 컴포넌트",
                "실시간 경보 알림 UI (배너/팝업)",
                "반응형 디자인 (모바일 대응)",
                "FastAPI REST API 연동 (fetch/SWR)",
            ],
            "skills": "React, TypeScript, Next.js, Deck.gl",
            "files": "frontend/",
            "color": (255, 230, 255),
        },
    ]

    for role in roles:
        r, g, b = role["color"]
        pdf.set_fill_color(r, g, b)
        pdf.set_font("nanum_bold", size=11)
        pdf.set_text_color(20, 40, 120)
        pdf.cell(0, 9, f"  {role['name']} — {role['desc']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("nanum", size=9)
        pdf.set_fill_color(min(255,r+10), min(255,g+10), min(255,b+10))
        for t in role["tasks"]:
            pdf.set_x(16)
            pdf.cell(0, 6, f"• {t}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_font("nanum_bold", size=9)
        pdf.set_x(14)
        pdf.set_fill_color(max(0,r-10), max(0,g-10), max(0,b-10))
        pdf.cell(0, 6, f"  필요 역량: {role['skills']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_x(14)
        pdf.cell(0, 6, f"  주요 파일: {role['files']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(3)

    # 주차별 계획 표
    pdf.add_page()
    pdf.chapter_title("3.1 주차별 역할 매트릭스", 2)
    pdf.table(
        ["주차", "A (Backend)", "B (Pipeline)", "C (ML)", "D (Frontend)"],
        [
            [
                "1~2주",
                "Kafka Consumer / DB 쿼리 구현",
                "Naver API 연동 / KOWAS 설계",
                "TFT 전처리 / 학습 파이프라인",
                "Next.js 셋업 / 지도 컴포넌트",
            ],
            [
                "3~4주",
                "signals API 완성 / alerts API 완성",
                "L1+L3 안정화 / L2 PDF 크롤러",
                "TFT 학습+검증 / Autoencoder 튜닝",
                "차트 컴포넌트 / API 연동",
            ],
            [
                "5~6주",
                "predictions API / 인증·인가 추가",
                "스케줄러 안정화 / 통합 테스트",
                "RAG 문서 수집 / 모델 서빙",
                "경보 UI / 반응형 대응",
            ],
            [
                "7~8주",
                "성능 최적화 / 부하 테스트",
                "장애 복구 / 데이터 품질",
                "성능 모니터링 / 재학습 자동화",
                "UX 테스트 / 배포 준비",
            ],
        ],
        [15, 47, 48, 42, 38]
    )

    pdf.info_box(
        "5인 팀 구성 시 추가 역할",
        [
            "역할 E: DevOps + 인프라 — Docker→K8s 마이그레이션, GKE 클러스터 관리",
            "역할 E 추가 업무: Prometheus + Grafana 모니터링, CI/CD 고도화, 보안 (RBAC, TLS)",
            "역할 E 필요 역량: Docker, Kubernetes, GitHub Actions, GCP",
        ]
    )

    # ──────────────────────────────────────────────────────────────
    # PAGE 7: 개선 필요 사항
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("4. 개선 필요 사항 (기술 검증 기반)", 1)

    pdf.chapter_title("4.1 CRITICAL — 서비스화 필수 개선", 2)

    critical = [
        (
            "(1) KOWAS PDF 자동화",
            "현재 수동 PDF 다운로드 + 파싱 → 서비스화 불가",
            "Selenium/Playwright로 KOWAS 사이트 자동 크롤링 → PDF 저장 → 파싱 파이프라인 완성",
            "KOWAS 사이트 구조 변경 시 크롤러 깨짐 → 사이트 변경 모니터링 로직 추가 필요"
        ),
        (
            "(2) Kafka Consumer 부재",
            "Producer만 존재 — Kafka에 데이터를 넣기만 하고 TimescaleDB에 적재 안 됨",
            "Consumer 그룹 구현 + DB INSERT 배치 처리 + 오류 재시도 로직",
            "Consumer lag 모니터링 필요 (Kafka UI 활용)"
        ),
        (
            "(3) TFT 학습 데이터 부족",
            "26주 데이터로는 TFT 학습 시 과적합 위험 (TFT는 수백~수천 시점 필요)",
            "2019-2024 과거 시즌 KOWAS 데이터 역추적 + 데이터 증강 (TimeGAN, sliding window)",
            "데이터 부족 시 더 가벼운 모델 (LSTM, ARIMA + 앙상블) 병행 검토 필요"
        ),
        (
            "(4) 실시간성 정의 재설정",
            "3개 Layer 모두 주 1회 갱신 → '실시간 경보'라고 하기 어색",
            "L3 검색은 일간 갱신 가능 / L1, L2는 주간 한계 → '주간 경보 + 일간 보조 신호' 구조로 명확히 재정의",
            "사용자/발표에서 갱신 주기를 솔직하게 명시해야 신뢰성 확보"
        ),
    ]

    for title, problem, solution, risk in critical:
        pdf.set_fill_color(255, 240, 240)
        pdf.set_font("nanum_bold", size=10)
        pdf.set_text_color(180, 30, 30)
        pdf.cell(0, 7, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("nanum", size=9)
        pdf.set_fill_color(255, 248, 248)
        pdf.set_x(14)
        pdf.cell(0, 6, f"  문제: {problem}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_x(14)
        pdf.set_fill_color(240, 255, 240)
        pdf.multi_cell(0, 6, f"  해결: {solution}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_x(14)
        pdf.set_fill_color(255, 250, 230)
        pdf.multi_cell(0, 6, f"  리스크: {risk}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(3)

    pdf.chapter_title("4.2 IMPORTANT — 품질 향상", 2)
    important = [
        "지역 세분화: 지도에 구별 시뮬레이션 데이터 → KOWAS 지역별 + 네이버 API 지역 파라미터로 실제 데이터화",
        "모델 해석가능성: TFT attention weights → SHAP values + Layer별 기여도 시각화 추가",
        "다중 질병 확장: 코로나/RSV/노로바이러스 등 다른 질병용 Layer 추가 가능 구조 설계 (캡스톤 어필 포인트)",
    ]
    for item in important:
        pdf.bullet(item)

    # ──────────────────────────────────────────────────────────────
    # PAGE 8: 벤치마킹
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("5. 벤치마킹 분석", 1)

    pdf.chapter_title("5.1 국내외 유사 시스템", 2)
    pdf.table(
        ["시스템", "운영 주체", "데이터 소스", "선행시간", "한계"],
        [
            ["KCDC 감염병 감시", "질병관리청", "의료기관 신고", "0일(후행)", "보고 지연"],
            ["Google Flu Trends", "Google (폐지)", "검색어", "1~2주", "과대추정, 2015 폐지"],
            ["KOWAS", "환경부", "하수 바이러스", "2~3주", "PDF만 제공, API 없음"],
            ["Biobot Analytics", "미국 스타트업", "하수", "2~3주", "미국 한정, 유료"],
            ["BlueDot", "캐나다 스타트업", "항공+뉴스+기후", "수일", "B2B, 비공개"],
            ["UIS (우리)", "오픈소스", "OTC+하수+검색", "1~3주", "데이터 자동화 진행중"],
        ],
        [35, 30, 35, 20, 70]
    )

    pdf.chapter_title("5.2 우리 시스템의 차별점", 2)
    diffs = [
        ("3-Layer 교차검증", "Google Flu Trends의 단일 신호 실패 극복. 독립된 3개 신호 교차로 오경보 0건 달성"),
        ("하수 데이터 ML 통합", "국내에서 KOWAS 데이터를 ML 예측 파이프라인에 통합한 거의 유일한 사례"),
        ("오픈소스 + 무료", "Biobot/BlueDot은 유료 B2B. 우리는 오픈소스로 지자체 직접 도입 가능"),
        ("RAG-LLM 리포트", "단순 수치가 아닌 역학 근거 기반 자연어 경보 리포트 자동 생성"),
        ("한국 특화", "네이버 API + KOWAS + 기상청 — 국내 데이터에 완전 최적화"),
    ]
    for key, val in diffs:
        pdf.set_font("nanum_bold", size=10)
        pdf.set_text_color(30, 80, 160)
        pdf.set_x(12)
        pdf.write(7, f"▶ {key}: ")
        pdf.set_font("nanum", size=10)
        pdf.set_text_color(0, 0, 0)
        pdf.write(7, val)
        pdf.ln(8)

    pdf.chapter_title("5.3 학술 근거", 2)
    refs = [
        "Keshaviah et al. (2023) \"Wastewater surveillance as a leading COVID-19 indicator\" — Nature Communications",
        "Lazer et al. (2014) \"The Parable of Google Flu Trends\" — Science (Google Flu Trends 실패 분석)",
        (
            "Lim et al. (2021) "
            "\"Temporal Fusion Transformers for Interpretable Multi-horizon Time Series Forecasting\" — IJF"
        ),
    ]
    for ref in refs:
        pdf.bullet(ref)

    # ──────────────────────────────────────────────────────────────
    # PAGE 9: 기술 아이디어
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("6. 덧붙이면 좋을 기술 & 아이디어", 1)

    pdf.chapter_title("6.1 기술 확장 아이디어", 2)
    pdf.table(
        ["기술", "적용 방안", "난이도", "임팩트"],
        [
            ["Graph Neural Network", "구 간 인구 이동 패턴 모델링 (지하철 유동인구)", "중간", "★★★★★"],
            ["Conformal Prediction", "예측 불확실성 구간 보장 (신뢰구간)", "낮음", "★★★★"],
            ["Digital Twin", "서울시 감염 확산 시뮬레이션 (SEIR+지리)", "높음", "★★★★★"],
            ["LLM Agent", "데이터 수집→분석→경보 자율 에이전트", "중간", "★★★★"],
            ["Federated Learning", "여러 지자체 데이터 프라이버시 보존 학습", "높음", "★★★★★"],
            ["Edge Computing", "하수처리장 IoT 센서 + 엣지 AI 배치", "높음", "★★★★★"],
        ],
        [45, 75, 22, 28]
    )

    pdf.chapter_title("6.2 데이터 소스 확장", 2)
    pdf.table(
        ["데이터", "선행성", "접근성", "활용 방안"],
        [
            ["HIRA 의약품 처방", "동시~1주", "공공 API", "L1 보강 (처방 vs 구매 교차검증)"],
            ["응급실 방문 (NEDIS)", "동시", "공공 API", "실시간 검증용 Ground Truth"],
            ["지하철 유동인구", "동시", "서울 열린데이터", "구 간 확산 예측 (GNN 입력)"],
            ["대기질 (에어코리아)", "보조", "공공 API", "호흡기 질환 상관 분석"],
            ["학교 결석률", "1주", "교육청", "학령기 감염 조기 지표"],
            ["SNS/커뮤니티 텍스트", "실시간", "크롤링", "NLP 기반 증상 텍스트 탐지"],
        ],
        [40, 22, 30, 98]
    )

    pdf.chapter_title("6.3 서비스화 아이디어 (수익 모델)", 2)
    pdf.table(
        ["아이디어", "대상 고객", "수익 모델", "우선순위"],
        [
            ["지자체 SaaS", "서울시 25개 구 보건소", "구독형 (월/연)", "★★★★★"],
            ["제약사 수요 예측", "감기약 제조사/유통사", "데이터 분석 리포트", "★★★★"],
            ["보험 리스크 분석", "보험사 언더라이팅팀", "컨설팅 프로젝트", "★★★"],
            ["연구자용 API", "대학/연구기관", "프리미엄 API 구독", "★★★"],
            ["시민 앱", "일반 시민", "프리미엄/광고", "★★"],
        ],
        [40, 50, 45, 25]
    )

    # ──────────────────────────────────────────────────────────────
    # PAGE 10: 아이디어 검증
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("7. 아이디어 검증 체크리스트", 1)

    pdf.chapter_title("7.1 기술 검증 현황", 2)
    pdf.table(
        ["검증 항목", "상태", "근거"],
        [
            ["3-Layer가 단일 신호보다 우수한가?", "완료", "F1: 0.71 vs 단독 최대 0.62"],
            ["Granger 인과성이 있는가?", "완료", "3개 Layer p < 0.05"],
            ["오경보 없이 경보 가능한가?", "완료", "Precision 1.00, 오경보 0건"],
            ["TFT가 이 데이터에 적합한가?", "부분", "코드 완성, 실학습 미완 — 데이터 부족 우려"],
            ["RAG-LLM이 유용한 리포트 생성?", "부분", "프롬프트 완성, 역학 문서 임베딩 미완"],
            ["Kafka 파이프라인이 안정적인가?", "부분", "Producer 완성, Consumer 미완"],
        ],
        [90, 20, 80]
    )

    pdf.chapter_title("7.2 시장 검증 현황", 2)
    pdf.table(
        ["검증 항목", "상태", "비고"],
        [
            ["감염병 조기경보 수요가 있는가?", "완료", "코로나 이후 수요 급증, 정부 예산 확대"],
            ["경쟁사 대비 차별점이 있는가?", "완료", "국내 유일 3-Layer + 오픈소스"],
            ["보건 당국이 도입할 의향?", "미검증", "PoC 후 서울시 보건환경연구원 접촉 필요"],
            ["의료기기 인증 규제 적용?", "확인필요", "의료 진단 목적 아닌 '공중보건 참고' 포지셔닝"],
            ["개인정보 법적 이슈?", "확인필요", "네이버 검색 데이터 집계 — 개인정보 비포함 확인 필요"],
        ],
        [90, 22, 78]
    )

    pdf.chapter_title("7.3 사업성 검증", 2)
    biz = [
        ("MVP로 가치 입증 가능한가?", True, "Streamlit 데모 + 26주 검증 결과로 충분한 어필 가능"),
        ("초기 도입 고객은?", True, "서울시 보건소 / 질병관리청 공중보건실 — 공공 부문 우선"),
        ("확장 경로가 명확한가?", True, "인플루엔자 → 다중 질병, 서울 → 전국, 한국 → 해외"),
        ("오픈소스 공개 전략?", True, "GitHub 공개 + 지자체 커스터마이즈 지원으로 저변 확대"),
    ]
    for q, ok, note in biz:
        pdf.set_font("nanum_bold", size=10)
        pdf.set_text_color(0 if ok else 180, 150 if ok else 30, 0 if ok else 30)
        pdf.set_x(12)
        pdf.write(7, ("[완료] " if ok else "? ") + q)
        pdf.set_font("nanum", size=9)
        pdf.set_text_color(60, 60, 60)
        pdf.write(7, f"  →  {note}")
        pdf.ln(8)

    # ──────────────────────────────────────────────────────────────
    # PAGE 11: 캡스톤 발표 전략
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("8. 캡스톤 발표 전략 제안", 1)

    pdf.chapter_title("8.1 발표 구조 (15분 기준)", 2)
    pdf.table(
        ["시간", "내용", "핵심 포인트"],
        [
            ["0~2분", "문제 제기", "Google Flu Trends 실패 + 국내 감시 지연 사례"],
            ["2~5분", "해결책 제시", "3-Layer 교차검증 아키텍처 다이어그램"],
            ["5~8분", "기술 데모", "Streamlit 대시보드 라이브 시연"],
            ["8~11분", "검증 결과", "F1 0.71, 오경보 0건, Granger 유의성"],
            ["11~13분", "서비스화 로드맵", "8주 개발 계획 + 수익 모델"],
            ["13~15분", "Q&A", "기대 질문 사전 준비"],
        ],
        [18, 30, 142]
    )

    pdf.chapter_title("8.2 핵심 메시지 (슬로건)", 2)
    messages = [
        "\"의료 데이터 없이도 감염병을 미리 감지할 수 있습니다\"",
        "\"Google Flu Trends가 실패한 이유를 3-Layer 교차검증으로 해결했습니다\"",
        "\"오경보 0건 — 보건 당국이 실제로 믿고 쓸 수 있는 시스템\"",
    ]
    for msg in messages:
        pdf.set_fill_color(230, 240, 255)
        pdf.set_font("nanum_bold", size=11)
        pdf.set_text_color(20, 50, 150)
        pdf.set_x(12)
        pdf.cell(0, 9, f"  {msg}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(3)

    pdf.chapter_title("8.3 예상 Q&A", 2)
    pdf.set_text_color(0, 0, 0)
    qas = [
        ("Q. 데이터가 26주뿐인데 충분한가?",
         "A. 검증 데이터로는 충분 (2024-25 실시즌). 모델 학습엔 과거 시즌 역추적으로 보완 예정."),
        ("Q. 하수 데이터를 자동으로 못 받으면?",
         "A. KOWAS 자동 크롤러 개발이 B 역할의 최우선 과제. 실패 시 수동→반자동으로 단계적 전환."),
        ("Q. TFT가 너무 복잡한 모델 아닌가?",
         "A. LSTM 등 단순 모델과 병행 비교 예정. 해석가능성(attention)은 보건 당국 신뢰에 중요."),
        ("Q. 오경보 0건은 Recall 희생 아닌가?",
         "A. 의도된 설계. 보건 당국에 '오경보 경보'는 신뢰 붕괴. Recall 개선은 장기 목표."),
    ]
    for q, a in qas:
        pdf.set_fill_color(245, 248, 255)
        pdf.set_font("nanum_bold", size=9)
        pdf.set_text_color(30, 60, 140)
        pdf.set_x(12)
        pdf.multi_cell(0, 6, f"  {q}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_font("nanum", size=9)
        pdf.set_text_color(40, 40, 40)
        pdf.set_fill_color(250, 252, 255)
        pdf.set_x(14)
        pdf.multi_cell(0, 6, f"  {a}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(3)

    # ──────────────────────────────────────────────────────────────
    # PAGE 12~13: 개발 로드맵
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("9. 8주 개발 로드맵", 1)

    pdf.info_box(
        "운영 원칙",
        [
            "각 주차는 구현, 검증, 문서화를 동시에 완료해야 함",
            "완료 기준은 코드 작성이 아니라 테스트/로그/시연 가능 상태까지 포함",
            "발표용 문서와 실제 저장소 상태가 어긋나지 않도록 README와 회의자료를 함께 갱신",
        ],
        (235, 245, 255)
    )

    pdf.table(
        ["주차", "핵심 목표", "검증 산출물"],
        [
            ["1주차", "환경 기준선 고정", "compose 기동 로그, health check"],
            ["2주차", "수집 자동화 1차", "적재 데이터 샘플, API 응답 캡처"],
            ["3주차", "저장/조회 파이프라인", "DB 적재 통합 테스트"],
            ["4주차", "모델 1차 검증", "walk-forward 결과표"],
            ["5주차", "경보 서비스 연결", "경보 생성 E2E 시나리오"],
            ["6주차", "데모 완성", "리허설 영상, 시연 로그"],
            ["7주차", "운영 품질 강화", "부하 테스트 결과"],
            ["8주차", "발표/제출 마감", "최종 보고서, 발표 자료, 체크리스트"],
        ],
        [20, 80, 90]
    )

    phases = [
        ("Phase 1 (1~2주): 데이터 흐름 고정", (255, 240, 220), [
            "네이버 API 키 발급 및 L1/L3/KMA 실연동 테스트",
            "KOWAS PDF 자동 다운로드 프로토타입 구현",
            "Kafka Consumer 구현 + TimescaleDB 적재 파이프라인",
            "signals/latest, signals/timeseries 실데이터 응답 검증",
            "Docker Compose 기준 End-to-End 흐름 재현",
        ]),
        ("Phase 2 (3~4주): 모델링 고도화", (220, 240, 255), [
            "과거 시즌 데이터 역추적 수집 (가능 범위 2019~2024)",
            "TFT 모델 학습 + walk-forward 교차검증",
            "Autoencoder threshold 최적화",
            "RAG 역학 문서 10~20편 임베딩 + Qdrant 업로드",
            "placeholder 예측 응답 제거",
        ]),
        ("Phase 3 (5~6주): 서비스 통합", (220, 255, 230), [
            "alerts/current, alerts/generate, predictions/forecast 실제 구현",
            "Next.js 대시보드 MVP 실데이터 연동",
            "AI 리포트/경보 배너 데모 경로 완성",
            "API 인증 또는 내부용 API Key 반영",
            "발표용 데모 시나리오 정리",
        ]),
        ("Phase 4 (7~8주): 안정화 + 발표 준비", (235, 220, 255), [
            "통합 테스트 + 부하 테스트",
            "K8s 배포 재현성 + 모니터링 기본 지표 정리",
            "fallback 데모 시나리오 준비",
            "README, 회의자료, 발표 자료 동기화",
            "최종 보고서와 release tag 정리",
        ]),
    ]

    for phase_title, color, tasks in phases:
        r, g, b = color
        pdf.set_fill_color(max(0, r - 10), max(0, g - 10), max(0, b - 10))
        pdf.set_font("nanum_bold", size=11)
        pdf.set_text_color(30, 30, 80)
        pdf.cell(0, 9, f"  {phase_title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("nanum", size=9)
        pdf.set_fill_color(r, g, b)
        for t in tasks:
            pdf.set_x(16)
            pdf.multi_cell(0, 6, f"- {t}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(3)

    pdf.add_page()
    pdf.chapter_title("9.1 리스크 및 완료 기준", 2)
    pdf.table(
        ["리스크", "영향", "대응"],
        [
            ["KOWAS 자동화 실패", "L2 실시간성 저하", "수동 다운로드 + 반자동 파싱 fallback 유지"],
            ["TFT 학습 데이터 부족", "과적합 위험", "단순 모델 병행, 시즌 데이터 추가 확보"],
            ["ML 의존성 과대", "개발 환경 불안정", "CPU 전용 requirements 분리, 학습/서빙 분리"],
            ["프론트/백 스키마 불일치", "데모 실패", "OpenAPI 기준 계약 고정, mock contract 테스트"],
            ["발표 직전 수집 장애", "실시간 시연 실패", "검증 데이터 replay 시나리오 준비"],
        ],
        [45, 45, 100]
    )

    pdf.info_box(
        "성공 기준 (캡스톤 심사 기준 제안)",
        [
            "기술 완성도: 3개 Layer 실데이터 자동 수집 + TFT 예측 + 웹 대시보드 통합 작동",
            "검증 결과: F1-Score 0.70 이상 유지 + 오경보 0건 유지",
            "서비스성: Next.js 대시보드에서 실시간 신호 조회 + AI 경보 리포트 생성",
            "확장성: 최소 1개 추가 질병 또는 지역 확장 시연",
        ],
        (230, 255, 240)
    )

    # ──────────────────────────────────────────────────────────────
    # PAGE 14: 상용화 가치 및 수익성 시나리오
    # ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("10. 상용화 가치 및 수익성 시나리오", 1)
    pdf.body_text(
        "아래 수치는 확정 계약가나 확정 수익이 아니라, 현재 저장소 구조를 실제 서비스로 운영한다고 "
        "가정한 보수적 사업성 시나리오다. 서울 25개 보건소 수준의 초기 시장과 전국 252개 보건소 "
        "자료를 기준으로 추정했다."
    )

    pdf.info_box(
        "핵심 가정",
        [
            "초기 시장: 서울 25개 자치구 기반 25개 보건소 수준 가정",
            "전국 확장 하한선: 보건복지부 자료 기준 보건소 252개소",
            "판매 단가: 기관당 월 200만원 / 300만원 / 400만원",
            "환율 가정: 1 USD = 1,500 KRW",
            "직접 운영 인건비: 월 1,100만원, 회사 공통 고정비: 월 4,200만원",
        ],
        (255, 245, 230)
    )

    pdf.table(
        ["항목", "가정", "월 비용"],
        [
            ["GKE", "4 vCPU, 16 GiB, 730h", "$187.43"],
            ["LLM", "월 750건 보고서 생성", "$48.00"],
            ["기타 버퍼", "로그/백업/예비비", "$300.00"],
            ["인프라 합계", "USD 합산", "$535.43"],
            ["인프라 합계", "KRW 환산", "803,152원"],
            ["직접원가", "인프라 + 운영 인건비", "11,803,152원"],
            ["총원가", "직접원가 + 공통 고정비", "53,803,152원"],
        ],
        [42, 82, 56]
    )

    pdf.table(
        ["단가", "서울 25개 월매출", "월 영업이익", "영업이익률", "BEP"],
        [
            ["200만원", "5,000만원", "-380만 3,152원", "-7.6%", "27개"],
            ["300만원", "7,500만원", "2,119만 6,848원", "28.3%", "18개"],
            ["400만원", "1억원", "4,619만 6,848원", "46.2%", "14개"],
        ],
        [26, 44, 50, 28, 22]
    )

    pdf.info_box(
        "해석",
        [
            "기관당 월 300만원 계약이 실제 성립할 경우 서울 25개 보건소 가정에서 손익분기 가능성이 있음",
            "기준 시나리오(전국 252개, 월 300만원) 연 매출 잠재력은 약 90억 7,200만원",
            "즉, 서울 시범사업과 초기 유료 전환이 성공할 경우 전국 확장 여지가 있다는 의미로 해석해야 함",
        ],
        (235, 250, 235)
    )

    pdf.body_text(
        "출처: 보건복지부 전국 보건기관 현황(보건소 252개소), Google Cloud GKE 공식 가격표, "
        "OpenAI GPT-4.1 공식 가격표. 인건비와 공통 고정비는 내부 보수 추정치이며 실제 사업화 시 달라질 수 있다."
    )

    # 저장
    out_path = "/tmp/캡스톤_회의자료.pdf"
    pdf.output(out_path)
    print(f"PDF 생성 완료: {out_path}")
    return out_path


if __name__ == "__main__":
    build_pdf()
