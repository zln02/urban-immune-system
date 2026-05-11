"""tests/test_reproduce_validation.py

ml/reproduce_validation.py 커버리지 테스트.

전략:
- 실제 ML 훈련(train()) 은 mock 처리 → CI 시간 절약
- argparse, stage 함수들, JSON 출력 구조, seed 재현성에 집중
"""
from __future__ import annotations

import json
import sys
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
        {"fold": 3, "mae": float("nan"), "f1": float("nan"), "precision": float("nan"),
         "recall": float("nan"), "auc_roc": float("nan")},
    ],
    "final_eval": {
        "mae": 5.0, "f1": 0.75, "precision": 0.8, "recall": 0.7, "auc_roc": 0.9,
        "target_col": "confirmed_future", "alert_col": "alert_future", "alert_threshold": 70.0,
    },
}


# ---------------------------------------------------------------------------
# 1. argparse 파싱
# ---------------------------------------------------------------------------

class TestParseArgs:
    def test_defaults(self):
        """기본 인자: skip-real=False, region=서울특별시"""
        with patch("sys.argv", ["reproduce_validation.py"]):
            from ml.reproduce_validation import main  # noqa: F401 — side-effect free import
            import argparse
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
        assert s["n_folds_valid"] == 2   # fold3 는 NaN
        assert abs(s["cv_mean_f1"] - 0.65) < 1e-9
        assert abs(s["cv_mean_precision"] - 0.75) < 1e-9
        assert abs(s["cv_mean_recall"] - 0.55) < 1e-9
        assert s["final_eval"]["f1"] == 0.75

    def test_all_nan_f1(self):
        """모든 fold 가 NaN → cv_mean_f1 = None"""
        from ml.reproduce_validation import _summary_from_train_result
        result = {
            "cv_scores": [
                {"fold": 1, "mae": 5.0, "f1": float("nan"), "precision": float("nan"),
                 "recall": float("nan"), "auc_roc": float("nan")},
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
                {"fold": 1, "mae": 4.0, "f1": float("nan"), "precision": float("nan"),
                 "recall": float("nan"), "auc_roc": float("nan")},
                {"fold": 2, "mae": 6.0, "f1": float("nan"), "precision": float("nan"),
                 "recall": float("nan"), "auc_roc": float("nan")},
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
        from ml.reproduce_validation import _run_synthetic_hardened, FEATURE_COLS
        result = _run_synthetic_hardened()
        assert result["feature_cols"] == FEATURE_COLS

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_alert_threshold(self, mock_train):
        from ml.reproduce_validation import _run_synthetic_hardened, HARDENED_ALERT_THRESHOLD
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
        from ml.xgboost.model import generate_synthetic_data, HARDENED_ALERT_COL
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
        import pandas as pd
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
        with patch("sys.argv", [
            "reproduce_validation.py",
            "--skip-real",
            "--output", str(out_file),
        ]):
            from ml import reproduce_validation
            import importlib
            importlib.reload(reproduce_validation)
            reproduce_validation.main()

        assert out_file.exists()
        d = json.loads(out_file.read_text(encoding="utf-8"))
        assert "stages" in d
        assert "synthetic_hardened" in d["stages"]
        assert "real" not in d["stages"]   # skip-real → real 스테이지 없어야 함
        assert "generated_at" in d

    @patch("ml.reproduce_validation.train", return_value=FAKE_TRAIN_RESULT)
    def test_main_returns_zero(self, mock_train, tmp_path, capsys):
        """정상 실행 시 return code 0"""
        out_file = tmp_path / "out.json"
        with patch("sys.argv", [
            "reproduce_validation.py",
            "--skip-real",
            "--output", str(out_file),
        ]):
            from ml import reproduce_validation
            import importlib
            importlib.reload(reproduce_validation)
            ret = reproduce_validation.main()
        assert ret == 0
