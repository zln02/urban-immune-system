"""KDCA 전수신고 감염병 발생현황 라벨 수집기 (publicDataPk=15139178).

End Point: https://apis.data.go.kr/1790387/EIDAPIService
키: DATA_GO_KR_API_KEY (.env)
승인: 자동승인, 일일 1,000건, 활용기간 2026-06-04 ~ 2028-06-04

수집 대상 (xlsx 8개 오퍼레이션 중 우리 라벨에 쓸 것):
    1) 기간별 감염병 발생 현황      — 주별/월별/연도별 전국 합계
    2) 지역별 감염병 발생 현황      — 17 시·도 연간

요청 파라미터 (xlsx 사양):
    serviceKey       : API 키
    resType          : 1=xml, 2=json
    searchPeriodType : 1=연도, 2=월, 3=주          [기간별 전용]
    searchStartYear  : 시작 연도 (예: 2024)
    searchEndYear    : 종료 연도
    searchYear       : 단일 연도                    [지역별 전용]
    searchSidoCd     : 00=전체, 01=서울 ... 17=세종 [지역별 전용]
    pageNo, numOfRows: 페이지네이션

응답 필드:
    {period, icdGroupNm, icdNm, resultVal}                — 기간별
    {year, sidoCd, sidoNm, icdGroupNm, icdNm, resultVal}  — 지역별

CLI:
    python -m pipeline.collectors.kdca_label_collector --mode period --period-type 3 --year 2024
    python -m pipeline.collectors.kdca_label_collector --mode sido   --year 2024 --sido 01
"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─────────────────────── 상수 ─────────────────────────────────────────────
BASE_URL = "https://apis.data.go.kr/1790387/EIDAPIService"

# 오퍼레이션 path — data.go.kr Swagger UI (2026-06-05 확정) PascalCase, no get prefix.
# 200 OK 라이브 검증 완료 (resType=2 JSON).
# 주의: /death 만 소문자 (Swagger UI 사양 그대로).
# 한계: 본 API 는 1·2·3급 전수신고 67종만 — 4급 표본감시(계절성 인플루엔자/COVID/노로) 미포함.
#       메인 모델 라벨로는 부적합 → 확장 데모용(백일해·홍역·콜레라 등) 으로만 사용.
#       4급 표본감시는 별도 KDCA 표본감시 collector 사용.
OPERATIONS: dict[str, str] = {
    "period":        "/PeriodBasic",    # 기간별 감염병 발생 현황
    "period_ptnt":   "/PeriodPtnt",     # 기간별 환자분류별
    "period_region": "/PeriodRegion",   # 기간별 감염지역별(국내/국외)
    "sido":          "/Region",         # 지역별 (시·도별)
    "age":           "/Age",            # 연령별
    "sex":           "/Gender",         # 성별
    "disease":       "/Disease",        # 감염병별
    "death":         "/death",          # 감염병별 사망 (소문자 — 사양 그대로)
}

# 시도 코드 (xlsx sheet5 표시)
SIDO_CODES: dict[str, str] = {
    "00": "전국",
    "01": "서울특별시",
    "02": "부산광역시",
    "03": "대구광역시",
    "04": "인천광역시",
    "05": "광주광역시",
    "06": "대전광역시",
    "07": "울산광역시",
    "08": "경기도",
    "09": "강원특별자치도",
    "10": "충청북도",
    "11": "충청남도",
    "12": "전라북도",
    "13": "전라남도",
    "14": "경상북도",
    "15": "경상남도",
    "16": "제주특별자치도",
    "17": "세종특별자치시",
}

# KDCA icdNm → 우리 모델 disease 코드 매핑.
# [확인 사항 2026-06-05] EIDAPIService 는 1·2·3급 67종만 — 메인 타겟(계절성 인플루엔자/COVID/노로)
# 은 4급 표본감시라 여기 없음. 아래는 "확장 데모" 용 1·2·3급 라벨.
DISEASE_NAME_MAP: dict[str, list[str]] = {
    # 1급 (pandemic 한정, 평시 0건)
    "novel_influenza": ["신종인플루엔자"],
    "zoonotic_influenza": ["동물인플루엔자 인체감염증"],
    # 2급 (확장 데모 후보 — 발생 데이터 있음)
    "hib": ["b형헤모필루스인플루엔자"],
    "pertussis": ["백일해"],
    "measles": ["홍역"],
    "mumps": ["유행성이하선염"],
    "rubella": ["풍진"],
    "varicella": ["수두"],
    "scarlet_fever": ["성홍열"],
    "hepatitis_a": ["A형간염"],
    # 3급 (확장 데모 후보)
    "scrub_typhus": ["쯔쯔가무시증"],
    "hfrs": ["신증후군출혈열"],
}


# ─────────────────────── 호출 ──────────────────────────────────────────────
def _api_key() -> str | None:
    """DATA_GO_KR_API_KEY 환경변수 — Pydantic Settings 경유 없이 os.getenv 사용.

    이유: 이 collector 는 standalone CLI 로도 동작해야 하므로 Settings 의존성을 피한다.
    backend 컨텍스트에서 호출 시는 settings.data_go_kr_api_key 가 동일 값을 보장한다.
    """
    key = os.getenv("DATA_GO_KR_API_KEY", "").strip()
    if not key or key == "your_data_go_kr_key":
        logger.warning("DATA_GO_KR_API_KEY 미설정 — 호출 불가")
        return None
    return key


def fetch_by_period(
    search_period_type: int = 3,
    start_year: int = 2024,
    end_year: int | None = None,
    page_no: int = 1,
    num_of_rows: int = 1000,
) -> list[dict[str, Any]]:
    """기간별 감염병 발생 현황 호출.

    Args:
        search_period_type: 1=연도, 2=월, 3=주
        start_year: 시작 연도
        end_year: 종료 연도 (기본: start_year)
        page_no, num_of_rows: 페이지네이션
    Returns:
        item 리스트. 호출 실패 시 빈 리스트.
    """
    op = OPERATIONS.get("period", "")
    if not op:
        logger.error("OPERATIONS['period'] 미설정 — data.go.kr 활용신청 상세기능정보 확인 필요")
        return []
    key = _api_key()
    if not key:
        return []

    end_year = end_year if end_year is not None else start_year
    url = f"{BASE_URL}{op}"
    params: dict[str, str | int] = {
        "serviceKey": key,
        "resType": 2,  # JSON (1=xml, 2=json — 사양상 숫자 필수, 문자열은 104 에러)
        "searchPeriodType": search_period_type,
        "searchStartYear": start_year,
        "searchEndYear": end_year,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
    }

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
        data = resp.json()
        # 실 응답 구조: {"response": {"header": {...}, "body": {"items": {"item": [...]}}}}
        body = data.get("response", data).get("body", {})
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        logger.info(
            "기간별 호출 성공: %d건 (period_type=%d, %d~%d)",
            len(items), search_period_type, start_year, end_year,
        )
        return items
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP %s: %s — %s", exc.response.status_code, url, exc.response.text[:200])
        return []
    except (httpx.RequestError, ValueError) as exc:
        logger.error("호출 실패: %s", exc)
        return []


def fetch_by_period_all(
    search_period_type: int = 3,
    start_year: int = 2024,
    end_year: int | None = None,
    num_of_rows: int = 1000,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """기간별 전 페이지 누적 수집 (totalCount 모를 때 빈 페이지 만나면 종료).

    안전 가드: max_pages 로 무한루프 차단 (1·2·3급 67종 × 53주 ≈ 3551건 → 1000건/page × 4 페이지).
    """
    aggregated: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        items = fetch_by_period(
            search_period_type=search_period_type,
            start_year=start_year,
            end_year=end_year,
            page_no=page,
            num_of_rows=num_of_rows,
        )
        if not items:
            break
        aggregated.extend(items)
        if len(items) < num_of_rows:
            break  # 마지막 페이지
    logger.info("기간별 전체 수집 누적: %d건 (%d페이지)", len(aggregated), page)
    return aggregated


def fetch_by_sido(
    search_year: int = 2024,
    sido_cd: str = "00",
    search_type: int = 1,
    page_no: int = 1,
    num_of_rows: int = 1000,
) -> list[dict[str, Any]]:
    """지역별 감염병 발생 현황 호출.

    Args:
        search_year: 연도
        sido_cd: 00=전체, 01=서울 ... 17=세종
        search_type: 1=발생수, 2=인구10만명당 발생률
    """
    op = OPERATIONS.get("sido", "")
    if not op:
        logger.error("OPERATIONS['sido'] 미설정 — data.go.kr 활용신청 상세기능정보 확인 필요")
        return []
    key = _api_key()
    if not key:
        return []

    url = f"{BASE_URL}{op}"
    params: dict[str, str | int] = {
        "serviceKey": key,
        "resType": 2,
        "searchType": search_type,
        "searchYear": search_year,
        "searchSidoCd": sido_cd,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
    }
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
        data = resp.json()
        body = data.get("response", data).get("body", {})
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        logger.info("지역별 호출 성공: %d건 (year=%d, sido=%s)", len(items), search_year, sido_cd)
        return items
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP %s: %s — %s", exc.response.status_code, url, exc.response.text[:200])
        return []
    except (httpx.RequestError, ValueError) as exc:
        logger.error("호출 실패: %s", exc)
        return []


# ─────────────────────── 정규화 ────────────────────────────────────────────
def to_disease_code(icd_nm: str) -> str | None:
    """KDCA icdNm 한글명 → 우리 모델 disease 코드 매핑.

    매칭 안 되는 질병은 None 반환 (skip).
    """
    for code, candidates in DISEASE_NAME_MAP.items():
        if any(c in icd_nm for c in candidates):
            return code
    return None


def normalize_period_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """기간별 응답 1건 → 정규화된 dict.

    응답 필드:
        period      : "2024" (연도) / "2024-01" (월) / "2024-W12" (주)
        icdGroupNm  : 감염병급
        icdNm       : 감염병명
        resultVal   : 발생수
    """
    disease = to_disease_code(item.get("icdNm", ""))
    if not disease:
        return None
    try:
        case_count = int(float(item.get("resultVal", 0)))
    except (ValueError, TypeError):
        return None
    return {
        "period": str(item.get("period", "")),
        "icd_group": item.get("icdGroupNm", ""),
        "icd_name": item.get("icdNm", ""),
        "disease": disease,
        "case_count": case_count,
        "source": "KDCA_EID_API",
    }


def normalize_sido_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """지역별 응답 1건 → 정규화."""
    disease = to_disease_code(item.get("icdNm", ""))
    if not disease:
        return None
    sido_cd = str(item.get("sidoCd", ""))
    region = SIDO_CODES.get(sido_cd, item.get("sidoNm", ""))
    if region in ("", "전국"):
        return None  # 전국은 시·도 분리 라벨로 부적합
    try:
        case_count = int(float(item.get("resultVal", 0)))
    except (ValueError, TypeError):
        return None
    return {
        "year": int(str(item.get("year", "0"))[:4]),
        "region": region,
        "sido_cd": sido_cd,
        "icd_name": item.get("icdNm", ""),
        "disease": disease,
        "case_count": case_count,
        "source": "KDCA_EID_API",
    }


# ─────────────────────── CLI ───────────────────────────────────────────────
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="KDCA 전수신고 감염병 발생현황 (15139178) 수집")
    p.add_argument("--mode", choices=["period", "sido"], default="period")
    p.add_argument("--period-type", type=int, default=3, choices=[1, 2, 3], help="1=연도 2=월 3=주")
    p.add_argument("--year", type=int, default=datetime.now(timezone.utc).year)
    p.add_argument("--end-year", type=int, default=None)
    p.add_argument("--sido", default="00")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.mode == "period":
        raw = fetch_by_period(
            search_period_type=args.period_type,
            start_year=args.year,
            end_year=args.end_year,
        )
        records = [r for r in (normalize_period_item(it) for it in raw) if r is not None]
    else:
        raw = fetch_by_sido(search_year=args.year, sido_cd=args.sido)
        records = [r for r in (normalize_sido_item(it) for it in raw) if r is not None]

    logger.info("정규화 후 %d건 (mode=%s)", len(records), args.mode)
    for r in records[:5]:
        logger.info("  sample: %s", r)
    if args.dry_run:
        logger.info("[dry-run] DB 저장 건너뜀")


if __name__ == "__main__":
    main()
