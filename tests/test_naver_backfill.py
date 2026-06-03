"""Naver DataLab OTC + Search 시계열 백필 테스트.

케이스:
1. _client() — 환경변수 없을 때 RuntimeError 검증
2. _client() — 정상 환경변수로 httpx.Client 생성 검증
3. fetch_search_series — 정상 응답 mock
4. fetch_shopping_series — 정상 응답 mock
5. rate limit(429) → raise_for_status 예외 처리
6. backfill_layer — 정상 경로 (17지역 × N주 INSERT 건수)
7. backfill_layer — 빈 시계열 입력 시 0 반환
8. zero-collapse 방지 — 비수기 raw=0.98 값이 그대로 유지됨 (회귀 방지)
9. source 라벨 통일 — OTC는 'naver_shopping_insight' 검증
10. run_backfill — both 레이어 성공 경로
11. run_backfill — search-only 경로
12. run_backfill — otc-only 경로
13. run_backfill — regions='single' → 서울만 적재
14. fetch_search_series — 빈 data 응답 처리
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────── Fixtures ────────────────────────────────────────
def _make_search_resp(weeks: int = 4) -> dict:
    """DataLab 검색 API 정상 응답 픽스처."""
    start = date(2026, 3, 1)
    data = [
        {"period": (start + timedelta(weeks=i)).strftime("%Y-%m-%d"), "ratio": float(50 + i * 5)} for i in range(weeks)
    ]
    return {"results": [{"data": data}]}


def _make_shopping_resp(weeks: int = 4) -> dict:
    """쇼핑인사이트 API 정상 응답 픽스처."""
    start = date(2026, 3, 1)
    data = [
        {"period": (start + timedelta(weeks=i)).strftime("%Y-%m-%d"), "ratio": float(40 + i * 4)} for i in range(weeks)
    ]
    return {"results": [{"data": data}]}


class FakeResp:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


class RateLimitResp:
    """429 Too Many Requests 시뮬레이션."""

    def raise_for_status(self) -> None:
        import httpx

        raise httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )

    def json(self) -> dict:
        return {}


# ─────────────────────── Case 1: _client() 환경변수 없을 때 오류 ─────────
def test_client_raises_without_env(monkeypatch: pytest.MonkeyPatch):
    """NAVER 환경변수 없으면 RuntimeError."""
    monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)

    from pipeline.collectors.naver_backfill import _client

    with pytest.raises(RuntimeError, match="NAVER_CLIENT_ID"):
        _client()


# ─────────────────────── Case 2: _client() 정상 생성 ─────────────────────
def test_client_created_with_env(monkeypatch: pytest.MonkeyPatch):
    """환경변수 설정 시 httpx.Client가 생성되고 헤더에 인증 정보 포함."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    from pipeline.collectors.naver_backfill import _client

    with _client() as client:
        assert "X-Naver-Client-Id" in client.headers
        assert client.headers["X-Naver-Client-Id"] == "test-id"
        assert client.headers["X-Naver-Client-Secret"] == "test-secret"


# ─────────────────────── Case 3: fetch_search_series 정상 응답 ─────────────
def test_fetch_search_series_normal(monkeypatch: pytest.MonkeyPatch):
    """DataLab 검색 API 정상 응답 mock → (date, ratio) 튜플 리스트 반환."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    from pipeline.collectors.naver_backfill import fetch_search_series

    payload = _make_search_resp(weeks=4)
    fake_resp = FakeResp(payload)

    mock_client = MagicMock(spec=["post"])
    mock_client.post = MagicMock(return_value=fake_resp)

    result = fetch_search_series(mock_client, date(2026, 3, 1), date(2026, 3, 28))

    assert len(result) == 4
    assert isinstance(result[0][0], date)
    assert isinstance(result[0][1], float)
    # 첫 주 ratio == 50.0
    assert result[0][1] == pytest.approx(50.0)


# ─────────────────────── Case 4: fetch_shopping_series 정상 응답 ───────────
def test_fetch_shopping_series_normal(monkeypatch: pytest.MonkeyPatch):
    """쇼핑인사이트 API 정상 응답 mock → (date, ratio) 튜플 리스트 반환."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    from pipeline.collectors.naver_backfill import fetch_shopping_series

    payload = _make_shopping_resp(weeks=3)
    fake_resp = FakeResp(payload)

    mock_client = MagicMock(spec=["post"])
    mock_client.post = MagicMock(return_value=fake_resp)

    result = fetch_shopping_series(mock_client, date(2026, 3, 1), date(2026, 3, 21))

    assert len(result) == 3
    assert result[0][1] == pytest.approx(40.0)
    assert result[2][1] == pytest.approx(48.0)


