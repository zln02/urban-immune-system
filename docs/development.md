# 개발 가이드

## 코드 규칙

### 공통

- **언어**: 주석·docstring 한국어, 코드 영어 식별자
- **타입 힌트**: public 함수 전체 필수 (`mypy --strict` 통과)
- **import 순서**: stdlib → third-party → local (ruff isort 자동 정렬)
- **로깅**: `logging.getLogger(__name__)` — `print()` 금지
- **외부 API**: 반드시 `try/except` 감싸기 (bare `except:` 금지, 구체적 예외 명시)

---

## 테스트

```bash
pytest                              # 전체
pytest tests/test_normalization.py  # 단일 파일
pytest -k "normalize"               # 키워드 필터
pytest -v --tb=short                # 기본 옵션 (pyproject.toml)
```

### 테스트 파일별 역할

| 파일 | 대상 |
|------|------|
| `test_normalization.py` | `min_max_normalize` 엣지케이스 (빈 리스트, 상수, 스케일링) |
| `test_backend_config.py` | Pydantic Settings 검증 (CSV 파싱, 프로덕션 자격증명) |
| `test_k8s_security.py` | K8s 매니페스트 보안 컨텍스트 (runAsNonRoot 등) |
| `test_config.py` | Streamlit 앱 설정 로딩 |
| `test_utils.py` | 유틸리티 함수 |
| `test_container_layout.py` | Streamlit 컴포넌트 레이아웃 |
| `test_report_generator.py` | RAG-LLM 리포트 생성 (Mock LLM 사용) |

### 테스트 작성 규칙

```python
# ✅ 외부 API는 반드시 Mock
from unittest.mock import AsyncMock, patch

@patch("pipeline.collectors.otc_collector.httpx.AsyncClient")
async def test_collect_otc_mocked(mock_client: AsyncMock) -> None:
    ...

# ✅ 실제 API 키 사용 금지
def test_config_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
    ...
```

---

## 커밋 전 자동화 (pre-commit)

```bash
# pre-commit 초기 설정 (최초 1회)
pip install pre-commit
pre-commit install   # .git/hooks/pre-commit 설치

# 수동 전체 실행
pre-commit run --all-files
```

**커밋 시 자동 실행 순서**:
1. `ruff check --fix` — 린트 + 자동 수정
2. `ruff format` — 코드 포맷
3. `detect-private-key` — API 키 하드코딩 차단
4. `trailing-whitespace` / `end-of-file-fixer` — 공백 정리
5. `pytest` — **테스트 실패 시 커밋 중단**

> **테스트 실패 = 커밋 불가**. `--no-verify` 우회는 긴급 핫픽스 외 금지.
