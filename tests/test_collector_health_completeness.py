"""Collector silent-fail detector — region completeness 회귀 테스트.

2026-06-01 사고 재발 방지:
- otc 인플루엔자 backfill 이 6지역 silent miss → anomaly 11/17 거짓 detect
- 신선도(MAX time)는 부분 적재를 못 잡으므로 region completeness 별도 체크 필수
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 동적 로드 — scripts/ops/ 는 sys.path 가 아니므로 module import 우회
SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "ops" / "check_collector_health.py"
)


@pytest.fixture
def hc(monkeypatch: pytest.MonkeyPatch):
    """Import healthcheck module with dummy DB env (DB 실연결 없이 함수만 로드)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    spec = importlib.util.spec_from_file_location("hc", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRegionCompleteness:
    """check_layer_completeness — 부분 적재 감지."""

    def test_full_17_regions_not_incomplete(self, hc, monkeypatch):
        """17지역 모두 들어가면 incomplete=False."""
        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_cur.fetchall.return_value = [(r,) for r in hc.SIDO_ALL]
        fake_conn.cursor.return_value = fake_cur
        monkeypatch.setattr(hc.psycopg2, "connect", lambda dsn: fake_conn)

        count, expected, is_incomplete, missing = hc.check_layer_completeness("otc")
        assert count == 17
        assert expected == 17
        assert is_incomplete is False
        assert missing == []

    def test_six_regions_missing_alerts_incident_replay(self, hc, monkeypatch):
        """2026-06-01 사고 그대로 재현 — 6지역 누락 → incomplete + missing 리스트."""
        # 사고 당시 누락된 6지역
        missing_actual = {
            "경상남도", "경상북도", "전라남도", "전라북도",
            "제주특별자치도", "충청남도",
        }
        present = hc.SIDO_ALL - missing_actual

        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_cur.fetchall.return_value = [(r,) for r in present]
        fake_conn.cursor.return_value = fake_cur
        monkeypatch.setattr(hc.psycopg2, "connect", lambda dsn: fake_conn)

        count, expected, is_incomplete, missing = hc.check_layer_completeness("otc")
        assert count == 11
        assert expected == 17
        assert is_incomplete is True
        assert set(missing) == missing_actual, (
            f"누락 지역 detection 실패: expected={missing_actual}, got={set(missing)}"
        )

    def test_zero_rows_marked_incomplete(self, hc, monkeypatch):
        """최신 주에 한 건도 없으면 incomplete=True, count=0."""
        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_cur.fetchall.return_value = []
        fake_conn.cursor.return_value = fake_cur
        monkeypatch.setattr(hc.psycopg2, "connect", lambda dsn: fake_conn)

        count, expected, is_incomplete, info = hc.check_layer_completeness("otc")
        assert count == 0
        assert is_incomplete is True
        assert "no rows" in str(info)

    def test_db_error_returns_incomplete(self, hc, monkeypatch):
        """DB 연결 실패 시 incomplete=True 로 보고 (정상으로 가리지 않음)."""
        def fake_connect(dsn):
            raise Exception("connection refused")
        monkeypatch.setattr(hc.psycopg2, "connect", fake_connect)

        count, expected, is_incomplete, info = hc.check_layer_completeness("otc")
        assert count is None
        assert is_incomplete is True
        assert "db error" in str(info)


class TestCompletenessConfig:
    """설정 회귀 방지 — 임계 17, 대상 3개 layer."""

    def test_expected_regions_is_17(self, hc):
        """한국 17 시·도 — 변경 시 인구·SIDO_ALL·collector 도 같이 갱신 필요."""
        assert hc.EXPECTED_REGIONS == 17

    def test_completeness_layers_excludes_aux(self, hc):
        """AUX(기상) 는 전국 단일값 → completeness 검사 대상 아님."""
        assert hc.COMPLETENESS_LAYERS == {"otc", "wastewater", "search"}
        assert "AUX" not in hc.COMPLETENESS_LAYERS
        assert "aux" not in hc.COMPLETENESS_LAYERS

    def test_sido_all_has_17(self, hc):
        """SIDO_ALL 상수 — 17개 정확히."""
        assert len(hc.SIDO_ALL) == 17
        # 핵심 시·도 몇 개만 sanity check
        assert "서울특별시" in hc.SIDO_ALL
        assert "제주특별자치도" in hc.SIDO_ALL
        assert "세종특별자치시" in hc.SIDO_ALL
