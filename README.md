# Urban Immune System

도시 데이터를 조기 감지 레이어로 통합해 감염병, 환경 이상, 지역 위험 신호를 탐지하고 리포트로 연결하는 멀티모달 분석 플랫폼입니다.

## Goals

- 이기종 도시 데이터의 수집과 표준화
- 이상탐지와 시계열 예측 기반 조기 경보
- RAG 기반 리포트 자동 생성
- 지도와 차트 중심 운영 대시보드 제공

## Stack

- Backend: FastAPI, SQLAlchemy
- Pipeline: Python collectors, Kafka
- Storage: TimescaleDB, Qdrant
- ML: PyTorch, scikit-learn
- Frontend: Next.js
- Infra: Docker Compose, Kubernetes, Terraform

## Repository Layout

```text
urban-immune-system/
├── README.md
├── LICENSE
├── .gitignore
├── docker-compose.yml           # Local development services
├── .github/
│   └── workflows/
│       ├── ci.yml               # PR lint + test
│       └── deploy.yml           # Deploy on main
├── backend/                     # FastAPI server
├── pipeline/                    # Data pipeline and collectors
├── ml/                          # ML models and report generation
├── frontend/                    # Next.js dashboard
├── infra/                       # Infrastructure assets
├── analysis/                    # Competition analysis archive
├── prototype/                   # Streamlit archive
└── docs/                        # Project documentation
```

## Quick Start

```bash
git clone https://github.com/zln02/urban-immune-system.git
cd urban-immune-system
docker compose up -d
```

서비스 개발 진입점:

- Backend: `backend/app/main.py`
- Pipeline: `pipeline/collectors/kafka_producer.py`
- ML: `ml/rag/report_generator.py`
- Frontend: `frontend/src/app/page.tsx`

## Status

현재 저장소는 팀 개발용 초기 스캐폴드와 실행 진입점을 포함합니다. 실제 수집 로직, 모델 학습 코드, 배포 스크립트는 각 디렉터리에서 확장하면 됩니다.
