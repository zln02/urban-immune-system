"""Layer 2: KOWAS 하수 바이오마커 수집기.

환경부 KOWAS(Korea Wastewater Surveillance) PDF에서
인플루엔자 바이러스 농도 데이터를 OCR/파싱해 수집한다.
선행 시간: 임상 확진 대비 약 2~3주 (가장 빠른 선행 신호).

현재: 수동 PDF 추출 → 자동화 목표 (OCR/크롤링 Phase 3~4)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

from collectors.kafka_producer import TOPIC_L2, send_signal
from collectors.utils import normalize_minmax

logger = logging.getLogger(__name__)

# KOWAS PDF 데이터 디렉토리 (로컬 수동 다운로드 경로)
KOWAS_DATA_DIR = Path(__file__).parent.parent / "data" / "kowas"


def _parse_kowas_pdf(pdf_path: Path) -> list[dict]:
    """KOWAS PDF에서 주차별 바이러스 농도를 파싱한다."""
    records = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                # TODO: 실제 KOWAS PDF 테이블 구조에 맞게 파싱 로직 구현
                # 현재는 샘플 패턴 (week, concentration)
                for match in re.finditer(r"(\d{4})[년\-](\d{1,2})주.*?([\d.]+)\s*copies", text):
                    year, week, conc = match.groups()
                    records.append({
                        "year": int(year),
                        "week": int(week),
                        "concentration": float(conc),
                    })
    except Exception as exc:
        logger.error("KOWAS PDF 파싱 실패 (%s): %s", pdf_path.name, exc)
    return records


def collect_wastewater_from_pdfs(region: str = "서울특별시") -> int:
    """KOWAS_DATA_DIR 내 모든 PDF를 파싱해 Kafka로 전송한다. 전송 건수 반환."""
    if not KOWAS_DATA_DIR.exists():
        logger.warning("KOWAS 데이터 디렉토리가 없습니다: %s", KOWAS_DATA_DIR)
        return 0

    all_records: list[dict] = []
    for pdf_file in sorted(KOWAS_DATA_DIR.glob("*.pdf")):
        all_records.extend(_parse_kowas_pdf(pdf_file))

    if not all_records:
        logger.warning("파싱된 KOWAS 데이터가 없습니다")
        return 0

    raw_vals = [r["concentration"] for r in all_records]
    normalized = normalize_minmax(raw_vals)

    for record, norm_val in zip(all_records, normalized):
        send_signal(
            TOPIC_L2, region, "L2", norm_val,
            raw_value=record["concentration"],
            source="kowas_pdf",
        )

    logger.info("Layer 2 (하수) %d건 전송 완료", len(all_records))
    return len(all_records)
