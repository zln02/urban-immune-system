# Contributing to Urban Immune System

## Development Setup

See [CLAUDE.md](./CLAUDE.md) for the canonical dev environment setup.

Quick start:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
pre-commit install
docker compose up -d
```

## Pre-commit Hooks

Already configured via `.pre-commit-config.yaml`. Runs on every commit:
1. ruff check --fix
2. ruff format
3. detect-private-key
4. trailing-whitespace
5. pytest (test failure = commit blocked)

Manual run:
```bash
pre-commit run --all-files
```

## Pull Requests

See `.github/PULL_REQUEST_TEMPLATE.md` for the checklist.

Branch strategy:
- `main`: release-ready
- `develop`: integration
- `feature/*`: feature work (branched from develop)
- `hotfix/*`: emergencies (branched from main)

## Code Style

- Python: ruff + black-compatible formatting (enforced)
- Imports: isort via ruff (stdlib → third-party → local)
- Type hints: required on all public functions (mypy --strict)
- Comments/docstrings: Korean OK, identifiers in English

## Testing

```bash
pytest                                  # full suite
pytest tests/test_<module>.py -v        # single file
pytest --cov=backend --cov-fail-under=74  # CI gate
```

Worker DoD: full pytest suite must pass before commit (see CLAUDE.md).
