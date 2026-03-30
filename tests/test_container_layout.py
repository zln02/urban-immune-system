from pathlib import Path


def test_pipeline_dockerfile_uses_package_layout() -> None:
    dockerfile = (Path(__file__).resolve().parents[1] / "pipeline" / "Dockerfile").read_text(encoding="utf-8")
    assert 'COPY . ./pipeline/' in dockerfile
    assert 'python", "-m", "pipeline.collectors.scheduler"' in dockerfile


def test_ml_dockerfile_points_to_existing_service_module() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "ml" / "Dockerfile").read_text(encoding="utf-8")
    assert 'uvicorn", "ml.serve:app"' in dockerfile
    assert (root / "ml" / "serve.py").exists()
