# 로컬/외부 가동 가이드 (Docker 미사용)

이 환경은 Docker 가 없어 `docker compose`(Kafka·TimescaleDB·Qdrant) 대신
**네이티브 PostgreSQL 16** 으로 가동한다. develop 브랜치 기준.

## 접속 (외부)
- **Next.js 대시보드 (정식)**: http://3.34.222.103:13000/dashboard
- FastAPI 백엔드: http://3.34.222.103:18001  (`/health`, `/docs`)
- 브라우저는 같은 origin(:13000)으로 `/api/v1/*` 호출 → Next 프록시가 내부 백엔드(127.0.0.1:18001)로 중계 (CORS·공인 백엔드포트 불필요).

## 포트 (다른 세션과 겹치지 않게 선택)
| 서비스 | 포트 | 바인드 |
|---|---|---|
| FastAPI 백엔드 | 18001 | 0.0.0.0 |
| Next.js 대시보드 | 13000 | 0.0.0.0 |
| Streamlit(Phase1, 옵션) | 18501 | 0.0.0.0 |

## 구성 요약
- DB: PostgreSQL `urban_immune` (user `uis_user`). 스키마는 `infra/db/init.sql` 에서
  TimescaleDB 전용 구문(`create_hypertable`, continuous aggregate)만 제거해 적용.
- 데모 데이터: `python scripts/seed_demo_db.py` — 17개 시·도 × 40주 시계열 + 융합점수
  (최신 주 대도시 RED + 나머지 YELLOW/ORANGE 혼합).
- `backend/app/api/predictions.py`: `import torch` 를 함수 내부 **지연 import** 로 변경
  (저메모리 환경에서 모듈 레벨 torch import 가 OOM 유발 → anomaly 호출 시점으로 미룸).
- 환경설정: 루트 `.env`, `frontend/.env.local`.

## 재기동
```bash
bash scripts/run_all.sh              # 백엔드 + 대시보드
bash scripts/run_all.sh --streamlit  # + Streamlit (메모리 여유 시)
```

## 기능별 상태
- ✅ 17지역 위험도 지도 / KPI / 시계열 / 경보 테이블 — 실 DB 데이터로 동작
- ⚠️ AI 리포트(SSE) · 챗봇: `ANTHROPIC_API_KEY` 입력 시 동작 (미입력 시 에러 이벤트로 graceful 종료)
- ⚠️ 이상탐지(anomaly): Autoencoder 체크포인트 없음 → 503 안내 메시지(graceful).
  필요 시 `python -m ml.anomaly.train_synth --save-checkpoint`
- ℹ️ 수집기/Kafka/스케줄러: 미가동(데모 데이터로 대체). 실 수집은 네이버·KMA API 키 필요.


## 🆕 실 임상 데이터 사전예측 모델 (CDC ILINet)
self-target proxy 라벨(KDCA 대비 Cohen κ=0.058) 문제를 닫기 위해, **실제 임상 감시 데이터
(CDC ILINet wILI, 2003–2024 · 21시즌 · 11권역)** 를 ground truth 로 사용하는 사전예측 모델을 추가.
모듈 `ml/forecast/`, 상세 `docs/REAL_CLINICAL_FORECAST.md`.

- 실측 walk-forward(2010–2023 시즌 holdout) 결과:
  - 2주 선행 유행경보 **F1=0.911 / Precision=0.920 / Recall=0.902 / AUPRC=0.975** (실 임상 라벨 대비)
  - wILI 회귀: persistence 대비 +19~26%, climatology 대비 +40~73% skill, 95% 구간 coverage 90.8~94.8%
  - 유행개시: 138 권역-시즌 중 **98.6% 가 onset 이전 경보**, 평균 1.96주 선행
- 재현: `PYTHONPATH=. python -m ml.forecast.validate` (검증) · `... -m ml.forecast.train` (학습+최신예측)
- API:
  - `GET /api/v1/forecast/validation` — walk-forward 임상 검증 메트릭
  - `GET /api/v1/forecast/latest` — 권역별 1–4주 선행 예측(점·95%구간·경보확률)
  - `GET /api/v1/forecast/regions` — 경보 권역 요약 (외부: http://3.34.222.103:18001/api/v1/forecast/regions)

## 메모 (메모리 ~3.7GB 공유 환경)
- 가용 메모리가 빠듯하면 Streamlit·anomaly torch 로드 시 OOM 위험.
  대시보드 본 기능은 백엔드(RSS ~150MB)+Next dev 로 충분히 동작.
