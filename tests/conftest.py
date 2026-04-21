"""pytest 공통 fixture.

모든 테스트가 공유하는 REPO_ROOT, read_claude_md 등을 여기서 단일 정의.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """프로젝트 루트 경로 (세션 단위 캐시)."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def claude_md_readers():
    """모듈명 → CLAUDE.md 텍스트 매핑 (한 번 읽어 재사용)."""
    modules = [
        "backend", "pipeline", "ml", "src", "frontend",
        "infra", "tests", "docs", "docs/business",
    ]
    return {m: (REPO_ROOT / m / "CLAUDE.md").read_text(encoding="utf-8") for m in modules}
