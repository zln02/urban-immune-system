"""HIRA 의약품사용정보조회서비스 수집기 (publicDataPk=15047819).

End Point: https://apis.data.go.kr/B551182/msupUserInfoService1.2
키: DATA_GO_KR_API_KEY (.env, KDCA EIDAPIService 와 동일 통합키)
활용기간: 2026-06-08 ~ 2028-06-08, 자동승인, 일일 트래픽 10,000건/operation
응답: XML default (JSON 응답 시도 — 다른 data.go.kr HIRA API 패턴)

목적:
    L1 OTC (네이버 쇼핑인사이트, 전국 단일값) 보완용 신규 layer "L1'" — 지역별 임상 신호.
    HIRA = 건강보험 청구자료라 OTC 가 아닌 처방조제 약품. 인플루엔자 치료제(타미플루 등)의
    시도×월 처방량 시계열을 L1' 로 활용.

12 operations 중 L1' 핵심:
    getAtcStp4AreaList1.2  — 4단계 ATC × 지역 (J05AH02 타미플루 → 시도 처방량)  ★ 메인
    getAtcStp3AreaList1.2  — 3단계 ATC × 지역 (J05AH 항인플루엔자 클래스 합)
    getCmpnAreaList1.2     — 성분 × 지역      (대체 시그널)
    getMeftDivAreaList1.2  — 약효분류군 × 지역 (한국 분류, ATC 와 다름)

요청 파라미터 (4단계 ATC × 지역 기준 — 활용신청 페이지 기준):
    serviceKey  : API 키 (Decoding 인증키)
    mdcareYm    : 진료년월 YYYYMM (예: 202112)
    insurTpCd   : 보험자구분 (0=전체, 5=건강보험, 7=의료급여 등 — 확인 필요)
    clDivCd     : 조제처방구분 (0=전체, 1=처방조제, 2=직접조제 — 확인 필요)
    sidoCd      : 시도코드 (HIRA 자체)
    sgguCd      : 시군구코드 (옵셔널)
    atcCd       : ATC 4단계 코드 (예: J05AH02)
    pageNo, numOfRows
    _type=json  : JSON 응답 시도 (XML default)

ATC 4단계 (인플루엔자 치료제):
    J05AH02 — 오셀타미비르 (타미플루)         ★ 가장 많이 처방
    J05AH01 — 자나미비르 (리렌자, 흡입형)
    J05AH04 — 페라미비르 (페라미플루, IV)

ATC 3단계 (인플루엔자 클래스):
    J05AH   — 항인플루엔자제 (3단계 모두 합산, 클래스 시그널)

CLI:
    # 단일 query (서울 2022-01 타미플루)
    python -m pipeline.collectors.hira_collector --atc J05AH02 --sido 110000 --ym 202201

    # 17 시도 × 24개월 backfill (2020-2022 인플루엔자 시즌 전체)
    python -m pipeline.collectors.hira_collector --atc-class J05AH --backfill 2020-01:2022-12
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────── 상수 ─────────────────────────────────────────────
BASE_URL = "https://apis.data.go.kr/B551182/msupUserInfoService1.2"

# 12 operations — 활용신청 페이지 (2026-06-08 확정) 기준 정확한 path
OPERATIONS: dict[str, str] = {
    # ATC 4단계 (구체적 약물 코드, 예: J05AH02 = 타미플루)
    "atc4_area":   "/getAtcStp4AreaList1.2",    # ★ L1' 메인 (지역별)
    "atc4_cl":     "/getAtcStp4ClList1.2",      # 의료기관종별
    "atc4_sick":   "/getAtcStp4SickList1.2",    # 상병별
    # ATC 3단계 (클래스, 예: J05AH = 항인플루엔자제)
    "atc3_area":   "/getAtcStp3AreaList1.2",
    "atc3_cl":     "/getAtcStp3ClList1.2",
    "atc3_sick":   "/getAtcStp3SickList1.2",
    # 성분 코드
    "cmpn_area":   "/getCmpnAreaList1.2",
    "cmpn_cl":     "/getCmpnClList1.2",
    "cmpn_sick":   "/getCmpnSickList1.2",
    # 약효분류군 (한국 분류, ATC 와 다른 체계)
    "meft_area":   "/getMeftDivAreaList1.2",
    "meft_cl":     "/getMeftDivClList1.2",
    "meft_sick":   "/getMeftDivSickList1.2",
}

# 인플루엔자 치료제 ATC 4단계 코드 (4급 표본감시 = ILI 와 직접 대응)
ATC4_INFLUENZA: dict[str, str] = {
    "J05AH02": "오셀타미비르 (타미플루)",
    "J05AH01": "자나미비르 (리렌자)",
    "J05AH04": "페라미비르 (페라미플루)",
}

# ATC 3단계 — 클래스 합계
ATC3_INFLUENZA = "J05AH"  # 항인플루엔자제

# HIRA 시도코드 (병원정보서비스 코드체계 — 6자리, 첫 2자리=시도, 나머지=시군구 또는 00)
# [TBD] 첫 호출 응답으로 검증 — 잘못된 코드 시 응답 0 행
SIDO_CODES_HIRA: dict[str, str] = {
    "110000": "서울특별시",
    "210000": "부산광역시",
    "220000": "대구광역시",
    "230000": "인천광역시",
    "240000": "광주광역시",
    "250000": "대전광역시",
    "260000": "울산광역시",
    "270000": "세종특별자치시",
    "310000": "경기도",
    "320000": "강원특별자치도",
    "330000": "충청북도",
    "340000": "충청남도",
    "350000": "전라북도",
    "360000": "전라남도",
    "370000": "경상북도",
    "380000": "경상남도",
    "390000": "제주특별자치도",
}

TIMEOUT_SEC = 30


@dataclass(frozen=True)
class HiraDrugUsage:
    """단일 (시도, ATC, 진료년월) 처방 사용량."""

    sido_cd: str
    sido_nm: str
    atc_cd: str
    atc_nm: str
    mdcare_ym: str
    quantity: int       # 수량 (조제건수 또는 일수)
    amount: int         # 금액 (원)


class HiraCollectorError(RuntimeError):
    """HIRA API 호출 실패."""


def _service_key() -> str:
    key = os.getenv("DATA_GO_KR_API_KEY", "")
    if not key:
        raise HiraCollectorError("DATA_GO_KR_API_KEY 미설정 (.env)")
    return key


async def fetch_raw(
    operation: str,
    *,
    mdcare_ym: str,
    atc_cd: str | None = None,
    sido_cd: str | None = None,
    sggu_cd: str | None = None,
    insur_tp_cd: str = "0",
    cl_div_cd: str = "0",
    page_no: int = 1,
    num_of_rows: int = 100,
) -> dict[str, Any]:
    """단일 operation 호출 — raw JSON dict 반환 (envelope 그대로).

    응답 envelope (data.go.kr 표준):
        {response: {header: {resultCode, resultMsg}, body: {items, numOfRows, pageNo, totalCount}}}
    items 가 list 면 그대로, dict (단건) 이면 [it] 로 래핑 필요.
    """
    if operation not in OPERATIONS:
        raise HiraCollectorError(f"unknown operation: {operation}")
    url = f"{BASE_URL}{OPERATIONS[operation]}"
    params: dict[str, str | int] = {
        "serviceKey": _service_key(),
        "mdcareYm": mdcare_ym,
        "insurTpCd": insur_tp_cd,
        "clDivCd": cl_div_cd,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "_type": "json",
    }
    if atc_cd:
        params["atcCd"] = atc_cd
    if sido_cd:
        params["sidoCd"] = sido_cd
    if sggu_cd:
        params["sgguCd"] = sggu_cd

    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        r = await client.get(url, params=params)
        # 4xx/5xx 도 JSON envelope 일 수 있음 — raise 전 본문 확인
        try:
            return r.json()
        except json.JSONDecodeError:
            raise HiraCollectorError(
                f"{operation} non-JSON response (status={r.status_code}): {r.text[:200]}"
            )


def _items_from_envelope(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    """data.go.kr 표준 envelope → items list."""
    body = envelope.get("response", envelope).get("body", {})
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    return items if isinstance(items, list) else []


async def fetch_atc4_area(
    atc_cd: str,
    sido_cd: str,
    mdcare_ym: str,
) -> list[HiraDrugUsage]:
    """4단계 ATC × 시도 × 월 → HiraDrugUsage list (단일 호출, 페이지네이션 X)."""
    env = await fetch_raw(
        "atc4_area",
        atc_cd=atc_cd,
        sido_cd=sido_cd,
        mdcare_ym=mdcare_ym,
        num_of_rows=500,
    )
    items = _items_from_envelope(env)
    out: list[HiraDrugUsage] = []
    for it in items:
        # [TBD] 응답 필드명은 첫 호출 후 확인. 흔한 패턴 추측 — 후 보정.
        out.append(
            HiraDrugUsage(
                sido_cd=str(it.get("sidoCd") or sido_cd),
                sido_nm=str(it.get("sidoNm") or SIDO_CODES_HIRA.get(sido_cd, "?")),
                atc_cd=str(it.get("atcCd") or atc_cd),
                atc_nm=str(it.get("atcKorNm") or it.get("atcNm") or ATC4_INFLUENZA.get(atc_cd, atc_cd)),
                mdcare_ym=mdcare_ym,
                quantity=int(it.get("totQty") or it.get("qty") or 0),
                amount=int(it.get("totAmt") or it.get("amt") or 0),
            )
        )
    return out


def _iter_months(start: str, end: str) -> list[str]:
    """'2020-01' ~ '2022-12' → ['202001', ..., '202212']."""
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    out: list[str] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m > 12:
            y += 1
            m = 1
    return out


async def backfill_atc4(
    atc_cd: str,
    ym_start: str,
    ym_end: str,
    *,
    sido_cds: list[str] | None = None,
    sleep_sec: float = 0.3,
) -> list[HiraDrugUsage]:
    """ATC 4단계 코드 × N 시도 × ym 범위 backfill.

    Args:
        atc_cd: 예 'J05AH02' (타미플루)
        ym_start, ym_end: 'YYYY-MM'
        sido_cds: 기본 17 시도 전체
        sleep_sec: API rate-limit 회피 (10,000건/일 여유)
    """
    if sido_cds is None:
        sido_cds = list(SIDO_CODES_HIRA.keys())
    months = _iter_months(ym_start, ym_end)
    logger.info(
        "backfill: atc=%s, sido=%d, months=%d, total calls=%d",
        atc_cd, len(sido_cds), len(months), len(sido_cds) * len(months),
    )
    out: list[HiraDrugUsage] = []
    for sido_cd in sido_cds:
        for ym in months:
            try:
                rows = await fetch_atc4_area(atc_cd, sido_cd, ym)
                out.extend(rows)
                logger.info("  %s/%s/%s → %d rows", atc_cd, sido_cd, ym, len(rows))
            except HiraCollectorError as e:
                logger.warning("  skip %s/%s/%s: %s", atc_cd, sido_cd, ym, e)
            await asyncio.sleep(sleep_sec)
    return out


# ─────────────────────── CLI ───────────────────────────────────────────────
async def _amain(args: argparse.Namespace) -> int:
    if args.smoke:
        # 단일 호출 — 응답 envelope 검증용
        env = await fetch_raw(
            "atc4_area",
            atc_cd=args.atc,
            sido_cd=args.sido,
            mdcare_ym=args.ym,
        )
        logger.info("raw envelope (first 1000 chars):\n%s", json.dumps(env, ensure_ascii=False)[:1000])
        items = _items_from_envelope(env)
        logger.info("items: %d", len(items))
        for it in items[:3]:
            logger.info("  field keys: %s", list(it.keys()))
            logger.info("  sample: %s", it)
        return 0

    if args.backfill:
        ym_start, ym_end = args.backfill.split(":")
        atc = args.atc or "J05AH02"
        rows = await backfill_atc4(atc, ym_start, ym_end)
        logger.info("총 %d 행 수집 — atc=%s", len(rows), atc)
        if args.output:
            out_data = [vars(r) for r in rows]
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(out_data, f, ensure_ascii=False, indent=2)
            logger.info("저장: %s", args.output)
        return 0

    # 단일 query
    rows = await fetch_atc4_area(args.atc, args.sido, args.ym)
    logger.info("응답 %d 행", len(rows))
    for r in rows[:5]:
        logger.info("  %s", r)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    p = argparse.ArgumentParser(description="HIRA 의약품사용정보조회 수집기")
    p.add_argument("--atc", default="J05AH02", help="ATC 4단계 코드")
    p.add_argument("--sido", default="110000", help="HIRA 시도코드 (6자리)")
    p.add_argument("--ym", default="202112", help="진료년월 YYYYMM")
    p.add_argument("--smoke", action="store_true", help="단일 호출 envelope 검증")
    p.add_argument("--backfill", help="ym 범위 (예: 2022-01:2022-12) 17 시도 backfill")
    p.add_argument("--output", help="backfill 결과 JSON 저장 경로")
    args = p.parse_args()
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
