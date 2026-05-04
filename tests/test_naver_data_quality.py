"""Naver L1 OTC + L3 search 데이터 품질 회귀 테스트.

회귀 방지 대상:
1. zero-collapse: 비수기 마지막 주가 raw=0.98 인데 정규화 후 value=0 으로 박히는 사고
   (2026-04-27 발생, naver_backfill.backfill_layer 내부 min-max 재정규화 책임)
2. region 미적재: otc_collector.collect_otc_weekly 가 단일 region 만 적재해
   /alerts/regions 17개 region 결손 발생 (2026-04-24 ~ 04-27)
3. source 분기: backfill 'naver_shopping' + collector 'naver_shopping_insight' 가 한 region 에
   섞여 정규화 스케일 차이로 등락 왜곡 (2026-04-13 vs 04-24 vs 04-27)
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest


# ── Fix A: backfill zero-collapse 회귀 방지 ───────────────────────────
class TestBackfillZeroCollapse:
    """backfill_layer 가 raw ratio 를 그대로 0~100 스케일로 사용해야 한다."""

    @pytest.mark.asyncio
    async def test_lowest_week_does_not_collapse_to_zero(self, monkeypatch: pytest.MonkeyPatch):
        """56주 시계열에서 마지막 주가 최저값(0.98)일 때 value=0 으로 박히지 않아야 한다."""
        from pipeline.collectors import naver_backfill

        # 사고 케이스: 비수기 끝, raw=0.98 (peak=100 기준 비수기 최저)
        series = [
            (date(2026, 4, 27) - timedelta(weeks=56 - i), float(v))
            for i, v in enumerate(
                # 인플루엔자 시즌 패턴: 점진 상승 → 피크(100) → 하강 → 비수기(<5)
                [50] * 5 + [80, 95, 100, 90, 70, 50, 30, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1.5, 1.2, 1.0]
                + [0.98] * 32
            )
        ]
        assert series[-1][1] == 0.98

        captured: list[dict] = []

        async def fake_insert_signal(**kwargs):
            captured.append(kwargs)

        async def fake_delete_range(**kwargs):
            return None

        monkeypatch.setattr(naver_backfill, "insert_signal", fake_insert_signal)
        monkeypatch.setattr(naver_backfill, "delete_signal_range", fake_delete_range)

        await naver_backfill.backfill_layer(
            layer="search",
            series=series,
            source="naver_datalab",
            regions=["서울특별시"],
        )

        # 마지막 주 raw=0.98 → value=0.98 (이전 버그: value=0.0)
        last = captured[-1]
        assert last["value"] == pytest.approx(0.98, abs=1e-6), (
            f"zero-collapse 재발: raw=0.98 인데 value={last['value']}. "
            f"backfill_layer 가 raw 그대로 사용해야 함."
        )
        assert last["raw_value"] == pytest.approx(0.98, abs=1e-6)

    @pytest.mark.asyncio
    async def test_raw_above_100_clamped(self, monkeypatch: pytest.MonkeyPatch):
        """raw 가 100 초과 (이상치) 면 value 는 100 으로 clamp."""
        from pipeline.collectors import naver_backfill

        captured: list[dict] = []

        async def fake_insert_signal(**kwargs):
            captured.append(kwargs)

        async def fake_delete_range(**kwargs):
            return None

        monkeypatch.setattr(naver_backfill, "insert_signal", fake_insert_signal)
        monkeypatch.setattr(naver_backfill, "delete_signal_range", fake_delete_range)

        series = [(date(2026, 4, 13), 150.0), (date(2026, 4, 20), 50.0)]
        await naver_backfill.backfill_layer(
            layer="otc", series=series, source="naver_shopping_insight",
            regions=["서울특별시"],
        )
        assert captured[0]["value"] == 100.0
        assert captured[1]["value"] == 50.0


# ── Fix B: otc_collector 17 region broadcast 회귀 방지 ───────────────────
class TestOtcRegionBroadcast:
    """collect_otc_weekly 는 17 region 모두에 적재해야 한다."""

    def test_inserts_to_all_17_sido(self, monkeypatch: pytest.MonkeyPatch):
        from pipeline.collectors import otc_collector

        # 가짜 naver datalab 응답
        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "results": [
                        {
                            "data": [
                                {"period": "2026-04-13", "ratio": 80.0},
                                {"period": "2026-04-20", "ratio": 75.0},
                                {"period": "2026-04-27", "ratio": 92.5},
                            ]
                        }
                    ]
                }

        captured_regions: list[str] = []

        def fake_insert(region, layer, value, raw_value=None, source=None):
            captured_regions.append(region)

        monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
        monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
        monkeypatch.setattr(otc_collector, "insert_signal_sync", fake_insert)
        monkeypatch.setattr(otc_collector.httpx, "post", lambda *a, **kw: FakeResp())

        result = otc_collector.collect_otc_weekly()
        assert result == 92.5

        # 17개 시·도 모두 적재됐는지
        assert len(captured_regions) == 17, (
            f"region broadcast 누락: {len(captured_regions)}/17. "
            f"otc_collector.SIDO_ALL 로 fan-out 해야 함."
        )
        assert set(captured_regions) == set(otc_collector.SIDO_ALL)

    def test_no_naver_key_returns_none(self, monkeypatch: pytest.MonkeyPatch):
        """API 키 없으면 빠르게 None 반환 — 17 region broadcast 시도 안 함."""
        from pipeline.collectors import otc_collector

        monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
        monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)
        result = otc_collector.collect_otc_weekly()
        assert result is None


# ── Fix C: source 통일 정책 — 회귀 방지 ─────────────────────────────────
class TestSourceUnification:
    """OTC backfill 과 collect_otc_weekly 가 같은 source 라벨을 써야 한다."""

    def test_run_backfill_uses_unified_source(self):
        """run_backfill 의 OTC 호출이 'naver_shopping_insight' 를 source 로 쓰는지 코드에서 검증."""
        from pathlib import Path

        src = Path(__file__).resolve().parents[1] / "pipeline" / "collectors" / "naver_backfill.py"
        text = src.read_text(encoding="utf-8")
        # OTC backfill_layer 호출에 'naver_shopping' (legacy) 가 단독으로 들어가면 안 됨
        # 'naver_shopping_insight' 통일 정책
        otc_block = text.split('layers in ("both", "otc")')[1].split("return counts")[0]
        assert '"naver_shopping_insight"' in otc_block, (
            "OTC backfill source 가 'naver_shopping_insight' 로 통일돼야 함 "
            "(otc_collector 와 같은 라벨, 두 source 섞임 방지)"
        )
        assert '"naver_shopping",' not in otc_block.replace('"naver_shopping_insight"', ""), (
            "legacy 'naver_shopping' source 로 backfill 하면 안 됨 — 정규화 스케일 분기 사고 재발"
        )
