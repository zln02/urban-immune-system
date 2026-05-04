"""KCDC 감염병 주간 확진자 수집기 테스트.

케이스:
1. 정상 API 응답 mock — XML 파싱 및 레코드 반환 검증
2. 지역 코드 매핑 — KCDC 코드 → 표준 한글명 변환 검증
3. 빈 응답 처리 — API 응답 없을 때 내장 아카이브 fallback 검증
4. 내장 아카이브 구조 — weeks 파라미터 반영 및 필드 완결성 검증
5. 서울 peak 주차 검증 — 2025-W50이 최대 확진자 주차인지 검증
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─────────────────────── Fixtures ────────────────────────────────────────
SAMPLE_API_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode></header>
  <body>
    <items>
      <item>
        <stnNm>서울</stnNm>
        <yearW>202550</yearW>
        <cnt>43040</cnt>
        <per100k>448.1</per100k>
      </item>
      <item>
        <stnNm>경기</stnNm>
        <yearW>202550</yearW>
        <cnt>60800</cnt>
        <per100k>448.1</per100k>
      </item>
    </items>
  </body>
</response>"""


# ─────────────────────── Case 1: 정상 API 응답 mock ──────────────────────
@pytest.mark.asyncio
async def test_api_xml_parsing_returns_records():
    """API XML 응답이 올바르게 파싱되어 레코드 반환되는지 검증."""
    from pipeline.collectors.kcdc_collector import _fetch_from_api

    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_API_XML
    mock_resp.raise_for_status = MagicMock()

    with (
        patch("os.getenv", side_effect=lambda k, d="": "test_api_key" if k == "DATA_GO_KR_API_KEY" else d),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        records = await _fetch_from_api(disease="influenza", weeks=4)

    assert records is not None, "API 응답이 있으면 None을 반환하면 안 됨"
    assert len(records) == 2, f"2개 item이 파싱되어야 함 (got {len(records)})"

    # 서울 레코드 검증
    seoul = next((r for r in records if r["region"] == "서울특별시"), None)
    assert seoul is not None, "서울특별시 레코드가 있어야 함"
    assert seoul["case_count"] == 43040
    assert seoul["iso_week"] == "2025-W50"
    assert seoul["disease"] == "influenza"
    assert seoul["source"] == "KCDC_API"


# ─────────────────────── Case 2: 지역 코드 매핑 ──────────────────────────
def test_region_code_mapping():
    """KCDC 지역 코드 및 축약명이 표준 한글명으로 올바르게 매핑되는지 검증."""
    from pipeline.collectors.kcdc_collector import KCDC_REGION_MAP

    # 숫자 코드 매핑
    assert KCDC_REGION_MAP["1100"] == "서울특별시"
    assert KCDC_REGION_MAP["4100"] == "경기도"
    assert KCDC_REGION_MAP["4200"] == "강원특별자치도"
    assert KCDC_REGION_MAP["5000"] == "제주특별자치도"

    # 축약명 매핑
    assert KCDC_REGION_MAP["서울"] == "서울특별시"
    assert KCDC_REGION_MAP["경기"] == "경기도"
    assert KCDC_REGION_MAP["전북"] == "전라북도"
    assert KCDC_REGION_MAP["경남"] == "경상남도"

    # 17개 시·도 전체 포함 확인
    from pipeline.collectors.kcdc_collector import REGIONS_17
    assert len(REGIONS_17) == 17, f"17개 시·도여야 함 (got {len(REGIONS_17)})"
    assert "서울특별시" in REGIONS_17
    assert "제주특별자치도" in REGIONS_17


# ─────────────────────── Case 3: 빈 응답 → fallback ─────────────────────
@pytest.mark.asyncio
async def test_empty_api_response_returns_none():
    """API가 item 없는 XML 반환 시 _fetch_from_api가 None을 반환하는지 검증."""
    from pipeline.collectors.kcdc_collector import _fetch_from_api

    empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <response><header><resultCode>00</resultCode></header><body><items/></body></response>"""

    mock_resp = MagicMock()
    mock_resp.text = empty_xml
    mock_resp.raise_for_status = MagicMock()

    with (
        patch("os.getenv", side_effect=lambda k, d="": "test_key" if k == "DATA_GO_KR_API_KEY" else d),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_from_api(disease="influenza", weeks=4)

    assert result is None, "빈 item 응답에서는 None을 반환해야 함"


def test_fallback_to_archive_when_api_key_missing():
    """API 키 없을 때 collect_weekly_confirmed가 내장 아카이브를 사용하는지 검증."""
    from pipeline.collectors.kcdc_collector import collect_weekly_confirmed

    # API 키 없는 환경에서 호출 (DATA_GO_KR_API_KEY 미설정 → _fetch_from_api 즉시 None 반환)
    with patch.dict("os.environ", {}, clear=False):
        # DATA_GO_KR_API_KEY 제거
        import os as _os
        _os.environ.pop("DATA_GO_KR_API_KEY", None)
        records = collect_weekly_confirmed(disease="influenza", weeks=10, regions=["서울특별시"])

    assert len(records) > 0, "fallback 시 내장 아카이브에서 레코드 반환되어야 함"
    assert all(r["source"] == "KCDC_ARCHIVE" for r in records), "fallback source는 KCDC_ARCHIVE여야 함"
    assert all(r["region"] == "서울특별시" for r in records), "요청 지역만 반환되어야 함"


# ─────────────────────── Case 4: 내장 아카이브 구조 검증 ─────────────────
def test_archive_record_structure_and_fields():
    """내장 아카이브 레코드가 필수 필드를 모두 갖추는지, weeks 파라미터가 반영되는지 검증."""
    from pipeline.collectors.kcdc_collector import REGIONS_17, collect_weekly_confirmed

    records = collect_weekly_confirmed(disease="influenza", weeks=20, regions=["서울특별시", "경기도"])

    assert len(records) <= 20 * 2, "weeks × regions 이하여야 함"
    assert len(records) > 0

    required_fields = {"region", "disease", "iso_week", "week_start", "time", "case_count", "per_100k", "source"}
    for r in records:
        missing = required_fields - set(r.keys())
        assert not missing, f"누락 필드: {missing}"

        assert r["region"] in REGIONS_17, f"표준 지역명이어야 함: {r['region']}"
        assert r["case_count"] > 0, "확진자 수는 0보다 커야 함"
        assert r["per_100k"] is not None and r["per_100k"] > 0
        assert r["iso_week"].startswith("20"), f"ISO 주차 형식 이상: {r['iso_week']}"


# ─────────────────────── Case 5: 서울 피크 주차 검증 ─────────────────────
def test_seoul_peak_week_is_2025_w50():
    """서울 데이터에서 2025-W50이 최대 확진자 주차인지 검증 (독감 절기 ground truth)."""
    from pipeline.collectors.kcdc_collector import collect_weekly_confirmed

    records = collect_weekly_confirmed(disease="influenza", weeks=60, regions=["서울특별시"])
    assert len(records) > 0

    peak = max(records, key=lambda r: r["case_count"])
    assert peak["iso_week"] == "2025-W50", (
        f"서울 peak 주차가 2025-W50이어야 함 (got {peak['iso_week']}, count={peak['case_count']})"
    )
    assert peak["case_count"] > 40_000, "서울 peak 확진자 수는 4만 명 초과여야 함"
