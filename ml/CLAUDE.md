# ml/ — 박진영 (PM·ML Lead)

## 담당자
박진영 (PM / ML Lead) · 전 모듈 PL 권한

## 기술 스택
- PyTorch + PyTorch Forecasting (TFT)
- scikit-learn (XGBoost, walk-forward CV)
- Claude Haiku (RAG via Qdrant + MiniLM 임베딩)
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
# 이상탐지: Autoencoder (재구성 오차 99th percentile — ff17dfa 핫픽스 상향)
# 리포트: Claude Haiku (RAG via Qdrant + MiniLM)
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
- 재구성 오차 **99th percentile** (훈련 세트 기준) — `ff17dfa` 핫픽스로 95p→99p 상향, 실데이터 17지역 inference 16/17→1/17 정상화
- `ml/configs/model_config.yaml` 의 `autoencoder.threshold_percentile` 또는 `ml/anomaly/train_synth.py` config 에서만 관리
- 하드코딩 금지
- ⚠️ `ml/outputs/anomaly_metrics.json` 의 `evaluation.precision=0.051` 은 **합성 artificial spike** 평가값(5TP/93FP/6TN). 발표 데모는 `real_data_inference` (실 17지역) 기준 사용.

## 모델 성능 모니터링 지표

| 지표 | 목표값 | 주기 |
|------|--------|------|
| F1-Score | **0.80 이상** (현 baseline 0.882) | 주간 |
| Recall | **0.85 이상** (현 baseline 0.837 — 미달, 게이트 완화 옵션 검토) | 주간 |
| Precision | **0.90 이상** (현 baseline 0.949) | 주간 |
| FAR (오경보율) | **0.30 미만** (현 baseline 0.206 gate ON, 0.602 gate OFF — 게이트 효과 65.8%) | 주간 |
| MCC | 0.50 이상 (현 baseline 0.595) | 주간 |
| Balanced Accuracy | 0.75 이상 (현 baseline 0.816) | 주간 |
| AUPRC | 0.85 이상 (현 baseline 0.973) | 주간 |
| MAE (예측 오차) | 임계값: `ml/configs/model_config.yaml` 관리 | 주간 |

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
│   ├── report_generator.py # Claude Haiku 리포트 (default; openai legacy fallback)
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

## 발표 QA 답변 스니펫

**Q: 왜 XGBoost를 주모델로 썼는가?**
A: 학습 데이터 26주 누적 시점에서 walk-forward CV 5-fold 결과 XGBoost가 안정적 성능(F1=0.882, Precision=0.949, Recall=0.837)을 보여 보수적 채택. TFT는 PoC 학습(79K params) 완료 상태이며 데이터 누적 시 전환 예정.

**Q: TFT는 언제 쓰나?**
A: `/predict/tft-{7,14,21}d` 엔드포인트로 7/14/21일 선행 예측 제공. 현재 합성 데이터 학습 결과(attention top3: 검색량·하수·OTC) 검증된 상태. 실제 데이터 12주 추가 누적 후 프로덕션 전환.

**Q: Recall이 0.837로 목표(0.85) 미달인데?**
A: 교차검증 게이트(2개 계층 동시 임계초과) 조건이 엄격해 FN이 일부 발생. 다만 직전 baseline 0.768 대비 +0.069 향상. 대신 Precision=0.949, FAR=0.206으로 오경보를 최소화했다 — 보건당국 신뢰 확보 우선. 게이트 임계 완화 시 Recall 0.90 이상 달성 가능하나 FAR 1.5배 상승 trade-off.

**Q: 17개 지역 평균 리드타임이 6.5주라는 근거는?**
A: `analysis/outputs/backtest_17regions.json` walk-forward 백테스트 결과 17지역 평균 6.47주. 가장 빠른 탐지는 세종(9주), 부산·제주(8주), 서울(7주), 경기·인천 등 12개 지역(6주). 임상 확진 약 1.5개월 전 YELLOW 발령으로 대응 준비시간 확보.

**Q: 합성 데이터 F1 0.967 vs 실제 F1 0.882 갭은?**
A: 합성 데이터는 이상적 분포 가정, 실제는 지역별 편차 존재. 갭이 있더라도 실제 데이터 기준 목표(0.80) 초과 달성. `ml/outputs/validation.json`에서 상세 수치 확인 가능.

**Q: F1 단독 표기가 아니라 더 엄격한 지표는?**
A: F1 외에 클래스 불균형에 강한 **MCC(Matthews Correlation Coefficient)·Balanced Accuracy·AUPRC** 도 병기한다. 17지역 평균 **MCC=0.595, Balanced Acc=0.816, AUPRC=0.973** (baseline 0.81 대비 +0.16). MCC 는 4셀(TP/FP/FN/TN) 모두 반영해 F1 의 TN 무시 한계를 보완하고, AUPRC 는 ROC 와 달리 클래스 불균형에서 정직한 지표(Saito & Rehmsmeier 2015 권장). 산출 함수: `ml/evaluation/metrics.py`, 갱신 위치: `analysis/outputs/backtest_17regions.json` summary.
