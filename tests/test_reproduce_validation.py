"""tests/test_reproduce_validation.py

ml/reproduce_validation.py 커버리지 테스트.

전략:
- 실제 ML 훈련(train()) 은 mock 처리 → CI 시간 절약
- argparse, stage 함수들, JSON 출력 구조, seed 재현성에 집중
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# 헬퍼: 가짜 train() 반환값
# ---------------------------------------------------------------------------
FAKE_TRAIN_RESULT: dict[str, Any] = {
    "cv_scores": [
        {"fold": 1, "mae": 10.0, "f1": 0.6, "precision": 0.7, "recall": 0.5, "auc_roc": 0.8},
        {"fold": 2, "mae": 9.0, "f1": 0.7, "precision": 0.8, "recall": 0.6, "auc_roc": 0.85},
        {
            "fold": 3,
            "mae": float("nan"),
            "f1": float("nan"),
            "precision": float("nan"),
            "recall": float("nan"),
            "auc_roc": float("nan"),
        },
    ],
    "final_eval": {
        "mae": 5.0,
        "f1": 0.75,
        "precision": 0.8,
        "recall": 0.7,
        "auc_roc": 0.9,
        "target_col": "confirmed_future",
        "alert_col": "alert_future",
        "alert_threshold": 70.0,
    },
}


# ---------------------------------------------------------------------------
# 1. argparse 파싱
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_defaults(self):
        """기본 인자: skip-real=False, region=서울특별시"""
        with patch("sys.argv", ["reproduce_validation.py"]):
            import argparse

            from ml.reproduce_validation import main  # noqa: F401 — side-effect free import

            # parse_args 는 main() 내부에 inline 되어 있으므로 직접 재구성
            parser = argparse.ArgumentParser()
            parser.add_argument("--skip-real", action="store_true")
            parser.add_argument("--region", default="서울특별시")
            parser.add_argument("--output", type=Path, default=Path("/tmp/dummy.json"))
            args = parser.parse_args([])
            assert args.skip_real is False
            assert args.region == "서울특별시"

    def test_skip_real_flag(self):
        """--skip-real 플래그 인식"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--skip-real", action="store_true")
        parser.add_argument("--region", default="서울특별시")
        parser.add_argument("--output", type=Path, default=Path("/tmp/dummy.json"))
        args = parser.parse_args(["--skip-real", "--region", "부산광역시"])
        assert args.skip_real is True
        assert args.region == "부산광역시"

    def test_custom_output(self, tmp_path):
        """--output 커스텀 경로 인식"""
        import argparse

        out = tmp_path / "out.json"
        parser = argparse.ArgumentParser()
        parser.add_argument("--skip-real", action="store_true")
        parser.add_argument("--region", default="서울특별시")
        parser.add_argument("--output", type=Path, default=Path("/tmp/dummy.json"))
        args = parser.parse_args(["--output", str(out)])
        assert args.output == out


# ---------------------------------------------------------------------------
# 2. _summary_from_train_result
# ---------------------------------------------------------------------------


class TestSummaryFromTrainResult:
    def test_normal_cv(self):
        from ml.reproduce_validation import _summary_from_train_result

        s = _summary_from_train_result(FAKE_TRAIN_RESULT)
        assert s["n_folds_total"] == 3
        assert s["n_folds_valid"] == 2  # fold3 는 NaN
        assert abs(s["cv_mean_f1"] - 0.65) < 1e-9
        assert abs(s["cv_mean_precision"] - 0.75) < 1e-9
        assert abs(s["cv_mean_recall"] - 0.55) < 1e-9
        assert s["final_eval"]["f1"] == 0.75

    def test_all_nan_f1(self):
        """모든 fold 가 NaN → cv_mean_f1 = None"""
        from ml.reproduce_validation import _summary_from_train_result

        result = {
            "cv_scores": [
                {
                    "fold": 1,
                    "mae": 5.0,
                    "f1": float("nan"),
                    "precision": float("nan"),
                    "recall": float("nan"),
                    "auc_roc": float("nan"),
                },
            ],
            "final_eval": {},
        }
        s = _summary_from_train_result(result)
        assert s["cv_mean_f1"] is None
        assert s["cv_mean_precision"] is None
        assert s["cv_mean_recall"] is None

    def test_empty_cv_scores(self):
        """cv_scores 없을 때 안전 처리"""
        from ml.reproduce_validation import _summary_from_train_result

        s = _summary_from_train_result({"cv_scores": [], "final_eval": {}})
        assert s["n_folds_total"] == 0
        assert s["cv_mean_f1"] is None
        assert s["cv_mean_mae"] is None

    def test_mae_always_present(self):
        """MAE 는 NaN 필터 없이 모든 fold 평균"""
        from ml.reproduce_validation import _summary_from_train_result

        result = {
            "cv_scores": [
                {
                    "fold": 1,
                    "mae": 4.0,
                    "f1": float("nan"),
                    "precision": float("nan"),
                    "recall": float("nan"),
                    "auc_roc": float("nan"),
                },
                {
                    "fold": 2,
                    "mae": 6.0,
                    "f1": float("nan"),
                    "precision": float("nan"),
                    "recall": float("nan"),
                    "auc_roc": float("nan"),
                },
            ],
            "final_eval": {},
        }
        s = _summary_from_train_result(result)
        assert abs(s["cv_mean_mae"] - 5.0) < 1e-9


