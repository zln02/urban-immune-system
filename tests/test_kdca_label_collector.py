"""KDCA 전수신고 감염병 발생현황 (publicDataPk=15139178) 라벨 수집기 회귀 테스트.

회귀 방지 대상:
- OPERATIONS path 가 PascalCase (Swagger UI 사양) — `getXxx` prefix 금지
- resType 은 숫자 2 (JSON) — 문자열 'json' 보내면 104 DATATYPE_PARAMETER_ERROR
- 응답 envelope 가 {"response":{"body":{"items":{"item": [...]}}}} 중첩 — body 직접 접근 금지
- 1·2·3급 67종만 — 4급 표본감시 라벨은 이 API 로 가져올 수 없음 (DISEASE_NAME_MAP 가 그에 맞게 정의)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from pipeline.collectors import kdca_label_collector as col


# ─────────────────────── 상수 회귀 ─────────────────────────────────────────
class TestOperationsConstants:
    """OPERATIONS path 가 사양에서 벗어나면 모든 호출이 404 → 회귀 차단."""

    def test_base_url_eidapiservice(self):
        assert col.BASE_URL == "https://apis.data.go.kr/1790387/EIDAPIService"

    def test_operations_pascalcase_no_get_prefix(self):
        """PascalCase 검증 — `getXxx` 형태 들어가면 fail."""
        assert col.OPERATIONS["period"] == "/PeriodBasic"
        assert col.OPERATIONS["sido"] == "/Region"
        assert col.OPERATIONS["disease"] == "/Disease"
        # death 만 lowercase (사양 그대로)
        assert col.OPERATIONS["death"] == "/death"
        for k, v in col.OPERATIONS.items():
            assert v.startswith("/"), f"OPERATIONS[{k}] must start with /"
            assert "get" not in v.lower() or v == "/death", (
                f"OPERATIONS[{k}]={v} — `get` prefix 는 EIDAPIService 사양에 없음 (404 발생)"
            )

    def test_sido_codes_17_regions_plus_nation(self):
        """SIDO_CODES 18개 (00 전국 + 17 시·도)."""
        assert len(col.SIDO_CODES) == 18
        assert col.SIDO_CODES["00"] == "전국"
        assert col.SIDO_CODES["01"] == "서울특별시"
        assert col.SIDO_CODES["17"] == "세종특별자치시"

    def test_disease_name_map_excludes_4th_grade(self):
        """4급 표본감시(계절성 인플루엔자/COVID/노로) 는 이 API 에 없음 → 매핑에서 제외돼야 한다.

        만약 'influenza' 또는 'covid' 키가 다시 추가되면 라벨 정확성이 부풀려져
        backtest 가 거짓 양성에 가까워진다. 4급 표본감시는 별도 collector 사용.
        """
        assert "influenza" not in col.DISEASE_NAME_MAP, (
            "계절성 인플루엔자(4급) 라벨은 EIDAPIService 가 제공하지 않음 — "
            "표본감시 collector 로 분리 필수"
        )
        assert "covid" not in col.DISEASE_NAME_MAP
        assert "norovirus" not in col.DISEASE_NAME_MAP
        # 1·2·3급 확장 데모 라벨은 살아있어야 함
        assert "pertussis" in col.DISEASE_NAME_MAP  # 백일해 2급
        assert "measles" in col.DISEASE_NAME_MAP    # 홍역 2급


# ─────────────────────── API 키 처리 ──────────────────────────────────────
class TestApiKeyResolution:
    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)
        assert col._api_key() is None

    def test_returns_none_for_placeholder(self, monkeypatch):
        """`.env.example` 의 placeholder 값을 실수로 .env 에 둔 경우 호출 차단."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "your_data_go_kr_key")
        assert col._api_key() is None

    def test_returns_actual_key(self, monkeypatch):
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "abc123real")
        assert col._api_key() == "abc123real"


# ─────────────────────── 호출 흐름 ────────────────────────────────────────
_SAMPLE_RESPONSE = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
        "body": {
            "items": {
                "item": [
                    {"period": "2024년 01주", "icdGroupNm": "제2급",
                     "icdNm": "백일해", "resultVal": "42"},
                    {"period": "2024년 01주", "icdGroupNm": "제2급",
                     "icdNm": "홍역", "resultVal": "3"},
                    {"period": "2024년 01주", "icdGroupNm": "제1급",
                     "icdNm": "에볼라바이러스병", "resultVal": "0"},
                ]
            },
            "pageNo": "1",
            "numOfRows": 3,
            "totalCount": "3551",
        },
    }
}


