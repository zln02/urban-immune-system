"""KCDC 감염병 주간 확진자 수집기 테스트.

케이스:
1. 정상 API 응답 mock — XML 파싱 및 레코드 반환 검증
2. 지역 코드 매핑 — KCDC 코드 → 표준 한글명 변환 검증
3. 빈 응답 처리 — API 응답 없을 때 내장 아카이브 fallback 검증
4. 내장 아카이브 구조 — weeks 파라미터 반영 및 필드 완결성 검증
5. 서울 peak 주차 검증 — 2025-W50이 최대 확진자 주차인지 검증
6. API HTTP 오류 → fallback 검증
7. XML 파싱 오류 → fallback 검증
8. _build_archive_records — 17지역 broadcast 및 비율 계산 검증
9. _week_to_isoweek 변환 검증
10. DB INSERT/UPSERT mock 검증 (_insert_records)
11. insert_confirmed_sync 동기 래퍼 검증
12. collect_and_insert_weekly 스케줄러 진입점 검증
13. API 키 있을 때 API 결과 사용 및 지역 필터링 검증
14. API 결과 빈 경우 아카이브 fallback 검증
"""
from __future__ import annotations

from datetime import datetime, timezone
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


# ─────────────────────── Case 6: API HTTP 오류 → fallback ────────────────
@pytest.mark.asyncio
async def test_api_http_error_returns_none():
    """API 호출 시 4xx/5xx 오류 발생 시 None 반환 (fallback 트리거)."""
    import httpx
    from pipeline.collectors.kcdc_collector import _fetch_from_api

    with (
        patch("os.getenv", side_effect=lambda k, d="": "test_key" if k == "DATA_GO_KR_API_KEY" else d),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500 Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_from_api(disease="influenza", weeks=4)

    assert result is None, "HTTP 오류 시 None 반환해야 함"


@pytest.mark.asyncio
async def test_api_connect_error_returns_none():
    """API 연결 오류(네트워크 문제) 시 None 반환."""
    import httpx
    from pipeline.collectors.kcdc_collector import _fetch_from_api

    with (
        patch("os.getenv", side_effect=lambda k, d="": "test_key" if k == "DATA_GO_KR_API_KEY" else d),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("연결 실패")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_from_api(disease="influenza", weeks=4)

    assert result is None, "연결 오류 시 None 반환해야 함"


@pytest.mark.asyncio
async def test_api_timeout_returns_none():
    """API 타임아웃 시 None 반환."""
    import httpx
    from pipeline.collectors.kcdc_collector import _fetch_from_api

    with (
        patch("os.getenv", side_effect=lambda k, d="": "test_key" if k == "DATA_GO_KR_API_KEY" else d),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("타임아웃"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _fetch_from_api(disease="influenza", weeks=4)

    assert result is None, "타임아웃 시 None 반환해야 함"


# ─────────────────────── Case 7: XML 파싱 오류 → fallback ────────────────
@pytest.mark.asyncio
async def test_api_xml_parse_error_returns_none():
    """응답이 유효하지 않은 XML일 때 None 반환."""
    from pipeline.collectors.kcdc_collector import _fetch_from_api

    mock_resp = MagicMock()
    mock_resp.text = "<<<INVALID XML>>>"
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

    assert result is None, "XML 파싱 오류 시 None 반환해야 함"


# ─────────────────────── Case 8: 17지역 broadcast 및 비율 계산 ────────────
def test_build_archive_records_17_regions():
    """_build_archive_records가 17개 지역에 대해 독립적인 레코드를 생성하는지 검증."""
    from pipeline.collectors.kcdc_collector import REGIONS_17, _build_archive_records

    records = _build_archive_records(disease="influenza", weeks=5)

    # 각 주차마다 17개 레코드 (최대 5주 × 17지역 = 85)
    assert len(records) <= 5 * 17
    assert len(records) > 0

    # 지역 목록에 17개 전체 포함
    regions_in_records = {r["region"] for r in records}
    for region in REGIONS_17:
        assert region in regions_in_records, f"지역 누락: {region}"


def test_build_archive_records_region_share_proportional():
    """지역별 확진자 수가 전국 비율(_REGION_SHARE)에 비례하는지 검증."""
    from pipeline.collectors.kcdc_collector import _NATIONAL_ARCHIVE, _REGION_SHARE, _build_archive_records

    records = _build_archive_records(disease="influenza", weeks=1, regions=["서울특별시", "경기도"])

    # 마지막 1주만
    assert len(records) == 2

    seoul_r = next(r for r in records if r["region"] == "서울특별시")
    gyeonggi_r = next(r for r in records if r["region"] == "경기도")

    # 경기도가 서울보다 비율이 높음 (0.262 > 0.186)
    assert gyeonggi_r["case_count"] > seoul_r["case_count"], "경기도 > 서울 비율이어야 함"


def test_build_archive_records_per_100k_calculated():
    """per_100k 값이 (case_count / population × 100000)으로 계산되는지 검증."""
    from pipeline.collectors.kcdc_collector import REGION_POPULATION, _build_archive_records

    records = _build_archive_records(disease="influenza", weeks=1, regions=["서울특별시"])
    assert len(records) == 1
    r = records[0]

    expected_per_100k = round(r["case_count"] / REGION_POPULATION["서울특별시"] * 100_000, 2)
    assert r["per_100k"] == pytest.approx(expected_per_100k, abs=0.1)


# ─────────────────────── Case 9: _week_to_isoweek 변환 ───────────────────
def test_week_to_isoweek_conversion():
    """_week_to_isoweek가 YYYY-MM-DD → ISO 주차 포맷으로 변환하는지 검증."""
    from pipeline.collectors.kcdc_collector import _week_to_isoweek

    assert _week_to_isoweek("2025-12-08") == "2025-W50"
    assert _week_to_isoweek("2025-01-06") == "2025-W02"
    assert _week_to_isoweek("2026-01-05") == "2026-W02"


# ─────────────────────── Case 10: DB INSERT mock 검증 ─────────────────────
@pytest.mark.asyncio
async def test_insert_records_upsert_mock():
    """_insert_records가 asyncpg를 통해 UPSERT를 실행하는지 mock으로 검증."""
    from pipeline.collectors.kcdc_collector import _insert_records

    # 테스트용 레코드
    test_records = [
        {
            "time": datetime(2025, 12, 8, tzinfo=timezone.utc),
            "region": "서울특별시",
            "disease": "influenza",
            "case_count": 43040,
            "per_100k": 448.1,
            "source": "KCDC_ARCHIVE",
            "iso_week": "2025-W50",
        }
    ]

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    mock_acquire_ctx = AsyncMock()
    mock_acquire_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_ctx)
    mock_pool.close = AsyncMock()

    with patch("asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
        inserted = await _insert_records(test_records)

    assert inserted == 1
    mock_conn.execute.assert_called_once()
    # INSERT INTO confirmed_cases 쿼리 포함 확인
    call_args = mock_conn.execute.call_args[0]
    assert "INSERT INTO confirmed_cases" in call_args[0]
    assert "ON CONFLICT" in call_args[0]


@pytest.mark.asyncio
async def test_insert_records_handles_exception():
    """개별 레코드 INSERT 오류 시 나머지 레코드는 계속 처리되는지 검증."""
    from pipeline.collectors.kcdc_collector import _insert_records

    test_records = [
        {
            "time": datetime(2025, 12, 8, tzinfo=timezone.utc),
            "region": "서울특별시",
            "disease": "influenza",
            "case_count": 43040,
            "per_100k": 448.1,
            "source": "KCDC_ARCHIVE",
            "iso_week": "2025-W50",
        },
        {
            "time": datetime(2025, 12, 8, tzinfo=timezone.utc),
            "region": "경기도",
            "disease": "influenza",
            "case_count": 60800,
            "per_100k": 448.1,
            "source": "KCDC_ARCHIVE",
            "iso_week": "2025-W50",
        },
    ]

    mock_conn = AsyncMock()
    # 첫 번째는 실패, 두 번째는 성공
    mock_conn.execute = AsyncMock(side_effect=[Exception("DB 오류"), None])

    mock_acquire_ctx = AsyncMock()
    mock_acquire_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_ctx)
    mock_pool.close = AsyncMock()

    with patch("asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
        inserted = await _insert_records(test_records)

    # 첫 번째 실패해도 두 번째는 성공 → inserted=1
    assert inserted == 1


# ─────────────────────── Case 11: insert_confirmed_sync 동기 래퍼 ─────────
def test_insert_confirmed_sync():
    """insert_confirmed_sync가 asyncio.run(_insert_records(…))를 호출하는지 검증."""
    from pipeline.collectors.kcdc_collector import insert_confirmed_sync

    test_records = [
        {
            "time": datetime(2025, 12, 8, tzinfo=timezone.utc),
            "region": "서울특별시",
            "disease": "influenza",
            "case_count": 43040,
            "per_100k": 448.1,
            "source": "KCDC_ARCHIVE",
            "iso_week": "2025-W50",
        }
    ]

    with patch("pipeline.collectors.kcdc_collector._insert_records", AsyncMock(return_value=1)) as mock_insert:
        result = insert_confirmed_sync(test_records)

    assert result == 1
    mock_insert.assert_called_once_with(test_records)


# ─────────────────────── Case 12: collect_and_insert_weekly 스케줄러 ──────
def test_collect_and_insert_weekly():
    """collect_and_insert_weekly가 collect → insert 순서로 동작하는지 검증."""
    from pipeline.collectors.kcdc_collector import collect_and_insert_weekly

    fake_records = [{"region": "서울특별시", "disease": "influenza", "iso_week": "2026-W01", "case_count": 1000}]

    with (
        patch("pipeline.collectors.kcdc_collector.collect_weekly_confirmed", return_value=fake_records) as mock_collect,
        patch("pipeline.collectors.kcdc_collector.insert_confirmed_sync", return_value=1) as mock_insert,
    ):
        collect_and_insert_weekly(disease="influenza")

    mock_collect.assert_called_once_with(disease="influenza", weeks=1)
    mock_insert.assert_called_once_with(fake_records)


# ─────────────────────── Case 13: API 결과 있을 때 지역 필터링 ─────────────
def test_collect_weekly_uses_api_result_when_available():
    """API 응답이 있으면 아카이브 대신 API 결과를 반환하는지 검증."""
    from pipeline.collectors.kcdc_collector import collect_weekly_confirmed

    api_records = [
        {
            "region": "서울특별시",
            "disease": "influenza",
            "iso_week": "2026-W10",
            "week_start": "2026-03-02",
            "time": datetime(2026, 3, 2, tzinfo=timezone.utc),
            "case_count": 5000,
            "per_100k": 52.1,
            "source": "KCDC_API",
        },
        {
            "region": "경기도",
            "disease": "influenza",
            "iso_week": "2026-W10",
            "week_start": "2026-03-02",
            "time": datetime(2026, 3, 2, tzinfo=timezone.utc),
            "case_count": 9800,
            "per_100k": 72.2,
            "source": "KCDC_API",
        },
    ]

    with patch("pipeline.collectors.kcdc_collector._fetch_from_api", AsyncMock(return_value=api_records)):
        result = collect_weekly_confirmed(disease="influenza", weeks=4, regions=["서울특별시"])

    # API 결과 중 요청 지역만 반환
    assert all(r["source"] == "KCDC_API" for r in result)
    assert all(r["region"] == "서울특별시" for r in result)


# ─────────────────────── Case 14: API 결과 빈 경우 → 아카이브 fallback ─────
def test_collect_weekly_falls_back_when_api_returns_empty():
    """API 결과가 비어있거나 요청 지역 없을 때 아카이브 fallback 동작 검증."""
    from pipeline.collectors.kcdc_collector import collect_weekly_confirmed

    # API가 다른 지역만 반환 → 필터 후 빈 리스트 → fallback
    api_records = [
        {
            "region": "부산광역시",
            "disease": "influenza",
            "iso_week": "2026-W10",
            "week_start": "2026-03-02",
            "time": datetime(2026, 3, 2, tzinfo=timezone.utc),
            "case_count": 2000,
            "per_100k": 60.0,
            "source": "KCDC_API",
        }
    ]

    with patch("pipeline.collectors.kcdc_collector._fetch_from_api", AsyncMock(return_value=api_records)):
        result = collect_weekly_confirmed(disease="influenza", weeks=5, regions=["서울특별시"])

    # 필터 후 빈 리스트 → 아카이브 fallback
    assert len(result) > 0
    assert all(r["source"] == "KCDC_ARCHIVE" for r in result)


# ─────────────────────── Case 15: 잘못된 yearW 포맷 → 레코드 건너뜀 ────────
@pytest.mark.asyncio
async def test_api_invalid_year_week_format_skipped():
    """yearW 필드가 6자리가 아닌 item은 파싱 시 건너뛰어야 함."""
    from pipeline.collectors.kcdc_collector import _fetch_from_api

    xml_with_invalid = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <body>
    <items>
      <item>
        <stnNm>서울</stnNm>
        <yearW>INVALID</yearW>
        <cnt>1000</cnt>
        <per100k>10.0</per100k>
      </item>
      <item>
        <stnNm>경기</stnNm>
        <yearW>202550</yearW>
        <cnt>2000</cnt>
        <per100k>14.7</per100k>
      </item>
    </items>
  </body>
</response>"""

    mock_resp = MagicMock()
    mock_resp.text = xml_with_invalid
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

        records = await _fetch_from_api(disease="influenza", weeks=4)

    # INVALID yearW → 건너뜀, 경기 1개만 반환
    assert records is not None
    assert len(records) == 1
    assert records[0]["region"] == "경기도"