# ─────────────────────── Case 5: rate limit(429) → 예외 전파 ─────────────
def test_fetch_search_series_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """API 429 응답 시 HTTPStatusError 전파 — run_backfill에서 catch해야 함."""
    import httpx

    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    from pipeline.collectors.naver_backfill import fetch_search_series

    fake_resp = RateLimitResp()
    mock_client = MagicMock(spec=["post"])
    mock_client.post = MagicMock(return_value=fake_resp)

    with pytest.raises(httpx.HTTPStatusError):
        fetch_search_series(mock_client, date(2026, 3, 1), date(2026, 3, 28))


# ─────────────────────── Case 6: backfill_layer 정상 경로 ─────────────────
@pytest.mark.asyncio
async def test_backfill_layer_normal_inserts(monkeypatch: pytest.MonkeyPatch):
    """backfill_layer가 series × regions 수만큼 insert_signal을 호출하는지 검증."""
    from pipeline.collectors import naver_backfill

    series = [(date(2026, 3, 1) + timedelta(weeks=i), float(50 + i * 5)) for i in range(4)]
    regions = ["서울특별시", "경기도", "부산광역시"]

    insert_calls: list[dict] = []

    async def fake_insert_signal(**kwargs):
        insert_calls.append(kwargs)

    async def fake_delete_range(**kwargs):
        return 0

    monkeypatch.setattr(naver_backfill, "insert_signal", fake_insert_signal)
    monkeypatch.setattr(naver_backfill, "delete_signal_range", fake_delete_range)

    count = await naver_backfill.backfill_layer(
        layer="search",
        series=series,
        source="naver_datalab",
        regions=regions,
    )

    # 4주 × 3지역 = 12건
    assert count == 12
    assert len(insert_calls) == 12

    # layer, source 정확히 전달됐는지
    for call in insert_calls:
        assert call["layer"] == "search"
        assert call["source"] == "naver_datalab"


# ─────────────────────── Case 7: backfill_layer 빈 시계열 ─────────────────
@pytest.mark.asyncio
async def test_backfill_layer_empty_series(monkeypatch: pytest.MonkeyPatch):
    """빈 시계열 입력 시 0 반환 (INSERT 없음)."""
    from pipeline.collectors import naver_backfill

    insert_calls: list[dict] = []

    async def fake_insert_signal(**kwargs):
        insert_calls.append(kwargs)

    async def fake_delete_range(**kwargs):
        return 0

    monkeypatch.setattr(naver_backfill, "insert_signal", fake_insert_signal)
    monkeypatch.setattr(naver_backfill, "delete_signal_range", fake_delete_range)

    count = await naver_backfill.backfill_layer(
        layer="otc",
        series=[],
        source="naver_shopping_insight",
        regions=["서울특별시"],
    )

    assert count == 0
    assert len(insert_calls) == 0