class TestFetchByPeriod:
    def test_returns_items_on_success(self, monkeypatch):
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "k")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        with patch.object(col.httpx, "Client", return_value=mock_client):
            items = col.fetch_by_period(
                search_period_type=3, start_year=2024, num_of_rows=3,
            )
        assert len(items) == 3
        assert items[0]["icdNm"] == "백일해"
        # path 가 PascalCase 로 호출됐는지 검증
        call_args = mock_client.get.call_args
        assert call_args.args[0].endswith("/PeriodBasic")
        # resType 가 숫자 2 인지 (사양 위반 방지)
        assert call_args.kwargs["params"]["resType"] == 2

    def test_empty_when_no_key(self, monkeypatch):
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)
        assert col.fetch_by_period(start_year=2024) == []

    def test_empty_on_http_error(self, monkeypatch):
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "k")
        import httpx
        mock_resp = MagicMock(status_code=500, text="server error")
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "boom", request=MagicMock(), response=mock_resp,
        )
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        with patch.object(col.httpx, "Client", return_value=mock_client):
            items = col.fetch_by_period(start_year=2024)
        assert items == []

    def test_single_item_dict_wrapped_into_list(self, monkeypatch):
        """numOfRows=1 일 때 KDCA 가 item 을 dict 단일로 반환 — 우리는 list 통일."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "k")
        single = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": {
                    "period": "2024년 01주", "icdGroupNm": "제2급",
                    "icdNm": "수두", "resultVal": "517",
                }}},
            }
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = single
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        with patch.object(col.httpx, "Client", return_value=mock_client):
            items = col.fetch_by_period(start_year=2024)
        assert isinstance(items, list) and len(items) == 1
        assert items[0]["icdNm"] == "수두"


class TestFetchByPeriodAll:
    def test_stops_when_page_smaller_than_chunk(self, monkeypatch):
        """마지막 페이지가 num_of_rows 미만이면 더 호출하지 않음."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "k")
        # 2개만 반환 → 1페이지로 종료
        with patch.object(col, "fetch_by_period") as mock_fetch:
            mock_fetch.return_value = [{"icdNm": "x"}, {"icdNm": "y"}]
            agg = col.fetch_by_period_all(num_of_rows=1000, max_pages=5)
        # 첫 페이지가 1000 미만이라 1회만 호출
        assert mock_fetch.call_count == 1
        assert len(agg) == 2

    def test_max_pages_guard(self, monkeypatch):
        """max_pages 까지만 호출 — 무한루프 차단."""
        monkeypatch.setenv("DATA_GO_KR_API_KEY", "k")
        with patch.object(col, "fetch_by_period") as mock_fetch:
            mock_fetch.return_value = [{"icdNm": "x"}] * 1000  # 매번 가득
            col.fetch_by_period_all(num_of_rows=1000, max_pages=3)
        assert mock_fetch.call_count == 3


# ─────────────────────── 정규화 ───────────────────────────────────────────
class TestNormalize:
    def test_disease_code_matched(self):
        assert col.to_disease_code("백일해") == "pertussis"
        assert col.to_disease_code("홍역") == "measles"

    def test_disease_code_skipped_when_no_match(self):
        assert col.to_disease_code("에볼라바이러스병") is None
        # 4급 라벨은 매핑 자체에 없으므로 None (이 API 가 제공해도 무시)
        assert col.to_disease_code("인플루엔자") is None

    def test_normalize_period_item_basic(self):
        item = {
            "period": "2024년 01주", "icdGroupNm": "제2급",
            "icdNm": "백일해", "resultVal": "42",
        }
        r = col.normalize_period_item(item)
        assert r is not None
        assert r["disease"] == "pertussis"
        assert r["case_count"] == 42
        assert r["source"] == "KDCA_EID_API"
        assert r["period"] == "2024년 01주"

    def test_normalize_period_item_skipped_for_unmapped(self):
        item = {"period": "2024년 01주", "icdGroupNm": "제1급",
                "icdNm": "에볼라바이러스병", "resultVal": "0"}
        assert col.normalize_period_item(item) is None

    def test_normalize_period_item_invalid_resultval(self):
        """resultVal 이 숫자가 아니면 skip (silent fail 금지 → None)."""
        item = {"period": "x", "icdGroupNm": "제2급",
                "icdNm": "백일해", "resultVal": "N/A"}
        assert col.normalize_period_item(item) is None

    def test_normalize_sido_item_filters_nationwide(self):
        """sidoCd=00 (전국) 은 시·도 라벨로 부적합 → None."""
        item = {"year": "2024", "sidoCd": "00", "sidoNm": "전국",
                "icdNm": "백일해", "resultVal": "100"}
        assert col.normalize_sido_item(item) is None

    def test_normalize_sido_item_maps_region(self):
        item = {"year": "2024", "sidoCd": "01", "sidoNm": "서울",
                "icdNm": "백일해", "resultVal": "12"}
        r = col.normalize_sido_item(item)
        assert r is not None
        assert r["region"] == "서울특별시"
        assert r["sido_cd"] == "01"
        assert r["case_count"] == 12
