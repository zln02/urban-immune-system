# FAQ-002: F1 수치는 어떻게 측정했나? (난도: M)

## 핵심 답변 (30초)

> `analysis/notebooks/performance_measurement.py` 스크립트에서 `sklearn.metrics.f1_score` 로 실측합니다. 2024-25 인플루엔자 시즌 52주 (Train 26주 + Test 26주) 를 사용해 3-Layer 앙상블 기준 **F1=0.643 · MCC=0.442 · AUPRC=0.885** 입니다. 임계값은 Train 에서 F1-최적화로 탐색했습니다. 현재 재현성을 위해 `seed=42` 합성 데이터를 쓰고 있으며, KDCA ILINet 실데이터 확보 후 동일 스크립트로 재측정 예정입니다.

## 상세

### 측정 파이프라인
```python
from sklearn.metrics import f1_score, matthews_corrcoef, average_precision_score

# 1. Train/Test 시간 순 분할 (walk-forward 방식)
train_gt = gt_binary[:26]   # 26주
test_gt = gt_binary[26:]    # 26주

# 2. Train 에서 F1 최적 임계값 탐색
for t in np.linspace(10, 90, 81):
    pred = (scores >= t).astype(int)
    f1 = f1_score(train_gt, pred, zero_division=0)
    # ...

# 3. Test 에서 평가
pred = (test_scores >= best_threshold).astype(int)
f1 = f1_score(test_gt, pred)
mcc = matthews_corrcoef(test_gt, pred)
auprc = average_precision_score(test_gt, test_scores)
```

### 결과 (2026-04-21 합성 데이터 기준)
| 모델 | F1 | MCC | AUPRC | FP |
|---|---|---|---|---|
| L1 단독 | 0.621 | 0.399 | 0.820 | 11 |
| L2 단독 | 0.615 | 0.359 | 0.838 | 9 |
| L3 단독 | 0.737 | 0.588 | 0.851 | 3 |
| 3-Layer | 0.643 | 0.442 | 0.885 | 10 |

결과는 `ml/outputs/validation.json` 에 저장, `src/tabs/validation.py` 가 실시간 로드하여 대시보드에 표시.

### 왜 Precision 1.00 주장 안 하는가
초기 README 에 "Precision=1.00 (오경보 0건)" 주장이 있었으나:
- 클래스 불균형(경보 이벤트 적음)에서 TP 1-2건·FP 0 이면 자동 1.00
- 단독 보고 시 오해 소지 → 현재 MCC + AUPRC + N 병기

## 연관 기록
- ADR-002 (F1 단독 → MCC/AUPRC 병기로 전환)
- TS-002 (README 하드코딩 수치 문제)
- metrics-history.md (주차별 측정값 추적)