# ─────────────────────── Case 8: zero-collapse 방지 ──────────────────────
@pytest.mark.asyncio
async def test_backfill_layer_no_zero_collapse(monkeypatch: pytest.MonkeyPatch):
    """비수기 raw=0.98 값이 min-max 재정규화 없이 그대로 value=0.98로 유지됨."""
    from pipeline.collectors import naver_backfill

    # 56주 시계열: 피크100 → 비수기 0.98
    series = [
        (date(2026, 4, 27) - timedelta(weeks=56 - i), float(v))
        for i, v in enumerate(
            [50] * 5 + [80, 95, 100, 90, 70, 50, 30, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1.5, 1.2, 1.0] + [0.98] * 32
        )
    ]
    assert series[-1][1] == pytest.approx(0.98)

    captured: list[dict] = []

    async def fake_insert_signal(**kwargs):
        captured.append(kwargs)

    async def fake_delete_range(**kwargs):
        return 0

    monkeypatch.setattr(naver_backfill, "insert_signal", fake_insert_signal)
    monkeypatch.setattr(naver_backfill, "delete_signal_range", fake_delete_range)

    await naver_backfill.backfill_layer(
        layer="search",
        series=series,
        source="naver_datalab",
        regions=["서울특별시"],
    )

    last = captured[-1]
    assert last["value"] == pytest.approx(0.98, abs=1e-6), (
        f"zero-collapse 재발: raw=0.98인데 value={last['value']}. backfill_layer가 raw 그대로 사용해야 함."
    )
    assert last["raw_value"] == pytest.approx(0.98, abs=1e-6)


# ─────────────────────── Case 9: source 라벨 통일 ────────────────────────
def test_otc_source_label_unified():
    """run_backfill OTC 호출이 'naver_shopping_insight' source를 사용하는지 코드 검증."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "pipeline" / "collectors" / "naver_backfill.py"
    text = src.read_text(encoding="utf-8")

    assert "if do_otc:" in text, "naver_backfill.py에 do_otc 가드가 있어야 함"
    otc_block = text.split("if do_otc:")[1].split("return counts")[0]
    assert '"naver_shopping_insight"' in otc_block, (
        "OTC backfill source가 'naver_shopping_insight'로 통일돼야 함 (do_otc 블록 내부)"
    )


# ─────────────────────── Case 10: run_backfill both 레이어 ────────────────
@pytest.mark.asyncio
async def test_run_backfill_both_layers(monkeypatch: pytest.MonkeyPatch):
    """run_backfill(layers='both')가 search + otc 모두 적재하고 건수를 반환하는지 검증."""
    from pipeline.collectors import naver_backfill

    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    search_series = [(date(2026, 3, 1) + timedelta(weeks=i), float(50 + i)) for i in range(3)]
    shopping_series = [(date(2026, 3, 1) + timedelta(weeks=i), float(40 + i)) for i in range(3)]

    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_client_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(naver_backfill, "_client", return_value=mock_client_ctx),
        patch.object(naver_backfill, "fetch_search_series", return_value=search_series),
        patch.object(naver_backfill, "fetch_shopping_series", return_value=shopping_series),
        patch.object(naver_backfill, "backfill_layer", new=AsyncMock(side_effect=[17 * 3, 17 * 3])),
    ):
        result = await naver_backfill.run_backfill(weeks=4, layers="both", regions="all")

    assert "search" in result
    assert "otc" in result
    assert result["search"] == 17 * 3
    assert result["otc"] == 17 * 3


# ─────────────────────── Case 11: run_backfill search-only ────────────────
@pytest.mark.asyncio
async def test_run_backfill_search_only(monkeypatch: pytest.MonkeyPatch):
    """layers='search' 시 search만 적재되고 otc는 결과에 없음."""
    from pipeline.collectors import naver_backfill

    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    search_series = [(date(2026, 3, 1), 55.0)]

    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_client_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(naver_backfill, "_client", return_value=mock_client_ctx),
        patch.object(naver_backfill, "fetch_search_series", return_value=search_series),
        patch.object(naver_backfill, "backfill_layer", new=AsyncMock(return_value=17)),
    ):
        result = await naver_backfill.run_backfill(weeks=4, layers="search", regions="all")

    assert "search" in result
    assert "otc" not in result


# ─────────────────────── Case 12: run_backfill otc-only ───────────────────
@pytest.mark.asyncio
async def test_run_backfill_otc_only(monkeypatch: pytest.MonkeyPatch):
    """layers='otc' 시 otc만 적재되고 search는 결과에 없음."""
    from pipeline.collectors import naver_backfill

    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    shopping_series = [(date(2026, 3, 1), 45.0)]

    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_client_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(naver_backfill, "_client", return_value=mock_client_ctx),
        patch.object(naver_backfill, "fetch_shopping_series", return_value=shopping_series),
        patch.object(naver_backfill, "backfill_layer", new=AsyncMock(return_value=17)),
    ):
        result = await naver_backfill.run_backfill(weeks=4, layers="otc", regions="all")

    assert "otc" in result
    assert "search" not in result


# ─────────────────────── Case 13: run_backfill regions='single' ───────────
@pytest.mark.asyncio
async def test_run_backfill_single_region(monkeypatch: pytest.MonkeyPatch):
    """regions='single' 시 서울특별시만 적재 (backfill_layer regions 인자 검증)."""
    from pipeline.collectors import naver_backfill

    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    search_series = [(date(2026, 3, 1), 55.0)]
    captured_regions: list[list[str]] = []

    async def fake_backfill_layer(layer, series, source, regions, pathogen="influenza"):
        captured_regions.append(regions)
        return len(regions) * len(series)

    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_client_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(naver_backfill, "_client", return_value=mock_client_ctx),
        patch.object(naver_backfill, "fetch_search_series", return_value=search_series),
        patch.object(naver_backfill, "backfill_layer", new=fake_backfill_layer),
    ):
        await naver_backfill.run_backfill(weeks=4, layers="search", regions="single")

    assert len(captured_regions) == 1
    assert captured_regions[0] == ["서울특별시"]


# ─────────────────────── Case 14: fetch_search_series 빈 data 처리 ─────────
def test_fetch_search_series_empty_data(monkeypatch: pytest.MonkeyPatch):
    """결과 data가 빈 배열일 때 빈 리스트 반환."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    from pipeline.collectors.naver_backfill import fetch_search_series

    payload = {"results": [{"data": []}]}
    fake_resp = FakeResp(payload)
    mock_client = MagicMock(spec=["post"])
    mock_client.post = MagicMock(return_value=fake_resp)

    result = fetch_search_series(mock_client, date(2026, 3, 1), date(2026, 3, 28))

    assert result == []


