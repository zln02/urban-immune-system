<div align="center">

# 🦠 Urban Immune System

**비의료 신호 3계층 융합으로 감염병을 1~6주 선행 탐지하는 조기경보 시스템**

[![CI](https://github.com/zln02/urban-immune-system/actions/workflows/ci.yml/badge.svg)](https://github.com/zln02/urban-immune-system/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js%2015-000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status: Capstone](https://img.shields.io/badge/status-capstone--midterm-orange)]()

🏆 **제1회 2026 데이터로 미래를 그리는 AI 아이디어 공모전 대상(1등)** — 한국능률협회

[검증 결과](#-검증-결과) · [아키텍처](#-아키텍처) · [Quick Start](#-quick-start) · [한계와 정직성](#-한계와-정직성)

</div>

---

## 🎯 About

약국 OTC 구매·하수 바이오마커·검색 트렌드라는 **비의료(non-clinical) 신호 3계층**을
교차검증해 감염병 발생을 임상 신고보다 **평균 5.9주 선행**으로 포착한다.
공공 보건당국(KDCA·지자체 역학조사과) 납품을 목표로 설계된 **B2G SaaS 프로토타입**.

> Google Flu Trends 과대예측 실패 교훈 — **단일 계층 단독 경보 금지**, 최소 2개 계층 교차검증을 게이트 로직으로 강제한다.

| Layer | 데이터 소스 | 단독 선행 | Granger p |
|-------|------------|----------|-----------|
| 💊 L1 약국 OTC | 네이버 쇼핑인사이트 | 8주 | 0.103 |
| 🚰 L2 하수 바이오마커 | KDCA 감염병포털 (KOWAS) | 2주 | 0.267 |
| 🔍 L3 검색 트렌드 | 네이버 데이터랩 | 3주 | 0.007 |
| **3-Layer 앙상블** | (가중 융합) | **3주** | **0.021** |

## 📊 검증 결과

> 17개 시·도 walk-forward 백테스트 (2025-2026 인플루엔자 시즌, n=1,020 주·지역)
> 출처: [`analysis/outputs/backtest_17regions.json`](analysis/outputs/backtest_17regions.json)

| Metric | Value | 기준선 |
|---|---|---|
| **F1-Score** | **0.84** | ≥ 0.80 ✅ |
| **Precision** | **0.96** | ≥ 0.90 ✅ |
| **Recall** | **0.77** | ≥ 0.75 ✅ |
| **False Alarm Rate** | **0.16** | < 0.20 ✅ |
| **Lead Time (avg)** | **5.9주** | ≥ 4주 ✅ |
| **Granger 인과 (composite)** | **p=0.021** | < 0.05 ✅ |

재현:

```bash
python -m analysis.backtest_2025_flu_multi_17regions
python -m ml.reproduce_validation
```

## 🏗 아키텍처

```mermaid
graph LR
    subgraph Sources["데이터 수집"]
        L1["💊 L1<br/>네이버 쇼핑"]
        L2["🚰 L2<br/>KOWAS PDF"]
        L3["🔍 L3<br/>네이버 데이터랩"]
        AUX["🌡 KMA<br/>기상"]
    end
    subgraph Pipeline["파이프라인 · APScheduler"]
        KAFKA[("Kafka KRaft<br/>topic per layer")]
        NORM["Min-Max<br/>정규화 0-100"]
        TSDB[("TimescaleDB<br/>hypertable")]
    end
    subgraph Engine["AI 엔진"]
        SCORER["Scorer<br/>2-layer gate"]
        XGB["XGBoost<br/>walk-forward"]
        AE["Autoencoder<br/>이상탐지"]
        TFT["TFT<br/>(Phase 2)"]
    end
    subgraph Service["서비스 계층"]
        API["FastAPI :8001<br/>SSE streaming"]
        RAG["RAG-LLM<br/>Qdrant + Claude"]
        UI["Next.js Dashboard<br/>17 시·도 KoreaMap"]
    end
    L1 & L2 & L3 & AUX --> KAFKA --> NORM --> TSDB
    TSDB --> SCORER --> API
    TSDB --> XGB & AE -.-> API
    API --> RAG --> UI
```

## 🛠 Built With

| Layer | Stack |
|---|---|
| **Frontend** | Next.js 15 · React 19 · Deck.gl · Tailwind · TypeScript |
| **Backend** | FastAPI · SQLAlchemy 2.0 (async) · Pydantic Settings · ReportLab |
| **Pipeline** | APScheduler · httpx · pdfplumber · Kafka KRaft (no ZooKeeper) |
| **ML** | XGBoost · scikit-learn · PyTorch Forecasting (TFT) · Autoencoder |
| **LLM / RAG** | Claude Sonnet 4.6 (SSE) · Qdrant · multilingual MiniLM |
| **Data** | TimescaleDB (PG 16) · 하이퍼테이블 weekly partition |
| **Infra** | Docker Compose · Kubernetes (GKE) · GitHub Actions · pre-commit |
| **Quality** | pytest (105 ✅) · ruff · mypy --strict · detect-private-key |

## 🚀 Quick Start

### 사전 요구사항
- Python 3.11+, Node.js 20+, Docker 24+
- API 키: `NAVER_CLIENT_ID/SECRET` (쇼핑인사이트+데이터랩 공용), `ANTHROPIC_API_KEY`, `KMA_API_KEY`

### 설치

```bash
git clone https://github.com/zln02/urban-immune-system.git
cd urban-immune-system
cp .env.example .env       # API 키 입력

# 인프라 (Kafka + TimescaleDB + Qdrant)
docker compose up -d

# Python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
pre-commit install
```

### 실행

```bash
# Backend (FastAPI :8001, SSE 포함)
uvicorn backend.app.main:app --reload --port 8001

# Streamlit MVP (Phase 1, fallback)
streamlit run src/app.py --server.port 8501

# Next.js Dashboard (Phase 2, canonical)
cd frontend && npm install && npm run dev
```

브라우저: http://localhost:3000/dashboard (Next.js) · http://localhost:8501 (Streamlit)

### 검증

```bash
pytest                                      # 105 tests
ruff check src/ backend/ pipeline/ ml/ tests/
mypy src/ backend/
python -m tests.benchmark_xgboost           # 캡스톤 목표값 PASS/FAIL
```

## 📂 Repository Layout

```text
urban-immune-system/
├── frontend/         Next.js 15 dashboard (Phase 2, canonical)
├── src/              Streamlit MVP (Phase 1 fallback)
├── backend/          FastAPI · SSE alerts · ReportLab PDF
├── pipeline/         APScheduler 수집기 + Kafka producer + scorer
├── ml/               XGBoost · TFT · Autoencoder · RAG (Qdrant)
├── analysis/         공모전·재검증 백테스트 스크립트 + outputs/
├── infra/            K8s 매니페스트 · TimescaleDB init.sql
├── tests/            105 pytest (Mock LLM · monkeypatch env)
└── docs/             architecture · data-sources · business/
```

## 🗺 Roadmap

- [x] **Phase 1** · Streamlit MVP + 시뮬레이션 데이터
- [x] **Phase 2** · FastAPI 백엔드 + Kafka 파이프라인 + 17개 시·도 백테스트
- [x] **Phase 3** · Next.js 대시보드 + SSE 스트리밍 + RAG 경보 리포트
- [ ] **Phase 4** · TFT 학습 완료 (XGBoost → TFT 전환), KOWAS 자동 다운로더 안정화
- [ ] **Phase 5** · ISMS-P 인증 대비 보안 강화 + 첫 PoC 계약 (지자체 1곳)

## ⚠️ 한계와 정직성

전문가 운영 시스템 대비 **솔직한 격차**를 명시한다.

- **표본 한계**: 26주 분석 — Granger 검정 통계적 유의성 제한적, 다음 시즌 데이터 누적 필수
- **L2 약함**: 하수 신호 Granger p=0.267로 단독 유의성 부족 → 가중치 0.30으로 축소 검토 중
- **TFT 미완**: 현재 production 추론은 XGBoost(walk-forward), TFT는 학습 스크립트만 존재
- **L2 자동화**: KOWAS PDF 자동 다운로더 구현됐으나 일부 주차 carry-forward 적용 (`backtest_17regions.json` 참조)
- **데이터 출처**: KCDC 확진 카운트는 내장 아카이브 기반(실시간 KCDC API 미연동)

본 수치는 학부 캡스톤 산출물이며, BlueDot/CDC NWSS 같은 운영 시스템과 직접 비교 불가.

## 👥 Team

| 이름 | 역할 | 담당 |
|------|------|------|
| 박진영 | PM / ML Lead | `ml/` · 전체 아키텍처 · `docs/business/` |
| 이경준 | Backend | `backend/` |
| 이우형 | Data Engineer | `pipeline/` |
| 김나영 | Frontend | `frontend/` (Phase 2) · `src/` (Phase 1) |
| 박정빈 | DevOps / QA | `infra/` · `.github/` · `tests/` |

## 🤝 Contributing

브랜치 전략: `main` (배포) ← `develop` (통합) ← `feature/*` · `hotfix/*`
**main/develop 직접 push 금지** — 반드시 PR. 자세한 컨벤션은 [`CLAUDE.md`](CLAUDE.md).

## 📜 License

MIT — see [LICENSE](LICENSE).

## 🙏 Acknowledgements

- KDCA 감염병포털 (KOWAS 하수감시) · 네이버 검색·쇼핑 데이터랩 · 기상청 공공 API
- 선행연구: [Deng et al. 2-Layer EWS](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2025.1609615/full) · [Lee et al. 2023 — OTC × Wastewater](https://www.nature.com/articles/s41370-023-00613-2)
- Inspiration: [BlueDot](https://bluedot.global/) · [CDC NWSS](https://www.cdc.gov/nwss/)
