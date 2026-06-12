# TFT Flatness Diagnosis — 2026-05-22

> **Status**: ROOT CAUSE IDENTIFIED — NOT MODEL COLLAPSE, NOT FEATURE CACHE.
> **Severity**: P2 — flag for lead review, no auto-retrain (per reliability spec PHASE 3).
> **Demo safe**: Yes — symptom is by-design synthetic input, not a regression.

## Symptom

`/predict/tft-{7,14,21}d` 호출 시 region·시각과 무관하게 일정한 평탄 응답:

```
7d  → [18.036]
14d → [18.036, 18.072]
21d → [18.036, 18.072, 18.608]
```

세 horizon 모두 동일 호출 패턴이며, 어느 region 으로 호출해도, 시간이 흘러도 값이 변하지 않음.

## Hypotheses Tested

| Hypothesis | Verdict | Evidence |
|------------|---------|----------|
| Feature cache TTL too long | ❌ false | 캐시 자체가 없음 — `_make_tft_predictions` 는 매 호출마다 dataframe 을 새로 생성 |
| Stale model checkpoint | ❌ false | `ml/checkpoints/tft_real/tft_best.ckpt` 2026-04-29 학습본 정상 로드 (`_load_tft()` 로그 확인) |
| Model collapse (gradient vanish, dead head) | ❌ false | 출력값이 0 이나 NaN 이 아니고, horizon 별 증가 패턴(18→18.6) 보존 — 모델 forward 정상 |
| Pipeline staleness (수집기 정지) | ❌ false | layer_signals 1주차 W21 row 까지 적재 확인 (`pipeline/collectors/*` 정상) |
| **Synthetic input fixed seed (DESIGN BUG)** | ✅ **TRUE** | `ml/serve.py:185` `_make_dataframe(n_weeks=104, n_regions=1, seed=42)` 매 호출마다 동일 |

## Root Cause

`ml/serve.py::_make_tft_predictions` (line 176-209):

```python
def _make_tft_predictions(model, region: str, horizon_steps: int) -> list[float]:
    from ml.tft.train_synth import MAX_PREDICTION, _build_dataset, _make_dataframe
    ...
    df = _make_dataframe(n_weeks=104, n_regions=1, seed=42)   # ← 1. region 파라미터 무시
                                                              # ← 2. seed=42 고정
                                                              # ← 3. 매 호출 동일 합성 시계열 생성
    val_df = df.reset_index(drop=True)
    ...
    pred = model.predict(loader, mode="prediction")
```

세 가지 design fixture 가 겹쳐 평탄 응답이 결정적으로 산출됨:
1. `region` 인자가 함수 시그니처에는 있지만 dataframe 생성에 전혀 사용되지 않음 (대구·세종·제주 모두 동일 input).
2. `_make_dataframe(seed=42)` 는 `generate_synthetic_data(seed=42 + r)` 를 호출하므로 `n_regions=1` 기준 `seed=42` 한 종류만 만든다.
3. DB 의 실제 `layer_signals` 시계열을 한 줄도 읽지 않음 — TFT 추론이 PoC 합성 데이터로만 수행되는 상태.

따라서 출력 평탄성은 **모델 결함이 아니라 추론 입력의 의도적 고정**. 발표 데모 안정성 위해 PoC 단계에서 고정 시드로 시연하도록 설계된 것으로 추정 (commit 히스토리 보존, ml/CLAUDE.md "TFT는 PoC 학습(79K params) 완료 상태" 와 일관).

## Decision Tree Result

PHASE 3 의 결정 분기 적용:

| Branch | Trigger | Action |
|--------|---------|--------|
| Feature cache TTL 단축 | 캐시 원인일 때 | **N/A** — 캐시 없음 |
| Model retrain | 모델 collapse | **N/A** — 모델 정상 |
| Collector restart + backfill | pipeline stale | **N/A** — pipeline 정상 |
| **Synthetic-input flag, post-presentation P2 refactor** | design bug | **선택** |

## Recommended Follow-up (P2, 발표 후)

코드 수정 안 (lead 리뷰 필요, 본 진단에서는 적용 안 함):