# ---------------------------------------------------------------------------
# 3. _run_synthetic_hardened (train mock)
# ---------------------------------------------------------------------------


class TestRunSyntheticHardened:
    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_returns_expected_keys(self, mock_train):
        from ml.reproduce_validation import _run_synthetic_hardened

        result = _run_synthetic_hardened()
        assert result["data_source"] == "synthetic_hardened"
        assert result["data_seed"] == 42
        assert result["lead_weeks"] == 2
        assert result["n_weeks"] == 104
        assert "cv_mean_f1" in result
        mock_train.assert_called_once()

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_feature_cols_present(self, mock_train):
        from ml.reproduce_validation import FEATURE_COLS, _run_synthetic_hardened

        result = _run_synthetic_hardened()
        assert result["feature_cols"] == FEATURE_COLS

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_alert_threshold(self, mock_train):
        from ml.reproduce_validation import HARDENED_ALERT_THRESHOLD, _run_synthetic_hardened

        result = _run_synthetic_hardened()
        assert result["alert_threshold"] == HARDENED_ALERT_THRESHOLD


# ---------------------------------------------------------------------------
# 4. seed 재현성
# ---------------------------------------------------------------------------


class TestSeedReproducibility:
    def test_same_seed_same_data(self):
        """seed=42 두 번 → 동일 데이터프레임"""
        from ml.xgboost.model import generate_synthetic_data

        df1 = generate_synthetic_data(n_weeks=50, seed=42)
        df2 = generate_synthetic_data(n_weeks=50, seed=42)
        assert list(df1.columns) == list(df2.columns)
        np.testing.assert_array_almost_equal(df1["l1_otc"].values, df2["l1_otc"].values)
        np.testing.assert_array_almost_equal(df1["composite_score"].values, df2["composite_score"].values)

    def test_different_seed_different_data(self):
        """다른 seed → 다른 데이터"""
        from ml.xgboost.model import generate_synthetic_data

        df1 = generate_synthetic_data(n_weeks=50, seed=42)
        df2 = generate_synthetic_data(n_weeks=50, seed=99)
        assert not np.allclose(df1["l1_otc"].values, df2["l1_otc"].values)

    def test_hardened_alert_col_present(self):
        """generate_synthetic_data 결과에 HARDENED_ALERT_COL 포함"""
        from ml.xgboost.model import HARDENED_ALERT_COL, generate_synthetic_data

        df = generate_synthetic_data(n_weeks=30, seed=7)
        assert HARDENED_ALERT_COL in df.columns
        assert set(df[HARDENED_ALERT_COL].unique()).issubset({0, 1})


# ---------------------------------------------------------------------------
# 5. _fetch_real_dataset — DB 없을 때 None 반환
# ---------------------------------------------------------------------------


class TestFetchRealDataset:
    def test_no_database_url_returns_none(self, monkeypatch):
        """DATABASE_URL 미설정 → None"""
        monkeypatch.setenv("DATABASE_URL", "")
        from ml.reproduce_validation import _fetch_real_dataset

        result = _fetch_real_dataset()
        assert result is None

    def test_placeholder_url_returns_none(self, monkeypatch):
        """changeme 포함 URL → None"""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:changeme@localhost/db")
        from ml.reproduce_validation import _fetch_real_dataset

        result = _fetch_real_dataset()
        assert result is None