# ─────────────────────── Case 15: run_backfill API 예외 처리 ──────────────
@pytest.mark.asyncio
async def test_run_backfill_handles_search_exception(monkeypatch: pytest.MonkeyPatch):
    """Search 수집 실패 시 counts['search']=0 반환 (예외 전파 X)."""
    from pipeline.collectors import naver_backfill

    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")

    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_client_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(naver_backfill, "_client", return_value=mock_client_ctx),
        patch.object(naver_backfill, "fetch_search_series", side_effect=Exception("API 실패")),
    ):
        result = await naver_backfill.run_backfill(weeks=4, layers="search", regions="single")

    assert result.get("search", 0) == 0


# ─────────────────────── Case 16: backfill_layer 100 초과 clamp ───────────
@pytest.mark.asyncio
async def test_backfill_layer_clamps_above_100(monkeypatch: pytest.MonkeyPatch):
    """raw > 100 값은 value=100으로 clamp되어야 함."""
    from pipeline.collectors import naver_backfill

    series = [(date(2026, 3, 1), 150.0), (date(2026, 3, 8), 50.0)]
    captured: list[dict] = []

    async def fake_insert_signal(**kwargs):
        captured.append(kwargs)

    async def fake_delete_range(**kwargs):
        return 0

    monkeypatch.setattr(naver_backfill, "insert_signal", fake_insert_signal)
    monkeypatch.setattr(naver_backfill, "delete_signal_range", fake_delete_range)

    await naver_backfill.backfill_layer(
        layer="otc",
        series=series,
        source="naver_shopping_insight",
        regions=["서울특별시"],
    )

    assert captured[0]["value"] == 100.0
    assert captured[1]["value"] == 50.0