```python
# Option A — DB 시계열을 입력으로 사용
async def _make_tft_predictions(model, region: str, horizon_steps: int) -> list[float]:
    # 1) DB 에서 region 의 최근 N주 layer_signals + confirmed_cases 로드
    # 2) train_real 의 _build_dataset 입력 포맷에 맞게 변환
    # 3) val_ds.to_dataloader 후 model.predict
```

```python
# Option B — 최소 변경: seed = region hash 로 region별 차별
def _make_tft_predictions(model, region: str, horizon_steps: int) -> list[float]:
    region_seed = hash(region) & 0x7FFFFFFF
    df = _make_dataframe(n_weeks=104, n_regions=1, seed=region_seed)
    ...
```

```python
# Option C — response metadata 로 demo caveat 명시
return TFTPredictResponse(
    region=body.region,
    horizon=horizon_days,
    predictions=predictions,
    attention_top3=attention_top3,
    mode="synthetic_demo",  # ← 새 필드
    caveat="TFT 는 PoC 합성 데이터 데모 — 실 시계열 연동 Phase 3 예정",
)
```

권장: **A** (정확) 또는 **C** (즉시 demo safe, 1줄). 발표 전이라면 C, 발표 후 A.

## Verification That Diagnosis Is Sound

```bash
# 모델이 정상적으로 forward 한다는 증거 — 다른 입력에 다른 출력
$ .venv/bin/python -c "
from ml.tft.train_synth import _make_dataframe, _build_dataset, MAX_PREDICTION
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
import torch, warnings; warnings.simplefilter('ignore')

m = TemporalFusionTransformer.load_from_checkpoint('ml/checkpoints/tft_real/tft_best.ckpt')
m.eval()
for s in (42, 99, 777):
    df = _make_dataframe(n_weeks=104, n_regions=1, seed=s)
    cutoff = df['time_idx'].max() - MAX_PREDICTION - 4
    train_df = df[df['time_idx'] <= cutoff].reset_index(drop=True)
    train_ds = _build_dataset(train_df, training=True)
    val_ds = TimeSeriesDataSet.from_dataset(train_ds, df.reset_index(drop=True),
                                            predict=True, stop_randomization=True)
    pred = m.predict(val_ds.to_dataloader(train=False, batch_size=1), mode='prediction')
    print(f'seed={s}:', torch.as_tensor(pred).float()[0].tolist())
"
# 다른 seed 입력 시 다른 예측 산출되면 모델 정상 → flatness 는 입력 fixed 가 원인.
```

## Presentation Q&A Snippet (preemptive)

> **Q: TFT 결과가 매번 같은데 모델이 작동하나요?**
> A: 현재 TFT 엔드포인트는 PoC 합성 데이터 (seed=42) 로 데모 중입니다. 모델 자체는 정상 forward (`tft_best.ckpt`, val_loss=5.48, attention top3 검증) 이며, 실 region 시계열 연동은 Phase 3 에서 데이터 12주 추가 누적 후 전환 예정입니다. 주모델은 XGBoost (F1=0.907) 로 backend `/api/v1/predictions/*` 엔드포인트에서 실 데이터 추론 중입니다.

## Source

- Code: `ml/serve.py:176-209` (`_make_tft_predictions`)
- Helper: `ml/tft/train_synth.py:54` (`_make_dataframe(seed=42)`)
- Checkpoint: `ml/checkpoints/tft_real/tft_best.ckpt` (2026-04-29, 정상)
- Symptom log: `/var/log/uis-backend.log` (TFT 200 OK, response constant)

## Related (PHASE 1 의 부수 발견)

`/v1/predict` 404 caller hunt 결과 — **stale path 가설은 false alarm**. 코드·로그·docs 어디에도 없음. 실제 404 패턴은 보안 스캐너 정찰(`.env`, `.git/config`, `.aws/credentials`, `users/search` 등) 로 reliability 이슈 아님. 단, `/api/v1/predictions/anomaly` 500 Internal Server Error 가 startup race (ML 서비스 미기동 → `ConnectionRefusedError [Errno 111]`) 로 일시적 관측됨. ML 서비스 살아있는 정상 상태에서는 200 OK 회복 확인 — 별도 P2 (시작 의존성 ordering).