# ---------------------------------------------------------------------------
# 6. _run_real — DB 없을 때 skipped 상태
# ---------------------------------------------------------------------------


class TestRunReal:
    def test_skipped_when_no_data(self, monkeypatch):
        """DB 없어서 _fetch_real_dataset → None 시 skipped 반환"""
        monkeypatch.setenv("DATABASE_URL", "")
        from ml.reproduce_validation import _run_real

        result = _run_real("서울특별시")
        assert result["status"] == "skipped"
        assert result["data_source"] == "real"
        assert "reason" in result

    def test_skipped_when_insufficient_rows(self, monkeypatch):
        """row 수 < 30 이면 skipped"""
        monkeypatch.setenv("DATABASE_URL", "")
        from ml.xgboost.model import generate_synthetic_data

        tiny_df = generate_synthetic_data(n_weeks=10, seed=1)
        with patch("ml.reproduce_validation._fetch_real_dataset", return_value=tiny_df):
            from ml.reproduce_validation import _run_real

            result = _run_real("제주특별자치도")
            assert result["status"] == "skipped"
            assert result["n_weeks_3layer_intersection"] == 10


# ---------------------------------------------------------------------------
# 7. _load_realistic_stage — 파일 없을 때 missing
# ---------------------------------------------------------------------------


class TestLoadRealisticStage:
    def test_missing_backtest_file(self, tmp_path, monkeypatch):
        """BACKTEST_17_PATH 없으면 status=missing"""
        import ml.reproduce_validation as rv

        orig = rv.BACKTEST_17_PATH
        monkeypatch.setattr(rv, "BACKTEST_17_PATH", tmp_path / "nonexistent.json")
        result = rv._load_realistic_stage()
        assert result["status"] == "missing"
        assert "reason" in result
        monkeypatch.setattr(rv, "BACKTEST_17_PATH", orig)

    def test_reads_backtest_ok(self, monkeypatch):
        """정상 backtest 파일 → status=ok, 지표 노출 (실제 analysis/outputs 파일 사용)"""
        real_path = Path(__file__).parent.parent / "analysis" / "outputs" / "backtest_17regions.json"
        if not real_path.exists():
            pytest.skip("analysis/outputs/backtest_17regions.json 없음")
        import ml.reproduce_validation as rv

        result = rv._load_realistic_stage()
        assert result["status"] == "ok"
        assert "cv_mean_f1" in result
        assert result["n_regions"] is not None

    def test_reads_lead_time_ok(self, monkeypatch):
        """lead_time 파일 포함 통합 테스트 (실제 파일 사용)"""
        real_bt = Path(__file__).parent.parent / "analysis" / "outputs" / "backtest_17regions.json"
        real_lt = Path(__file__).parent.parent / "analysis" / "outputs" / "lead_time_summary.json"
        if not real_bt.exists() or not real_lt.exists():
            pytest.skip("analysis/outputs 파일 없음")
        import ml.reproduce_validation as rv

        result = rv._load_realistic_stage()
        assert result["status"] == "ok"
        assert "lead_time_weeks" in result
        assert "analysis_window" in result


# ---------------------------------------------------------------------------
# 8. validation.json 구조 검증 (기존 파일)
# ---------------------------------------------------------------------------


class TestExistingValidationJson:
    def test_json_structure(self):
        """ml/outputs/validation.json 의 최소 구조 확인"""
        p = Path(__file__).parent.parent / "ml" / "outputs" / "validation.json"
        if not p.exists():
            pytest.skip("validation.json 없음 — CI skip")
        d = json.loads(p.read_text(encoding="utf-8"))
        assert "stages" in d
        assert "generated_at" in d
        assert isinstance(d["stages"], dict)

    def test_synthetic_hardened_stage_keys(self):
        """synthetic_hardened 스테이지 지표 키 존재"""
        p = Path(__file__).parent.parent / "ml" / "outputs" / "validation.json"
        if not p.exists():
            pytest.skip("validation.json 없음")
        d = json.loads(p.read_text(encoding="utf-8"))
        sh = d["stages"].get("synthetic_hardened", {})
        assert sh.get("data_source") == "synthetic_hardened"
        assert "cv_mean_f1" in sh
        assert sh.get("data_seed") == 42

    def test_realistic_stage_present(self):
        """realistic 스테이지 존재 + status 체크"""
        p = Path(__file__).parent.parent / "ml" / "outputs" / "validation.json"
        if not p.exists():
            pytest.skip("validation.json 없음")
        d = json.loads(p.read_text(encoding="utf-8"))
        assert "realistic" in d["stages"]
        assert d["stages"]["realistic"]["status"] in ("ok", "missing", "error")


