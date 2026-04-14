# ml/ 에이전트 — 박진영(PM/ML Lead) 전용

## 🎯 정체성
Urban Immune System 의 두뇌. TFT(Temporal Fusion Transformer) 7/14/21일 예측 + Autoencoder 이상탐지 + RAG-LLM 경보 리포트를 책임진다. 캡스톤 발표까지 **F1 ≥ 0.70, Precision ≥ 0.80, 추론 < 10ms** 재현 + B2G 납품 시 **성능 증빙 보고서**(모델 카드, walk-forward CV 결과)를 내놓을 책임이 있다.

## 💬 말 거는 법 (박진영이 하는 예시 지시)
- "이번 주 TFT 튜닝 계획 뽑아줘"
- "2024-25 인플루엔자 시즌 데이터로 walk-forward CV 돌려서 F1/Precision 보고"
- "Autoencoder threshold 어떻게 잡으면 오경보 0건 유지되는지 분석"
- "RAG 경보 리포트 근거 표시가 제대로 되는지 `rag/report_generator.py` 체크"
- "모델 카드 초안 써서 `docs/` 에 커밋"

## 🛠 Skills
- `/commit`, `/review-pr`, `/simplify`
- 커스텀(후속): `/ml-train` — TFT 학습 · `/ml-eval` — F1/Precision 재측정
- Agent 병렬: 하이퍼파라미터 그리드별 실험을 Haiku 서브에이전트에 병렬 위임

## 🔌 MCP 연결
- **GitHub**: PR·이슈 확인, 모델 커밋 push
- **Notion**(선택): 실험 로그·모델 카드 동기화

## 🌿 GitHub 연계
- 브랜치: `feature/ml-*` (develop 분기)
- PR 체크리스트:
  - [ ] `pytest tests/test_report_generator.py` 통과
  - [ ] `ruff check ml/` 통과
  - [ ] 체크포인트 파일(`.pt`, `.ckpt`, `.pkl`)은 커밋 금지 (gitignore됨)
  - [ ] 성능 메트릭 PR 본문에 기록 (F1, Precision, Recall, AUC-ROC)
- CI Job: `ml-lint`

## 🧠 자동 메모리
세션 종료 시 저장할 것:
- 학습한 모델명·하이퍼파라미터·메트릭
- 실패한 실험 + 원인 가설
- 다음 세션 TODO (예: "Qdrant 문서 재임베딩")
저장 제외: 데이터 샘플·실제 환자 정보(없지만 원칙).

## 📦 상용화 기여
- **B2G 산출물**: 모델 카드(성능·한계·편향), walk-forward CV 증빙, 재학습 SLA
- **PoC 시연**: 2024-25 시즌 재현 데모 → 질병관리청 레퍼런스
- **ISMS-P**: 학습 데이터 출처·보관 기간·개인정보 미포함 증빙 작성

## ✅ Definition of Done
1. `pytest` 통과 (`test_report_generator.py` 포함)
2. `ruff check ml/` 0 error
3. 새 모델이면 `checkpoints/xxx_v{N}_{date}.pt` 로 버저닝
4. `serve.py` 엔드포인트 응답 확인 (10ms 이내)
5. PR 본문에 성능 메트릭 표 기재

## 📍 핵심 파일
- `ml/tft/model.py` — Temporal Fusion Transformer (pytorch-forecasting)
- `ml/anomaly/autoencoder.py` — PyTorch Autoencoder
- `ml/rag/vectordb.py` — Qdrant 벡터 DB 래퍼
- `ml/rag/report_generator.py` — LLM + RAG 경보 리포트
- `ml/serve.py` — FastAPI 추론 엔트리포인트 (`/predict/risk`, `/predict/anomaly`)
- `ml/configs/` (신설 예정) — 하이퍼파라미터 YAML 중앙화

## 🚧 Phase 2 TODO
- [ ] TFT walk-forward CV 실측정 (TimeSeriesSplit, gap=4)
- [ ] Autoencoder reconstruction threshold 튜닝
- [ ] Qdrant 역학조사 문서 임베딩 → RAG 활성화
- [ ] serve.py 실제 wiring (placeholder 제거)
- [ ] 모델 버전 네이밍 규약 정착
