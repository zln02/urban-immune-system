# 보안 컨벤션

## 환경변수 원칙

```python
# ✅ 올바름 — pydantic Settings로 로드
from backend.app.config import settings
db_url = settings.database_url

# ❌ 금지 — 하드코딩
DB_PASSWORD = "mypassword123"

# ❌ 금지 — os.getenv 직접 사용 (검증 우회)
import os
key = os.getenv("OPENAI_API_KEY")  # Settings를 통해 접근할 것
```

## 필수 환경변수 (`.env.example` 기준)

```bash
DB_PASSWORD=             # TimescaleDB 비밀번호
NAVER_CLIENT_ID=         # 네이버 쇼핑인사이트 + DataLab 공용
NAVER_CLIENT_SECRET=
ANTHROPIC_API_KEY=       # Claude Haiku (default, RAG 리포트)
OPENAI_API_KEY=          # GPT-4o (legacy fallback)
KMA_API_KEY=             # 기상청 초단기예보
NEXT_PUBLIC_MAPBOX_TOKEN= # 프론트엔드 지도
ENVIRONMENT=development  # development | production
```

## 프로덕션 환경 강제 검증

`backend/app/config.py` Pydantic validator — **절대 제거 금지**:

```python
@model_validator(mode="after")
def validate_environment_settings(self) -> Settings:
    is_production = self.environment.lower() == "production"
    if is_production and "changeme" in self.database_url:
        raise ValueError("database_url must not use placeholder credentials in production")
    if is_production and self.ml_service_url.startswith("http://"):
        raise ValueError("ml_service_url must use https in production")
    return self
```

## API 키 보안 규칙

1. **`.env` 파일은 `.gitignore`에 포함** — `git add .env` 즉시 중단 후 히스토리 정리
2. **API 키 로그 출력 금지** — `logger.debug(f"key={key}")` 형태 포함
3. **테스트 코드에도 실제 키 금지** — `pytest-mock` 또는 `monkeypatch` 사용
4. **K8s 프로덕션**: `uis-secrets` Secret에서만 주입 (환경변수 직접 명시 금지)

## CORS 설정

```python
# backend/app/main.py
# allow_origins: 반드시 환경변수 CSV로 관리
# 개발: "http://localhost:3000,http://localhost:8501"
# 프로덕션: 도메인 명시적 지정 (와일드카드 * 금지)
CORSMiddleware(
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],   # PUT/DELETE 추가 시 리뷰 필요
    allow_credentials=False,          # 쿠키 인증 미구현 — True 변경 금지
)
```

## K8s 보안 컨텍스트

모든 Deployment에 반드시 포함 — **제거 금지**:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

## 민감 파일 — 커밋 금지

```
.env
*.pem
*.key
pipeline/data/kowas/*.pdf    # 공공 데이터지만 용량 이슈
ml/checkpoints/              # 모델 체크포인트 (용량)
```

## SQL / ORM 규칙

```python
# ✅ 올바름 — SQLAlchemy ORM 파라미터 바인딩
result = await db.execute(
    select(LayerSignal).where(LayerSignal.region == region)
)

# ❌ 금지 — f-string SQL (인젝션 위험)
query = f"SELECT * FROM layer_signals WHERE region = '{region}'"
```
