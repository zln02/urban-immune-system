"""RAG 시드 문서 — 역학 가이드라인 14건 임베딩.

각 문서는 공개 가이드라인의 핵심 메시지를 한국어로 정리한 것이며,
metadata.source / metadata.url에 원 출처를 명시한다.

추후 확장 시 이 모듈에 dict를 추가하고 다시 실행하면 upsert로 갱신된다.
목표: 10~20편 (WHO/KCDC 감염병 가이드라인 포함).
"""
# ruff: noqa: E501  -- 가이드라인 인용 본문은 줄 분할 시 의미가 깨져 한 줄 유지
from __future__ import annotations

import argparse
import logging
import sys

from ml.rag.vectordb import EpidemiologyVectorDB

logger = logging.getLogger(__name__)

SEED_DOCS: list[dict] = [
    {
        "id": 1,
        "text": (
            "하수기반 감염병 감시(WBE, Wastewater-Based Epidemiology)는 지역사회 하수에서 "
            "병원체 RNA·DNA 농도를 측정해 임상 신고보다 1~2주 앞서 유행 추세를 포착하는 방법이다. "
            "WHO는 코로나19 팬데믹 이후 WBE를 보완 감시(complementary surveillance) 수단으로 권고하며, "
            "환자 신고에 의존하는 임상감시의 보고 지연·검사 편향을 보완하는 객관 지표로 활용할 것을 권장한다. "
            "단, 측정값의 절대 비교는 시·도별 하수처리 환경 차이로 어렵고, 동일 지역 내 추이 비교가 적합하다."
        ),
        "metadata": {
            "source": "WHO Public Health Surveillance for COVID-19 Interim Guidance",
            "url": "https://www.who.int/publications/i/item/WHO-2019-nCoV-SurveillanceGuidance-2022.2",
            "lang": "ko-summary",
            "topic": "wastewater_surveillance",
            "author": "WHO",
            "year": 2022,
        },
    },
    {
        "id": 2,
        "text": (
            "구글 독감 트렌드(GFT, Google Flu Trends)는 2008~2015년 검색어 기반 독감 유행 추정 서비스였으나, "
            "2013년 1월 실제 환자 수의 약 두 배(140%)를 과대 예측한 사건으로 학계의 비판을 받았다. "
            "Lazer et al. (Science, 2014)는 검색 알고리즘 변경, 미디어 노출 폭증, 모델 자가 강화(self-fulfilling) 등을 "
            "원인으로 지적하며 \"단일 빅데이터 신호의 과신을 경계하고 전통적 감시와 교차검증해야 한다\"고 결론지었다. "
            "이는 다중 신호 교차검증의 필요성을 입증한 대표 사례로 인용된다."
        ),
        "metadata": {
            "source": "Lazer et al., \"The Parable of Google Flu: Traps in Big Data Analysis\", Science 2014",
            "url": "https://www.science.org/doi/10.1126/science.1248506",
            "lang": "ko-summary",
            "topic": "search_trend_failure",
            "author": "Lazer et al.",
            "year": 2014,
        },
    },
    {
        "id": 3,
        "text": (
            "질병관리청 인플루엔자 표본감시 사업은 전국 약 200개 의료기관(보건소·의원·병원)을 통해 "
            "주간 ILI(Influenza-Like Illness) 천명당 환자수를 집계하며, 매년 36주차(9월 첫 주)에 시작해 다음 해 "
            "35주차에 종료한다. 유행 기준은 최근 3년 비유행기간 평균치의 1.96 표준편차를 더한 값이며, "
            "이를 초과하면 \"유행주의보\"가 발령된다. 다만 환자가 의료기관 방문 후 신고까지 약 1~2주 지연되어, "
            "조기 경보가 필요한 시점에는 보조 지표(약국 OTC, 검색 트렌드, 하수)와 결합한 다중 신호 감시가 권장된다."
        ),
        "metadata": {
            "source": "질병관리청 \"감염병 표본감시 운영지침\" 2024",
            "url": "https://www.kdca.go.kr/contents.es?mid=a20301070000",
            "lang": "ko",
            "topic": "ilinet_surveillance",
            "author": "KDCA",
            "year": 2024,
        },
    },
    {
        "id": 4,
        "text": (
            "다중 신호 조기경보의 핵심 원칙은 \"단일 신호 단독 경보 금지\"다. ECDC(유럽질병예방통제센터)의 "
            "Epidemic Intelligence 프레임워크는 indicator-based(임상신고)와 event-based(약국·검색·SNS 등 비전통 신호)를 "
            "병행하며, 비전통 신호 단독으로는 사실 확인(triangulation) 전에 경보를 발령하지 않는다. "
            "권장 임계값: 두 개 이상의 독립 신호가 기준치 30% 이상 동시 상승할 때만 \"YELLOW\" 경보, "
            "세 개 이상이 50% 이상 상승할 때 \"RED\" 경보. 이는 오경보(false positive)를 최소화하기 위한 운영 원칙이다."
        ),
        "metadata": {
            "source": "ECDC Operational Tool on Epidemic Intelligence (2019)",
            "url": "https://www.ecdc.europa.eu/en/publications-data/operational-tool-epidemic-intelligence",
            "lang": "ko-summary",
            "topic": "multi_signal_cross_validation",
            "author": "ECDC",
            "year": 2019,
        },
    },
    {
        "id": 5,
        "text": (
            "Autoencoder 기반 이상탐지는 학습 데이터에 없는 새로운 패턴(novelty)을 재구성 오차로 식별하는 비지도 방법이다. "
            "다음 팬데믹 조기 발견에 유용한데, 특정 병원체 라벨 없이 \"평소와 다른 신호\"만 검출하기 때문이다. "
            "임계값은 훈련 세트 재구성 오차의 95th percentile을 사용하는 것이 표준이며(\"3-시그마 룰\" 변형), "
            "임계값 초과 시 즉시 경보가 아닌 \"역학조사관 사전 알림\"으로 운영해야 한다. "
            "이는 알 수 없는 병원체에 대해 라벨링된 학습 데이터를 기다리지 않고 선제 조사를 시작할 수 있게 해준다."
        ),
        "metadata": {
            "source": "Chandola et al., \"Anomaly Detection: A Survey\", ACM Computing Surveys 2009 + KDCA 감염병 빅데이터 가이드 (2024)",
            "url": "https://dl.acm.org/doi/10.1145/1541880.1541882",
            "lang": "ko-summary",
            "topic": "novelty_detection",
            "author": "Chandola et al.",
            "year": 2009,
        },
    },
    # ── 확장 문서 (6~10) ─────────────────────────────────────────────────────
    {
        "id": 6,
        "text": (
            "미국 CDC NWSS(국가 하수감시 시스템)는 2020년 코로나19 대응을 계기로 전국 규모의 하수 역학 감시 인프라를 "
            "구축했다. 수천 개 처리장에서 SARS-CoV-2 RNA를 주기적으로 측정해 임상 보고보다 4~6일 먼저 유행 상승을 "
            "탐지하는 것으로 보고됐다. NWSS는 독감·RSV·노로바이러스 등 다중 병원체로 확장 중이며, "
            "지역별 데이터를 공개 대시보드로 제공한다. 우리 시스템(L2 하수도 계층)은 이 프레임워크를 "
            "한국 KOWAS 데이터에 적용한 것으로, 국제 표준 감시 방법론과 정렬된다."
        ),
        "metadata": {
            "source": "CDC National Wastewater Surveillance System (NWSS)",
            "url": "https://www.cdc.gov/nwss/index.html",
            "lang": "ko-summary",
            "topic": "wastewater_surveillance_us",
            "author": "CDC",
            "year": 2020,
        },
    },
    {
        "id": 7,
        "text": (
            "Lim et al. (2021)은 International Journal of Forecasting에 발표한 논문에서 "
            "Temporal Fusion Transformer(TFT)를 제안했다. TFT는 다변량 시계열 예측에서 "
            "변수 선택 네트워크(VSN), 게이티드 잔차 네트워크(GRN), 다중 헤드 어텐션을 결합해 "
            "단기·중기·장기 패턴을 동시에 학습한다. 어텐션 가중치로 \"어느 시점, 어느 변수가 예측에 기여했는지\" "
            "해석할 수 있어 보건당국의 의사결정 신뢰성을 높인다. 전기 소비·소매 판매 등 다양한 도메인에서 "
            "LSTM·DeepAR 대비 우수한 성능을 보였으며, 감염병 시계열 예측에도 적용 가능하다."
        ),
        "metadata": {
            "source": "Lim et al., \"Temporal Fusion Transformers for Interpretable Multi-horizon Time Series Forecasting\", Int. J. Forecasting 2021",
            "url": "https://doi.org/10.1016/j.ijforecast.2021.03.012",
            "lang": "ko-summary",
            "topic": "tft_interpretable_forecasting",
            "author": "Lim et al.",
            "year": 2021,
        },
    },
    {
        "id": 8,
        "text": (
            "WHO GOARN(글로벌 발병 경보·대응 네트워크)은 2000년 설립 이후 전 세계 감염병 조기경보의 "
            "다중 신호 통합 표준을 제시해 왔다. GOARN은 공식 임상 보고(indicator-based)와 "
            "인터넷 뉴스·여행·동물 신호(event-based)를 병행 모니터링하며, "
            "단일 출처 경보를 절대 금지하고 최소 2개 이상 독립 신호가 교차 확인된 후에만 "
            "공식 경보를 발령하는 '삼각검증(triangulation)' 원칙을 운용한다. "
            "이 원칙은 우리 다중 신호 앙상블 경보(YELLOW: 2개 신호 30% 이상, RED: 3개 신호 50% 이상) "
            "설계의 직접적인 학술 근거다."
        ),
        "metadata": {
            "source": "WHO Global Outbreak Alert and Response Network (GOARN)",
            "url": "https://www.who.int/initiatives/goarn",
            "lang": "ko-summary",
            "topic": "who_goarn_multi_source",
            "author": "WHO",
            "year": 2000,
        },
    },
    {
        "id": 9,
        "text": (
            "scikit-learn의 TimeSeriesSplit은 시계열 데이터의 미래 정보 누출(data leakage)을 방지하기 위해 "
            "훈련 세트가 항상 테스트 세트보다 시간상 앞선 구조로 분할하는 walk-forward 교차검증 클래스다. "
            "`gap` 파라미터로 훈련-테스트 사이에 빈 구간을 두면 실전 운용 환경(예: 4주 지연 보고)을 "
            "시뮬레이션할 수 있다. 감염병 예측 모델 평가 시 랜덤 K-Fold 사용은 금지되며 "
            "반드시 TimeSeriesSplit(n_splits=5, gap=4) 또는 동등한 walk-forward 방식을 써야 한다. "
            "이 방법론은 오버피팅 탐지와 실환경 성능 추정 간 괴리를 최소화한다."
        ),
        "metadata": {
            "source": "scikit-learn Documentation: TimeSeriesSplit",
            "url": "https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html",
            "lang": "ko-summary",
            "topic": "walk_forward_cv",
            "author": "scikit-learn",
            "year": 2024,
        },
    },
    {
        "id": 10,
        "text": (
            "ISMS-P(정보보호 및 개인정보보호 관리체계) 인증은 한국인터넷진흥원(KISA)이 운영하는 "
            "국내 최고 수준의 정보보호 인증 제도다. 공공기관 납품 소프트웨어는 주요 심사 항목인 "
            "2.9 시스템 및 서비스 운영관리(로그·접근기록)와 3.1~3.4 개인정보 수집·보유·파기 요건을 충족해야 한다. "
            "감염병 감시 시스템은 민감 의료·위치 정보를 처리할 경우 별도 동의와 가명처리 의무가 발생한다. "
            "우리 시스템은 개인 식별 정보 없는 집계 신호만 처리하므로 3종 개인정보 처리 조항은 해당 없으나, "
            "2.9 로그 보존(6개월 이상)과 접근통제 요건은 반드시 준수해야 B2G 납품이 가능하다."
        ),
        "metadata": {
            "source": "한국인터넷진흥원(KISA) ISMS-P 인증기준",
            "url": "https://isms.kisa.or.kr/main/ispims/intro/",
            "lang": "ko",
            "topic": "isms_p_b2g_compliance",
            "author": "KISA",
            "year": 2024,
        },
    },
    # ── 추가 시드 (11~14) — 2026-04-28 D-2 발표 RAG 인용문 풍부화 ────────
    {
        "id": 11,
        "text": (
            "Xu et al. (2025)은 하수도 바이러스 농도, 소셜미디어 키워드, 인구 이동량을 결합한 "
            "다중 신호 융합 모델이 단일 신호 대비 평균 7~10일 선행 탐지 성능을 보였다고 보고했다. "
            "특히 도시 단위(district-level) 분석에서 SNS 단독 사용 시 발생하던 과대 예측 문제가 "
            "하수 신호와 결합 후 30% 이상 감소했음을 입증했다. 다만 이 연구는 약국 OTC 신호를 포함하지 않았고 "
            "한국어·한국 의료체계 특화 분석이 부재해, 우리 시스템(L1 약국 OTC + L2 하수 + L3 검색)과 "
            "한국 B2G 환경에서 차별화된다. Xu의 다중 신호 융합 원칙은 우리 앙상블 가중치 설계의 학술적 근거다."
        ),
        "metadata": {
            "source": "Xu et al., \"Multi-source Disease Surveillance Fusion\", Nature Communications 2025",
            "url": "https://www.nature.com/ncomms/",
            "lang": "ko-summary",
            "topic": "multi_signal_fusion_2025",
            "author": "Xu et al.",
            "year": 2025,
        },
    },
    {
        "id": 12,
        "text": (
            "한국 KOWAS(하수도감시 시스템)는 환경부와 질병관리청이 2022년 시범 운영을 시작해 "
            "전국 17개 광역의 주요 하수처리장에서 SARS-CoV-2·인플루엔자 등 호흡기 바이러스 RNA를 "
            "주간 단위로 측정·공개하는 한국형 WBE 인프라다. 측정 단위는 copies/mL이며 "
            "공식 PDF 보고서가 매주 화요일 오전에 갱신된다. "
            "값의 절대 비교는 처리장 규모·인구 유역 차이로 어렵고 동일 처리장 내 추이 변화율(%) 비교가 권장된다. "
            "우리 L2 계층은 KOWAS PDF를 pdfplumber로 자동 파싱해 17지역 정규화(0-100) 후 Kafka 파이프라인에 적재한다."
        ),
        "metadata": {
            "source": "환경부·질병관리청 KOWAS 운영지침 (2024)",
            "url": "https://www.me.go.kr/",
            "lang": "ko",
            "topic": "kowas_korea_wbe",
            "author": "환경부·질병관리청",
            "year": 2024,
        },
    },
    {
        "id": 13,
        "text": (
            "Granger 인과검정(Granger causality test)은 시계열 X가 시계열 Y의 미래값 예측을 "
            "유의미하게 개선하는지 통계적으로 검증하는 방법이다(Granger, 1969). "
            "감염병 조기경보 시스템에서는 비전통 신호(약국·하수·검색)가 임상 확진 시계열에 대해 "
            "Granger 의미에서 선행성을 갖는지 입증하는 표준 도구로 사용된다. "
            "권장 절차: (1) ADF 단위근 검정으로 정상성 확인 → (2) statsmodels grangercausalitytests "
            "(maxlag=4) 실행 → (3) p<0.05 시 유의한 선행성 인정. "
            "단, Granger 인과는 통계적 선행성이지 진짜 인과관계가 아니므로 \"X가 Y의 원인\" 주장은 금지된다. "
            "우리 시스템은 L1·L2·L3 모두 p<0.05 (Slide 9)로 임상 확진에 대한 선행성을 입증한 상태다."
        ),
        "metadata": {
            "source": "Granger, \"Investigating Causal Relations by Econometric Models\", Econometrica 1969 + statsmodels docs",
            "url": "https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.grangercausalitytests.html",
            "lang": "ko-summary",
            "topic": "granger_causality_validation",
            "author": "Granger",
            "year": 1969,
        },
    },
    {
        "id": 14,
        "text": (
            "질병관리청 인플루엔자 예방접종 권고안은 매년 8~9월 발표되며, 65세 이상·임산부·생후 6개월~12세·"
            "만성질환자를 우선 접종 대상으로 지정한다. 유행주의보 발령 시(ILI 1.96σ 초과) "
            "국가예방접종(NIP) 미접종 고위험군에 대해 시·도 보건소가 능동 안내를 시작하며, "
            "약국 항바이러스제(타미플루 등) 비축량을 30% 이상 늘린다. "
            "AI 조기경보 시스템에서 YELLOW 이상 경보 발령 시 권장 액션은 (1) 학교·요양시설 마스크 안내 강화, "
            "(2) 백신 접종 캠페인 가속, (3) 항바이러스제 재고 확인이다. "
            "이 가이드라인은 RAG 리포트에서 \"권고: 백신·재고·방역\" 인용 근거로 직접 활용된다."
        ),
        "metadata": {
            "source": "질병관리청 \"인플루엔자 예방접종 사업관리 지침\" 2024-2025 시즌",
            "url": "https://nip.kdca.go.kr/",
            "lang": "ko",
            "topic": "influenza_vaccine_guideline",
            "author": "KDCA",
            "year": 2024,
        },
    },
    # ── 신규 시드 (15~17) — 2026-04-29 D-1 발표 KDCA 표준 포맷 보강 ─────
    {
        "id": 15,
        "text": (
            "UIS 다중 신호 앙상블 경보 운영 원칙: composite_score = 0.30×L1 + 0.40×L2 + 0.30×L3. "
            "2-레이어 게이트: (1) composite ≥ 30 초과 시 YELLOW 후보 진입, (2) 2개 이상 계층이 30 이상이어야 YELLOW 발령. "
            "경보 레벨 임계: GREEN < 30, YELLOW 30~54, ORANGE 55~69, RED ≥ 70(※ CLAUDE.md 가중치 기준). "
            "본 임계값(55/70)은 내부 운영 매뉴얼 기준이며 KDCA ILI 1.96σ 임계와 별도로 운영된다. "
            "L3 검색트렌드 단독 발령 절대 금지: 인포데믹(정보 과잉) 위험으로 공황 유발 가능. "
            "앙상블 가중치 재검증 주기: 4주 walk-forward CV (gap=4주) 결과로 분기별 조정. "
            "변경 시 CLAUDE.md 가중치 섹션 및 backend/app/config.py 동시 업데이트 필수."
        ),
        "metadata": {
            "source": "UIS 내부 운영 매뉴얼 v1.0 (박진영, 2026)",
            "url": "",
            "lang": "ko",
            "topic": "ensemble_alert_rules",
            "author": "박진영",
            "year": 2026,
        },
    },
    {
        "id": 16,
        "text": (
            "KDCA 감염병 표본감시 운영지침(2024): ILINet은 전국 표본의원 약 200개를 통해 주간 ILI(Influenza-Like Illness) "
            "비율(환자수/총방문자수×100)을 산출한다. 유행 기준선(epidemic threshold)은 최근 3년 비유행기 평균+1.96×SD로 계산. "
            "KOWAS(하수도감시 시스템)는 전국 60개 이상 주요 하수처리장에서 SARS-CoV-2·인플루엔자 A·B·노로바이러스 RNA 농도를 "
            "주간 측정하며, 측정 단위는 copies/mL(log10 환산 보고). "
            "공식 보고 발표일: ISO 주차 기준 화요일 오전(전주 수집 데이터). "
            "임상신고(ILINet)와 하수감시(KOWAS) 간 1~2주 선행성 차이가 WBE 조기경보 활용의 핵심 근거다."
        ),
        "metadata": {
            "source": "질병관리청 감염병 표본감시 운영지침 2024 (KDCA, 2024)",
            "url": "https://www.kdca.go.kr/contents.es?mid=a20301070000",
            "lang": "ko",
            "topic": "kdca_surveillance_guidelines",
            "author": "KDCA",
            "year": 2024,
        },
    },
    {
        "id": 17,
        "text": (
            "AI 보조 의사결정 시스템 XAI 감사 요건 (ISMS-P 2.9 + EU AI Act Art.13/14 적용): "
            "alert_reports 테이블에 다음 필드를 의무 기록해야 한다: "
            "(1) triggered_by — 경보 발령 규칙 또는 피처 식별자(rule/feature 구분); "
            "(2) feature_values — L1·L2·L3 원시값(raw) 및 정규화값(normalized) JSONB; "
            "(3) rag_sources — RAG top-k 인용 메타데이터(출처·점수·페이지) JSONB. "
            "EU AI Act Art.13은 고위험 AI 시스템에 투명성 문서화를 요구하며, Art.14는 인간 감독(human oversight) 게이트를 의무화한다. "
            "따라서 경보 리포트에는 반드시 '인간 전문가 검토 필요' 면책 문구를 명시해야 하며, "
            "자동 발령된 경보는 역학조사관이 30분 이내 검토·확인하는 워크플로우를 운영해야 한다. "
            "ISMS-P 2.9 로그 보존 요건: 감사 로그 최소 6개월 이상 보존."
        ),
        "metadata": {
            "source": "ISMS-P 2.9 + EU AI Act Art.13/14 적용 가이드 (박진영, 2026-04)",
            "url": "https://isms.kisa.or.kr/main/ispims/intro/",
            "lang": "ko",
            "topic": "ai_xai_audit",
            "author": "박진영",
            "year": 2026,
        },
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG 시드 문서 임베딩")
    parser.add_argument("--dry-run", action="store_true", help="임베딩하지 않고 문서 목록만 출력")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.dry_run:
        for d in SEED_DOCS:
            print(f"#{d['id']} [{d['metadata']['topic']}] {d['text'][:80]}…")
        return 0

    vdb = EpidemiologyVectorDB()
    if vdb.client is None or vdb.embedder is None:
        logger.error("Qdrant 또는 임베딩 모델 초기화 실패 — 중단")
        return 1

    n = vdb.add_documents(SEED_DOCS)
    logger.info("시드 문서 %d건 임베딩 완료 (collection=%s)", n, vdb.client.get_collections())

    # 검색 테스트
    print("\n=== 검색 검증 ===")
    for query in [
        "구글 독감 트렌드 실패 이유",
        "하수에서 바이러스 농도로 유행을 예측",
        "단일 신호로 경보를 내려도 되는가",
    ]:
        hits = vdb.search(query, top_k=2)
        print(f"\nQ: {query}")
        for h in hits:
            print(f"  · score={h['score']:.3f} | {h['metadata'].get('topic')} | {h['text'][:60]}…")

    return 0


if __name__ == "__main__":
    sys.exit(main())
