# ml/ — C 박진영 전용

## 담당자
역할 C — 박진영 (ML/AI 엔진)

## 기술 스택
- PyTorch + PyTorch Forecasting (TFT)
- scikit-learn (XGBoost, walk-forward CV)
- LangChain + Qdrant (RAG)
- FastAPI (추론 서빙, `serve.py`)

## 모델 선택 가이드

> **목표 모델: TFT** — Temporal Fusion Transformer (7/14/21일 예측)
> TFT의 Attention Weight는 보건당국 신뢰에 중요한 해석 근거 제공.
>
> 데이터 부족(26주) 해결책: **2019-2024 과거 시즌 역추적** + TimeGAN/Sliding Window 증강으로 26주+ 확보
> **Fallback (데이터 증강 이전)**: LSTM / XGBoost (walk-forward) 병행 비교 후 TFT 전환

```python
# 모델 구성
# 목표: TFT (7/14/21일 예측) — Attention weight 해석 가능성 필수
# Fallback: XGBoost (walk-forward) + LSTM (7/14일) — 데이터 증강 전
# 이상탐지: Autoencoder (재구성 오차 95th percentile)
# 리포트: RAG-LLM (Qdrant + GPT-4o-mini 또는 claude-haiku)
```

## LLM 설정

```bash
# .env 에서 선택
LLM_PROVIDER=openai          # openai | anthropic
OPENAI_MODEL=gpt-4o-mini     # 비용 절감 (mini 권장)
ANTHROPIC_MODEL=claude-haiku-4-5-20251001  # Haiku 권장
```

- LLM 관련 설정은 `ml/configs/model_config.yaml`의 `llm` 섹션에서 관리
- `LLM_PROVIDER` 환경변수가 yaml 설정을 override

## 하이퍼파라미터 규칙
- **`ml/configs/model_config.yaml`에서만 변경** — 코드 내 하드코딩 금지
- 체크포인트(`ml/checkpoints/`)와 yaml 버전 반드시 일치
- `threshold_percentile` 변경 시 `test_report_generator.py` 업데이트

## Walk-forward 교차검증 필수

```python
# 모든 시계열 모델에 walk-forward 적용
# TimeSeriesSplit(n_splits=5, gap=4)  # 4주 갭 (미래 누출 방지)
```

## 이상탐지 임계값
- 재구성 오차 **95th percentile** (훈련 세트 기준)
- `ml/configs/model_config.yaml`의 `autoencoder.threshold_percentile`에서만 관리
- 하드코딩 금지

## 모델 성능 모니터링 지표

| 지표 | 목표값 | 주기 |
|------|--------|------|
| F1-Score | **0.70 이상** | 주간 |
| Precision (오경보율) | 오경보 **0건** 유지 | 주간 |
| MAE (예측 오차) | 임계값: `ml/configs/model_config.yaml` 관리 | 주간 |
| AUC-ROC | 0.75 이상 | 주간 |

- 지표 계산 로직: `ml/evaluation/metrics.py` (별도 파일)
- 성능 저하 감지 시 텔레그램/로그로 알림

## RAG 설정
- Qdrant 컬렉션명: `epidemiology_docs` — **임의 변경 금지**
- `top_k`: 5 (yaml에서 변경)
- **임베딩 문서**: 역학 논문·가이드 **10~20편** 수집 목표 (WHO/KCDC 감염병 가이드라인 포함)
- 프롬프트 변경 시 `tests/test_report_generator.py` 반드시 함께 업데이트

## 폴더 구조
```
ml/
├── configs/
│   └── model_config.yaml   # 유일한 하이퍼파라미터 소스
├── tft/
│   └── model.py            # TFT 7/14/21일 예측
├── anomaly/
│   └── autoencoder.py      # 이상탐지
├── rag/
│   ├── report_generator.py # GPT-4o-mini / Claude-Haiku 리포트
│   └── vectordb.py         # Qdrant 클라이언트
├── serve.py                # FastAPI 추론 엔드포인트
└── checkpoints/            # ← 커밋 금지 (.gitignore)
```

## 커밋 금지 파일
```
ml/checkpoints/   # 모델 체크포인트 (용량 이슈)
```

## 테스트
```bash
pytest tests/test_report_generator.py   # RAG 리포트 (Mock LLM)
```
- 외부 LLM API는 반드시 Mock 사용 (`unittest.mock.patch`)
- 실제 API 키 테스트 코드에 포함 금지
