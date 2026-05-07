# ML 모델 설정 명세

> 운영 현황·베이스라인 수치는 `docs/STATUS.md` 참조.

## TFT (Temporal Fusion Transformer)

설정 위치: `ml/configs/model_config.yaml` — 이 파일에서만 변경

```yaml
# ml/configs/model_config.yaml 에서만 변경
hidden_size: 64
attention_heads: 4
dropout: 0.1
encoder_length: 24   # 주 단위
prediction_lengths: [7, 14, 21]
```

## 이상탐지 Autoencoder

- 임계값: 재구성 오차 **99th percentile**
  - `ff17dfa` 핫픽스로 95p → 99p 상향 (17지역 inference 16/17 → 1/17 정상화)
- 임계값 하드코딩 금지 → `ml/configs/model_config.yaml` 관리

## RAG 리포트

- LLM 선택: 환경변수 `LLM_PROVIDER=openai|anthropic`
- 프롬프트 변경 시 `tests/test_report_generator.py` 반드시 동시 업데이트
- Qdrant 컬렉션명: `epidemiology_docs` — **임의 변경 금지**
