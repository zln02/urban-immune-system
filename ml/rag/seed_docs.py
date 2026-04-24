"""중간발표용 RAG 시드 문서 — 역학 가이드라인 5건 임베딩.

각 문서는 공개 가이드라인의 핵심 메시지를 한국어로 정리한 것이며,
metadata.source / metadata.url에 원 출처를 명시한다.

추후 확장 시 이 모듈에 dict를 추가하고 다시 실행하면 upsert로 갱신된다.
"""
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
