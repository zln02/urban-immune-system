# urban-immune-system

> AI 기반 감염병 조기경보 시스템 (B2G 납품 목표).
> 3계층 비의료 신호 교차검증으로 임상 확진 1–3주 선행 탐지.
> **중간발표: 2026-05-07** · **최종: 2026-06 초**

## 절대 규칙

- **main 브랜치 직접 푸시 금지** — feature/* → develop → main PR 필수
- 팀원 담당 모듈 수정 시 반드시 확인 후 진행 (AGENTS.md 역할표 참조)
- API 키 절대 커밋 금지 (.gitignore 확인 필수)
- 어떤 단일 계층도 단독 경보 발령 금지 — 반드시 2개 이상 계층 교차검증 필요

## 빠른 시작

```bash
cd /home/wlsdud5035/urban-immune-system
source .venv/bin/activate
docker compose up -d                                       # Kafka + TimescaleDB + Qdrant
streamlit run src/app.py --server.port 8501               # Phase 1 대시보드
uvicorn backend.app.main:app --reload --port 8001         # FastAPI 백엔드
cd frontend && npm run dev                                 # Next.js http://localhost:3000
pytest                                                     # 테스트 (커밋 전 필수)
```

## 브랜치 전략

- `main`      : 배포 가능한 안정 버전
- `develop`   : 개발 통합 브랜치
- `feature/*` : 기능 개발 (develop에서 분기)
- `hotfix/*`  : 긴급 수정 (main에서 분기 → main + develop 머지)

## 리스크 파일 (수정 주의)

| 파일 | 이유 |
|------|------|
| `backend/app/config.py` | 프로덕션 보안 검증 로직 포함 |
| `infra/db/init.sql` | 하이퍼테이블 구조 — 재생성 시 데이터 손실 |
| `infra/k8s/*-deployment.yaml` | 보안 컨텍스트 — 제거 시 취약점 |
| `pipeline/collectors/normalization.py` | 계층 간 비교 기준 — 변경 시 전체 재보정 필요 |
| `ml/configs/model_config.yaml` | TFT 체크포인트와 버전 일치 필수 |

## 컨텍스트 인덱스

@docs/STATUS.md         — baseline 수치, Phase 로드맵, 캡스톤 성공 기준
@docs/layer_specs.md    — Layer 1/2/3/Aux + Kafka + 정규화 + 앙상블 + DB
@docs/security.md       — 환경변수, CORS, K8s, SQL/ORM
@docs/development.md    — 코드 규칙, 테스트, pre-commit
@docs/ml_specs.md       — TFT, Autoencoder, RAG 설정
@docs/architecture.md   — 전체 아키텍처
@AGENTS.md              — 팀 역할, PL 권한, 스킬 가이드