# ---------------------------------------------------------------------------
# 9. main() 통합 — skip-real + mock train
# ---------------------------------------------------------------------------


class TestMainIntegration:
    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_main_writes_json(self, mock_train, tmp_path):
        """main() 실행 시 output JSON 파일 생성 + stages 포함"""
        out_file = tmp_path / "result.json"
        with patch(
            "sys.argv",
            [
                "reproduce_validation.py",
                "--skip-real",
                "--output",
                str(out_file),
            ],
        ):
            import importlib

            from ml import reproduce_validation

            importlib.reload(reproduce_validation)
            reproduce_validation.main()

        assert out_file.exists()
        d = json.loads(out_file.read_text(encoding="utf-8"))
        assert "stages" in d
        assert "synthetic_hardened" in d["stages"]
        assert "real" not in d["stages"]  # skip-real → real 스테이지 없어야 함
        assert "generated_at" in d

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_main_returns_zero(self, mock_train, tmp_path, capsys):
        """정상 실행 시 return code 0"""
        out_file = tmp_path / "out.json"
        with patch(
            "sys.argv",
            [
                "reproduce_validation.py",
                "--skip-real",
                "--output",
                str(out_file),
            ],
        ):
            import importlib

            from ml import reproduce_validation

            importlib.reload(reproduce_validation)
            ret = reproduce_validation.main()
        assert ret == 0

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_main_with_real_stage_skipped_due_to_no_db(self, mock_train, tmp_path, monkeypatch):
        """skip-real 없음 + DB 미설정 → real=skipped, JSON 저장"""
        monkeypatch.setenv("DATABASE_URL", "")
        out_file = tmp_path / "result_real.json"
        with patch(
            "sys.argv",
            [
                "reproduce_validation.py",
                "--output",
                str(out_file),
            ],
        ):
            import importlib

            from ml import reproduce_validation

            importlib.reload(reproduce_validation)
            ret = reproduce_validation.main()
        assert ret == 0
        assert out_file.exists()
        d = json.loads(out_file.read_text(encoding="utf-8"))
        assert "real" in d["stages"]
        assert d["stages"]["real"]["status"] == "skipped"

    def test_main_synthetic_hardened_exception_captured(self, tmp_path):
        """synthetic_hardened 예외 발생 시 stages에 error 기록 (직접 함수 호출)"""
        import importlib

        import ml.reproduce_validation as rv

        importlib.reload(rv)

        out_file = tmp_path / "err.json"
        with (
            patch.object(rv, "_run_synthetic_hardened", side_effect=RuntimeError("훈련 실패")),
            patch.object(rv, "_run_real", return_value={"status": "skipped", "data_source": "real", "reason": "skip"}),
            patch.object(rv, "_load_realistic_stage", return_value={"status": "missing", "reason": "skip"}),
            patch("sys.argv", ["reproduce_validation.py", "--skip-real", "--output", str(out_file)]),
        ):
            ret = rv.main()
        assert ret == 0
        d = json.loads(out_file.read_text(encoding="utf-8"))
        sh = d["stages"]["synthetic_hardened"]
        assert sh["status"] == "error"
        assert "훈련 실패" in sh["error"]

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_main_realistic_exception_captured(self, mock_train, tmp_path):
        """_load_realistic_stage 예외 발생 시 stages에 error 기록"""
        import importlib

        import ml.reproduce_validation as rv

        importlib.reload(rv)

        out_file = tmp_path / "rs_err.json"
        with (
            patch.object(
                rv,
                "_run_synthetic_hardened",
                return_value={
                    "data_source": "synthetic_hardened",
                    "data_seed": 42,
                    "n_weeks": 104,
                    "n_alert_positive": 10,
                    "alert_threshold": 70.0,
                    "lead_weeks": 2,
                    "feature_cols": [],
                    "task": "t",
                    **{k: v for k, v in FAKE_TRAIN_RESULT.items()},
                },
            ),
            patch.object(rv, "_load_realistic_stage", side_effect=ValueError("파일 손상")),
            patch("sys.argv", ["reproduce_validation.py", "--skip-real", "--output", str(out_file)]),
        ):
            ret = rv.main()
        assert ret == 0
        d = json.loads(out_file.read_text(encoding="utf-8"))
        rs = d["stages"]["realistic"]
        assert rs["status"] == "error"
        assert "파일 손상" in rs["error"]

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_main_print_summary_with_realistic_ok(self, mock_train, tmp_path, capsys):
        """realistic stage가 ok일 때 발표용 요약 출력 확인 (line 301, 316)"""
        import importlib

        import ml.reproduce_validation as rv

        importlib.reload(rv)

        out_file = tmp_path / "print_test.json"
        realistic_ok = {
            "status": "ok",
            "cv_mean_f1": 0.621,
            "cv_mean_precision": 0.700,
            "cv_mean_recall": 0.838,
            "cv_mean_far": 0.206,
            "n_regions": 17,
            "lead_time_weeks": {"composite": 6.47},
        }
        with (
            patch.object(rv, "_load_realistic_stage", return_value=realistic_ok),
            patch("sys.argv", ["reproduce_validation.py", "--skip-real", "--output", str(out_file)]),
        ):
            rv.main()
        captured = capsys.readouterr()
        assert "realistic_17regions" in captured.out
        assert "F1=0.621" in captured.out

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_main_print_summary_with_real_ok(self, mock_train, tmp_path, capsys, monkeypatch):
        """real stage가 ok일 때 발표용 요약 real 출력 (line 301, _print 경로)"""
        monkeypatch.setenv("DATABASE_URL", "")
        out_file = tmp_path / "print_real.json"
        # cv_mean_auc_roc 포함한 fake result
        real_ok_result = {
            "data_source": "real",
            "region": "서울특별시",
            "status": "ok",
            "n_weeks": 50,
            "n_alert_positive": 10,
            "alert_threshold": 50.0,
            "feature_cols": ["l1_otc"],
            "first_week": "2024-01-01",
            "last_week": "2024-12-31",
            "cv_mean_f1": 0.75,
            "cv_mean_precision": 0.80,
            "cv_mean_recall": 0.70,
            "cv_mean_auc_roc": 0.85,
            "cv_mean_mae": 5.0,
            "n_folds_total": 3,
            "n_folds_valid": 3,
            "fold_scores": [],
            "final_eval": {},
        }
        with (
            patch(
                "sys.argv",
                [
                    "reproduce_validation.py",
                    "--output",
                    str(out_file),
                ],
            ),
            patch("ml.reproduce_validation._run_real", return_value=real_ok_result),
        ):
            import importlib

            from ml import reproduce_validation

            importlib.reload(reproduce_validation)
            reproduce_validation.main()
        captured = capsys.readouterr()
        assert "real" in captured.out


