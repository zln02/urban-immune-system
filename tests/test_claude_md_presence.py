"""에이전트 CLAUDE.md 체계 존재·구조 스모크 테스트.

모든 모듈에 CLAUDE.md 가 있고, 필수 섹션 헤더를 포함하는지 확인한다.
실패 시 에이전트 시스템이 깨진 것이므로 CI 에서 막는다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MODULES = [
    "backend",
    "pipeline",
    "ml",
    "src",
    "frontend",
    "infra",
    "tests",
    "docs",
    "docs/business",
]

REQUIRED_SECTIONS = [
    "## 🎯 정체성",
    "## 💬 말 거는 법",
    "## 🛠 Skills",
    "## 🔌 MCP 연결",
    "## 🌿 GitHub 연계",
    "## 🧠 자동 메모리",
    "## 📦 상용화 기여",
    "## ✅ Definition of Done",
]

REQUIRED_BUSINESS_DOCS = [
    "docs/business/roadmap.md",
    "docs/business/isms-p-checklist.md",
    "docs/business/sales-targets.md",
    "docs/business/pricing-model.md",
    "docs/business/procurement.md",
]


@pytest.mark.parametrize("module", REQUIRED_MODULES)
def test_module_has_claude_md(module: str) -> None:
    path = REPO_ROOT / module / "CLAUDE.md"
    assert path.exists(), f"{module}/CLAUDE.md 가 없음 (에이전트 배치 누락)"


@pytest.mark.parametrize("module", REQUIRED_MODULES)
def test_module_claude_md_has_required_sections(module: str) -> None:
    text = (REPO_ROOT / module / "CLAUDE.md").read_text(encoding="utf-8")
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    assert not missing, f"{module}/CLAUDE.md 에 누락된 섹션: {missing}"


def test_root_claude_md_has_team_section() -> None:
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "팀 에이전트 시스템" in text, "루트 CLAUDE.md 에 팀 에이전트 섹션 누락"
    assert "B2G 납품 금지 규칙" in text, "루트 CLAUDE.md 에 B2G 규칙 섹션 누락"


@pytest.mark.parametrize("doc", REQUIRED_BUSINESS_DOCS)
def test_business_docs_exist(doc: str) -> None:
    path = REPO_ROOT / doc
    assert path.exists(), f"{doc} 누락 (상용화 트랙 문서 부족)"
    assert path.stat().st_size > 200, f"{doc} 내용이 너무 얇음"


def test_claude_settings_json_exists() -> None:
    path = REPO_ROOT / ".claude" / "settings.json"
    assert path.exists(), ".claude/settings.json 누락"

    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "permissions" in data
    assert "hooks" in data
    assert "SessionStart" in data["hooks"]
    assert "Stop" in data["hooks"]
