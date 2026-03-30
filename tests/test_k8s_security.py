from pathlib import Path


def test_k8s_deployments_define_container_security_context() -> None:
    root = Path(__file__).resolve().parents[1] / "infra" / "k8s"
    for name in ("backend-deployment.yaml", "pipeline-deployment.yaml", "ml-deployment.yaml"):
        content = (root / name).read_text(encoding="utf-8")
        assert "runAsNonRoot: true" in content
        assert "allowPrivilegeEscalation: false" in content
        assert "readOnlyRootFilesystem: true" in content
        assert "drop: [\"ALL\"]" in content


def test_k8s_services_define_health_probes_for_http_apps() -> None:
    root = Path(__file__).resolve().parents[1] / "infra" / "k8s"
    backend = (root / "backend-deployment.yaml").read_text(encoding="utf-8")
    ml = (root / "ml-deployment.yaml").read_text(encoding="utf-8")
    assert "livenessProbe:" in backend
    assert "readinessProbe:" in backend
    assert "livenessProbe:" in ml
    assert "readinessProbe:" in ml
