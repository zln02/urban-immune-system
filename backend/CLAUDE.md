# backend/ — 이경준

## 담당자
이경준 (Backend) · 박진영 PL 권한으로 직접 수정 가능

## 기술 스택
- **FastAPI** + Uvicorn (ASGI)
- SQLAlchemy 2.x async + asyncpg (TimescaleDB)
- Pydantic v2 Settings (`backend/app/config.py`)
- taskiq + Kafka (백그라운드 잡)
- Anthropic Claude Haiku (RAG 리포트, SSE)
- httpx (외부 API)

## 포트 / 엔드포인트 베이스
- 개발: `uvicorn backend.app.main:app --reload --port 8001`
- frontend `NEXT_PUBLIC_API_BASE_URL=http://localhost:8001` 와 일치 필수

## 라우터 (현재 17개 엔드포인트)
```
backend/app/api/
├── signals.py       /api/v1/signals/* (latest, timeseries, layer별)
├── predictions.py   /api/v1/predictions/* (XGBoost·TFT 추론 호출)
├── alerts.py        /api/v1/alerts/* (current, stream SSE, report-pdf)
└── chat.py          /api/v1/chat/* (SSE 챗봇)
```

## ML 서비스 호출
- `backend/app/services/ml_client.py` — `ml_service_url` 로 ml/serve.py(:8000 별도 프로세스) 호출
- 프로덕션: `ml_service_url` 은 https 강제 (`config.py` validator)

## 환경변수 (`.env`, Pydantic Settings)
```bash
DATABASE_URL=postgresql+asyncpg://uis:CHANGEME@localhost:5432/uis
ML_SERVICE_URL=http://localhost:8000        # 프로덕션 https 강제
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8501
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
NAVER_CLIENT_ID=... / NAVER_CLIENT_SECRET=...
ENVIRONMENT=development
```

## 절대 규칙
- `os.getenv` 직접 호출 금지 → 반드시 `from backend.app.config import settings`
- f-string SQL 금지 → SQLAlchemy 파라미터 바인딩
- CORS `allow_origins=*` 금지, `allow_credentials=False` 유지
- `database_url` 에 `changeme` placeholder 가 production 에서 통과되면 startup 실패 (validator)

## 라우터 추가 시
1. `backend/app/api/<name>.py` 생성 + APIRouter
2. `backend/app/main.py` 에 `app.include_router(...)` 등록
3. `tests/integration/test_<name>.py` 추가 (anthropic·kafka mock)
4. CI `backend-test` 잡 통과 확인

## 테스트
```bash
pytest backend/tests/                      # 단위
pytest tests/integration/                  # 통합 (asyncpg 필요)
pytest --cov=backend --cov-fail-under=35   # CI 게이트
```
- 외부 API mock: `unittest.mock.patch` 또는 `pytest-httpx`
- Anthropic SSE 통합 테스트는 CI 환경 한정 500 skip (`a64ee5e` 참조)

## 권장 스킬
- `/harden` 에러 핸들링·엣지 케이스
- `/security-review` 라우터 변경 시