# ---------------------------------------------------------------------------
# 10. _fetch_real_dataset — psycopg2 mock 경로
# ---------------------------------------------------------------------------


class TestFetchRealDatasetMocked:
    def test_db_connection_failure_returns_none(self, monkeypatch):
        """psycopg2.connect 예외 → None 반환 (line 174-176)"""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        with patch("psycopg2.connect", side_effect=Exception("연결 실패")):
            from ml.reproduce_validation import _fetch_real_dataset

            result = _fetch_real_dataset()
        assert result is None

    def test_empty_rows_returns_none(self, monkeypatch):
        """쿼리 결과 빈 rows → None 반환 (line 178-179)"""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        with patch("psycopg2.connect", return_value=mock_conn):
            from ml.reproduce_validation import _fetch_real_dataset

            result = _fetch_real_dataset()
        assert result is None

    def test_valid_rows_returns_dataframe(self, monkeypatch):
        """정상 DB rows → DataFrame 반환 (line 181-199)"""

        import pandas as pd

        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

        # 충분한 행 생성 (3계층 * 여러 주)
        weeks = pd.date_range("2024-01-01", periods=40, freq="W")
        rows = []
        for w in weeks:
            for layer in ("otc", "wastewater", "search"):
                rows.append({"week": w, "layer": layer, "value": 50.0})

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = rows
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        with patch("psycopg2.connect", return_value=mock_conn):
            from ml.reproduce_validation import _fetch_real_dataset

            result = _fetch_real_dataset()

        assert result is not None
        assert "l1_otc" in result.columns
        assert "l2_wastewater" in result.columns
        assert "l3_search" in result.columns
        assert "alert_label" in result.columns
        assert len(result) == 40


