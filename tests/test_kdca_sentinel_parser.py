"""KDCA 표본감시 (4급) 인플루엔자 ILI CSV 파서 회귀 테스트.

회귀 방지:
- EUC-KR 디코딩 (UTF-8 으로 읽으면 한글 깨짐)
- 절기명 가드 (기생충/풍토병 등 비-ILI 파일 잘못 파싱 방지)
- KDCA 절기 정의 (시작 W36) 기반 ISO 주차 계산
- `집계 중` 토큰 skip (진행 중 절기)
- ILI ≥ 임계 → 양성 라벨 (KDCA 공식 유행 기준)
- 다년 절기 병합 시 (iso_year, iso_week) 중복 dedup
"""
from __future__ import annotations

from pathlib import Path

from pipeline.collectors import kdca_sentinel_parser as p


# ─────────────────────── 상수/임계 ────────────────────────────────────────
class TestConstants:
    def test_threshold_matches_kdca_2024_2025(self):
        """KDCA 2024-2025절기 유행 임계 = 5.8/1000."""
        assert p.ILI_EPIDEMIC_THRESHOLD == 5.8

    def test_season_start_week_is_36(self):
        """KDCA 절기 시작 = 36주차 (대략 9월 첫째 주)."""
        assert p.SEASON_START_WEEK == 36


# ─────────────────────── 절기명 가드 ──────────────────────────────────────
class TestSeasonYearGuard:
    def test_valid_season_name(self):
        assert p._season_year_from_name("2025-2026절기") == 2025
        assert p._season_year_from_name("2020-2021절기") == 2020

    def test_rejects_plain_year(self):
        """기생충 파일의 `2023` 첫 컬럼 같은 형태는 거부 — ILI 파서로 흘러가면 안 됨."""
        import pytest
        with pytest.raises(ValueError, match="절기"):
            p._season_year_from_name("2023")

    def test_rejects_empty(self):
        import pytest
        with pytest.raises(ValueError):
            p._season_year_from_name("")


# ─────────────────────── ISO 주차 계산 ────────────────────────────────────
class TestIsoWeekCalculation:
    def test_offset_zero_returns_week_36_of_start_year(self):
        """절기 시작 (offset=0) 은 시작 연도의 W36 월요일."""
        iso_y, iso_w, monday = p._iso_week_for_season_offset(2025, 0)
        assert iso_y == 2025
        assert iso_w == 36
        assert monday.isoformat() == "2025-09-01"

    def test_offset_crosses_year_boundary(self):
        """W36 + 17주 = 다음해 W1 또는 W2 영역 진입."""
        # 2025-W36 + 17주 = 2026-W1 (approx)
        iso_y, iso_w, _ = p._iso_week_for_season_offset(2025, 17)
        assert iso_y == 2026
        # W36 + 17 = 53 → 다음해 W1
        assert iso_w == 1


# ─────────────────────── CSV 파싱 ─────────────────────────────────────────
class TestParseIliCsv:
    def _write_euckr_csv(self, tmp_path: Path, content: str) -> Path:
        """헬퍼: EUC-KR 인코딩으로 CSV 쓰기."""
        path = tmp_path / "test.csv"
        path.write_bytes(content.encode("euc-kr"))
        return path

    def test_parses_single_season_row(self, tmp_path):
        path = self._write_euckr_csv(
            tmp_path,
            "2025-2026절기,6.6,6.7,8.0,9.0,12.4,집계 중,\n",
        )
        recs = p.parse_ili_csv(path)
        assert len(recs) == 5  # 집계 중 + 빈 셀 skip
        assert recs[0].season == "2025-2026절기"
        assert recs[0].season_year == 2025
        assert recs[0].week_no == 1
        assert recs[0].ili_per_1000 == 6.6
        assert recs[-1].ili_per_1000 == 12.4

    def test_skips_incomplete_token(self, tmp_path):
        """`집계 중` 셀은 silent skip — silent fail 아니라 명시적 토큰 처리."""
        path = self._write_euckr_csv(
            tmp_path,
            "2025-2026절기,6.6,집계 중,\n",
        )
        recs = p.parse_ili_csv(path)
        assert len(recs) == 1  # 6.6 만, 집계 중 skip

    def test_rejects_non_season_first_column(self, tmp_path):
        """첫 컬럼이 `2023` (절기 토큰 없음) 형태면 행 전체 skip."""
        path = self._write_euckr_csv(
            tmp_path,
            "2023,4,2.0,110,9.2\n",   # 기생충 파일 형식
        )
        recs = p.parse_ili_csv(path)
        assert recs == [], "비-ILI 행이 통과되면 라벨 정확성 깨짐"

    def test_returns_empty_for_missing_file(self, tmp_path):
        recs = p.parse_ili_csv(tmp_path / "nope.csv")
        assert recs == []

    def test_period_start_is_monday_of_iso_week(self, tmp_path):
        path = self._write_euckr_csv(
            tmp_path,
            "2025-2026절기,6.6,\n",
        )
        recs = p.parse_ili_csv(path)
        assert recs[0].period_start.weekday() == 0  # 월요일
        assert recs[0].period_start.isoformat() == "2025-09-01"


