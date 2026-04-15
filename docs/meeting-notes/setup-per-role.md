# 팀원별 환경 세팅 CLI 가이드

서버: **GCP e2-standard-2 (uis-capstone, 34.64.124.90)**, 타임존 KST, Python 3.11.

## 공통 단계 (전원)

```bash
# 1. SSH 접속 (각자 공개키 박정빈에게 공유 → wlsdud5035 authorized_keys 추가)
ssh wlsdud5035@34.64.124.90

# 2. 프로젝트 이동
cd ~/urban-immune-system

# 3. 최신 동기화
git fetch origin
git checkout develop
git pull origin develop

# 4. venv 활성화 (이미 생성됨)
source .venv/bin/activate
python --version   # 3.11.2

# 5. 자기 feature 브랜치
git switch -c feature/<이니셜>-<작업명> origin/develop
# 예: git switch -c feature/ljn-api-auth    (이경준)
#     git switch -c feature/nyk-dashboard   (김나영)

# 6. 자기 모듈로 이동 + Claude Code 기동
cd <모듈>       # backend/ pipeline/ ml/ src/ frontend/ infra/ tests/
claude          # 배지 출력: "👤 담당: ..."
```

## 🧑 박진영 (PM / ML Lead) — `ml/`, `docs/`

```bash
cd ~/urban-immune-system/ml
claude

# Jupyter Lab (노트북 작업용)
.venv/bin/jupyter lab --ip=0.0.0.0 --port=8888 --no-browser

# 실험 추적 (권장: W&B 무료 플랜)
export WANDB_API_KEY=...
python ml/tft/train.py

# 성능 측정 노트북
jupyter nbconvert --execute analysis/notebooks/performance_measurement.ipynb
```

**이번 주 주 작업**: P0 수치 정직성 복구, P1 멀티 시즌 검증.

---

## 🧑 이경준 (Backend) — `backend/`

```bash
cd ~/urban-immune-system/backend
claude

# FastAPI 개발 서버
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# DB 연결 확인 (Docker 컴포즈가 이미 떠 있어야)
psql -U uis_user -d urban_immune -h localhost

# 라우터별 테스트
curl http://localhost:8000/signals/latest?region=강남구
curl http://localhost:8000/docs    # Swagger UI
```

**이번 주 주 작업**: `/alerts/generate` 실로직, JWT 인증, 감사 로그 미들웨어.

---

## 🧑 이우형 (Data Engineer) — `pipeline/`

```bash
cd ~/urban-immune-system/pipeline
claude

# Docker 스택 확인
sudo docker compose ps

# Kafka UI (브라우저: http://34.64.124.90:8080)

# 개별 수집기 테스트
python -m pipeline.collectors.otc_collector
python -m pipeline.collectors.search_collector

# 스케줄러
python -m pipeline.collectors.scheduler

# Prefect 전환 시 (이번 주 스파이크)
pip install prefect
prefect server start --host 0.0.0.0
```

**이번 주 주 작업**: Kafka Consumer 구현 또는 **Prefect 마이그레이션 PoC**, KOWAS PDF 파싱.

---

## 🧑 김나영 (Frontend) — `src/` (Phase1), `frontend/` (Phase2)

```bash
# Phase 1 Streamlit
cd ~/urban-immune-system/src
claude

streamlit run ../src/app.py --server.port 8501 --server.address 0.0.0.0
# 브라우저: http://34.64.124.90:8501

# Phase 2 Next.js
cd ~/urban-immune-system/frontend
claude

npm install
npm run dev          # http://34.64.124.90:3000
npm run lint
npm run type-check
```

**이번 주 주 작업**: `src/tabs/validation.py` 박진영 JSON 연결, `src/tabs/report.py` PDF 다운로드.

---

## 🧑 박정빈 (DevOps / QA) — `infra/`, `.github/`, `tests/`

```bash
cd ~/urban-immune-system/infra
claude

# Docker 스택
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs -f timescaledb

# K8s 매니페스트 검증
kubectl --dry-run=client apply -f infra/k8s/

# 테스트
cd ~/urban-immune-system
pytest tests/ -v --cov
pytest tests/ --cov-report=html   # htmlcov/index.html

# CI 워크플로 로컬 테스트 (선택)
# act 설치 후: act -j backend-lint
```

**이번 주 주 작업**: Frontend Lint CI 수정, trivy/CodeQL/Dependabot 워크플로, Grafana 모니터링 PoC.

---

## 🚨 자주 겪는 문제 (FAQ)

### Q. `claude` 명령어가 없다
```bash
# Claude Code 미설치 상태. 공식 설치 (5분):
curl -fsSL https://claude.ai/download/install.sh | bash
# 또는 npm:
npm install -g @anthropic-ai/claude-code
```

### Q. Docker 스택 붙여놓고 세션 닫았더니 멈췄다
```bash
sudo docker compose up -d    # 백그라운드 재기동
```

### Q. git push 할 때 인증 오류
```bash
gh auth login --git-protocol https --web
gh auth setup-git
```

### Q. venv 이상
```bash
cd ~/urban-immune-system
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[all,dev]"
```

### Q. 내 모듈 외 코드를 수정해야 하는데
- 다른 모듈 담당자에게 먼저 슬랙·Discord 에서 상의
- PR 에 해당 담당자를 reviewer 로 추가 (`CODEOWNERS` 로 자동 지정되기도 함)