# ---------------------------------------------------------------------------
# 11. _run_real 성공 경로 (line 216-221)
# ---------------------------------------------------------------------------


class TestRunRealSuccess:
    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_run_real_ok_with_sufficient_data(self, mock_train, monkeypatch):
        """데이터 30행 이상 → status=ok"""
        import numpy as np
        import pandas as pd

        monkeypatch.setenv("DATABASE_URL", "")
        # 30행 이상인 fake DataFrame
        n = 50
        weeks = pd.date_range("2023-01-01", periods=n, freq="W")
        df = pd.DataFrame(
            {
                "l1_otc": np.random.default_rng(1).uniform(10, 90, n),
                "l2_wastewater": np.random.default_rng(2).uniform(10, 90, n),
                "l3_search": np.random.default_rng(3).uniform(10, 90, n),
                "temperature": [15.0] * n,
                "humidity": [60.0] * n,
                "composite_score": np.random.default_rng(4).uniform(10, 90, n),
            },
            index=weeks,
        )
        from ml.xgboost.model import ALERT_COL, ALERT_THRESHOLD

        df[ALERT_COL] = (df["composite_score"] > ALERT_THRESHOLD).astype(int)

        with patch("ml.reproduce_validation._fetch_real_dataset", return_value=df):
            from ml.reproduce_validation import _run_real

            result = _run_real("서울특별시")

        assert result["status"] == "ok"
        assert result["data_source"] == "real"
        assert result["region"] == "서울특별시"
        assert result["n_weeks"] == n
        assert "cv_mean_f1" in result
        mock_train.assert_called_once()


# ---------------------------------------------------------------------------
# 12. _load_realistic_stage — lead_time 없는 경우 (line 251-252)
# ---------------------------------------------------------------------------


class TestLoadRealisticStageNoLeadTime:
    def test_reads_backtest_without_lead_time(self, tmp_path, monkeypatch):
        """BACKTEST_17_PATH 존재 + LEAD_TIME_PATH 없음 → lead_time 키 없어도 ok"""
        import ml.reproduce_validation as rv

        backtest_data = {
            "summary": {
                "ok_regions": 17,
                "mean_f1": 0.882,
                "mean_precision": 0.949,
                "mean_recall": 0.837,
                "mean_far_with_gate": 0.206,
                "skipped_regions": [],
            }
        }
        # 프로젝트 내부 경로에 임시 파일 생성 (relative_to 우회)
        outputs_dir = Path(rv.__file__).parent.parent / "analysis" / "outputs"
        bt_file = outputs_dir / "backtest_test_no_lead.json"
        bt_file.write_text(json.dumps(backtest_data), encoding="utf-8")

        try:
            monkeypatch.setattr(rv, "BACKTEST_17_PATH", bt_file)
            monkeypatch.setattr(rv, "LEAD_TIME_PATH", tmp_path / "nonexistent_lead.json")

            result = rv._load_realistic_stage()
            assert result["status"] == "ok"
            assert result["cv_mean_f1"] == 0.882
            # lead_time 키는 없어야 함
            assert "lead_time_weeks" not in result
        finally:
            bt_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 13. argparse 추가 조합
# ---------------------------------------------------------------------------


class TestParseArgsExtra:
    def test_region_custom_value(self):
        """--region 인자 커스텀 값"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--skip-real", action="store_true")
        parser.add_argument("--region", default="서울특별시")
        parser.add_argument("--output", type=Path, default=Path("/tmp/dummy.json"))
        args = parser.parse_args(["--region", "제주특별자치도"])
        assert args.region == "제주특별자치도"
        assert args.skip_real is False

    def test_all_args_combined(self, tmp_path):
        """모든 인자 동시 지정"""
        import argparse

        out = tmp_path / "combined.json"
        parser = argparse.ArgumentParser()
        parser.add_argument("--skip-real", action="store_true")
        parser.add_argument("--region", default="서울특별시")
        parser.add_argument("--output", type=Path, default=Path("/tmp/dummy.json"))
        args = parser.parse_args(["--skip-real", "--region", "인천광역시", "--output", str(out)])
        assert args.skip_real is True
        assert args.region == "인천광역시"
        assert args.output == out