# ─────────────────────── 라벨 생성 ────────────────────────────────────────
class TestEpidemicLabel:
    def _make_rec(self, ili: float) -> p.IliRecord:
        from datetime import date
        return p.IliRecord(
            season="2025-2026절기", season_year=2025, week_no=1,
            iso_year=2025, iso_week=36,
            period_start=date(2025, 9, 1), ili_per_1000=ili,
        )

    def test_above_threshold_is_positive(self):
        labels = p.to_epidemic_label([self._make_rec(6.0)], threshold=5.8)
        assert labels[0]["label"] == 1

    def test_at_threshold_is_positive(self):
        """KDCA 공식 정의: ILI ≥ 임계 → 유행 (= 양성). 미만 = 음성."""
        labels = p.to_epidemic_label([self._make_rec(5.8)], threshold=5.8)
        assert labels[0]["label"] == 1

    def test_below_threshold_is_negative(self):
        labels = p.to_epidemic_label([self._make_rec(4.4)], threshold=5.8)
        assert labels[0]["label"] == 0

    def test_label_carries_metadata(self):
        labels = p.to_epidemic_label([self._make_rec(50.7)])
        rec = labels[0]
        assert rec["source"] == "KDCA_SENTINEL_ILI"
        assert rec["disease"] == "influenza"
        assert rec["ili_per_1000"] == 50.7
        assert rec["iso_year"] == 2025
        assert rec["iso_week"] == 36
        assert rec["period_start"] == "2025-09-01"


# ─────────────────────── 다년 병합 ────────────────────────────────────────
class TestParseAllSeasons:
    def test_dedup_when_overlapping_weeks(self, tmp_path):
        """같은 (iso_year, iso_week) 가 두 파일에 있으면 마지막 파일 우선."""
        # 2025-2026 절기 첫 주 (2025-W36) 만 한 줄씩 두 파일
        (tmp_path / "인플루엔자_a.csv").write_bytes(
            "2025-2026절기,10.0,\n".encode("euc-kr")
        )
        (tmp_path / "인플루엔자_b.csv").write_bytes(
            "2025-2026절기,20.0,\n".encode("euc-kr")
        )
        recs = p.parse_all_seasons(tmp_path)
        assert len(recs) == 1  # dedup
        assert recs[0].ili_per_1000 == 20.0  # 마지막 파일 우선

    def test_returns_empty_for_missing_dir(self, tmp_path):
        recs = p.parse_all_seasons(tmp_path / "nope")
        assert recs == []

    def test_only_matching_glob_processed(self, tmp_path):
        """`기생충*.csv` 같은 비-인플루엔자 파일은 기본 glob 에서 제외."""
        (tmp_path / "인플루엔자.csv").write_bytes(
            "2025-2026절기,6.0,\n".encode("euc-kr")
        )
        (tmp_path / "기생충.csv").write_bytes(
            "2023,4,2.0\n".encode("euc-kr")
        )
        recs = p.parse_all_seasons(tmp_path, glob="인플루엔자*.csv")
        assert len(recs) == 1
        assert recs[0].ili_per_1000 == 6.0


# ─────────────────────── 실 데이터 회귀 ────────────────────────────────────
class TestRealDataRegression:
    """사용자가 실제 다운로드한 파일에 대한 sanity check (있을 때만 실행).

    파일이 없으면 skip — CI 에서는 데이터 없으니 통과.
    """

    REAL_DIR = Path("/home/wlsdud5035/urban-immune-system/pipeline/data/kdca")

    def _find_influenza_file(self) -> Path | None:
        if not self.REAL_DIR.exists():
            return None
        import unicodedata
        for f in self.REAL_DIR.glob("*.csv"):
            if "인플루엔자" in unicodedata.normalize("NFC", f.name):
                return f
        return None

    def test_real_file_parses_to_at_least_30_weeks(self):
        """1개 절기는 보통 39주 — 30주 이하면 절기 다운로드가 비정상."""
        import pytest
        f = self._find_influenza_file()
        if not f:
            pytest.skip(f"실 데이터 없음 ({self.REAL_DIR})")
        recs = p.parse_ili_csv(f)
        assert len(recs) >= 30, f"주차 수 비정상: {len(recs)} — 파일 다시 다운로드 필요"

    def test_real_file_peak_lies_in_korea_winter_season(self):
        """한국 인플루엔자 피크는 보통 11월~다음해 1월 (ISO W44~W4) 사이."""
        import pytest
        f = self._find_influenza_file()
        if not f:
            pytest.skip("실 데이터 없음")
        recs = p.parse_ili_csv(f)
        peak = max(recs, key=lambda r: r.ili_per_1000)
        # W44 ~ W52 또는 W1 ~ W4 — 한국 인플루엔자 시즌
        in_winter = (44 <= peak.iso_week <= 52) or (1 <= peak.iso_week <= 4)
        assert in_winter, (
            f"피크 주차 비정상: {peak.iso_year}-W{peak.iso_week} "
            f"(ILI={peak.ili_per_1000}) — KDCA 절기 구조 변경 또는 파싱 오프셋 오류"
        )
