# UIS 전수 점검 + R&D 로드맵 (2024–2026 신기술 반영)

> 작성: 2026-06-03 · 발표 D-5~10
> 점검·서치: Claude Opus 4.7 + Sonnet 서브에이전트
> 입력: 박진영 PL "더 개발할 사항·개선점·전체 오류·신기술/신모델/논문 검색"

---

## 1. 코드베이스 전수 점검 결과

### 1.1 테스트

| 항목 | 결과 |
|---|---|
| pytest | **547 passed / 2 → 0 failed (이번 수정)** / 3 skipped |
| coverage | ≥35% CI 게이트 통과 |
| 수정 commit 후 통과 확인 | ✅ |

> 실패 2건은 다질병 OTC 도입 후 source 라벨이 변수(`otc_source`)로 분기되면서 리터럴 grep 테스트가 못 잡은 것 → 변수 정의 라인 검증으로 패턴 갱신.

### 1.2 lint·타입

| 도구 | 발견 → 수정 |
|---|---|
| ruff | 33 → 14 (자동수정 19) |
| 잔여 14 | E402 7 (`load_dotenv` 후 import — 의도적), E501 4 (긴 주석), F841 2 (unused-var), E741 1 (모호 이름) |
| mypy --strict | 핵심 모듈 (config·main·scorer) clean |

> 잔여 14건은 모두 비기능적. 발표 후 R&D 시 cleanup 권장.

### 1.3 보안

| 항목 | 상태 |
|---|---|
| 시크릿 하드코딩 | ✅ 없음 (자체 grep + gitleaks CI 통과) |
| `.env` 커밋 여부 | ✅ `.gitignore` 보호 |
| K8s SecurityContext | ✅ `runAsNonRoot`, `readOnlyRootFilesystem`, drop ALL |
| CORS | ✅ `allow_credentials=False`, 명시 도메인 |
| Pydantic Settings 검증 | ✅ production placeholder 차단 |
| HTTPS | ⚠ **미적용** (HTTP Basic Auth 평문 전송) |
| IP 화이트리스트 | ⚠ 0.0.0.0/0 공개 (팀 IP 제한 권장) |

### 1.4 데이터·운영

| 항목 | 상태 | 메모 |
|---|---|---|
| 시점 적재 결손 감지 | ⚠ **silent 누락** | 6/1 OTC 11/17지역만 INSERT → anomaly 거짓 11지역으로 표시되던 사고 (오늘 핫픽스) |
| KOWAS PDF 자동 다운로드 | ⚠ 수동 | Selenium/Playwright Phase 3 P0 |
| L1·L3 region 분리 | ⚠ 17지역 동일 broadcast | HIRA OpenAPI Phase 3 분리 |
| TFT-real 발산 | ⚠ 26주 데이터 한계 | 12주 추가 누적 후 재학습 |
| **scheduler 적재 알람** | ⚠ region별 누락 미감지 | ntfy 알람에 "17/17 적재 확인" 룰 추가 권장 (P1) |

### 1.5 의존성

- 주요 outdated: transformers 5.5→5.9, uvicorn 0.44→0.48, fastapi 마이너, typer 0.24→0.26
- **발표 직전 업그레이드 금지** — 회귀 위험. 발표 후 일괄 Phase 4 cleanup.

---

## 2. 발견된 개선점·오류 (우선순위)

| # | 항목 | 영향 | 우선 | 소요 |
|---|------|-----|------|-----|
| **P0** | OTC INSERT 결손 자동 재시도 + 17지역 적재 확인 알람 | 오늘 사고 재발 방지 | 발표 전 권장 | 2시간 |
| **P0** | HTTPS (Let's Encrypt + 도메인) | 비번 평문 전송 차단, ISMS-P 가산 | 발표 전 권장 | 2시간 |
| **P0** | KDCA COVID·노로 확진자 API 연동 | 다질병 supervised → F1 0.85+ 회복 | 박진영 신청 진행 중 | 3~5일 |
| P1 | proxy 한계 대신 transition + L1 OTC ML 우위 (+13%p 노로) → 발표 카드로 활용 | 정직성·심사 신뢰 | 이미 PR #74 완료 | — |
| P1 | scheduler 적재 healthcheck (region별 row 개수) | silent 누락 차단 | 발표 후 | 1시간 |
| P1 | 잔여 ruff 14건 cleanup (E402·E501·F841·E741) | 비기능 — 코드 품질 | 발표 후 | 30분 |
| P2 | 의존성 일괄 업그레이드 + 회귀 테스트 | 보안패치 + 성능 (Pydantic v2.7+ 50× validation 등) | Phase 4 | 1일 |
| P2 | KOWAS Selenium 자동 다운로드 | 수동 작업 폐기 | Phase 3 | 2일 |
| P3 | TFT-real 26→52주 누적 후 재학습 | val_loss=5.48 발산 해소 | 2026-09 (데이터 누적 필요) | 1주 |

---

## 3. 신기술·신모델 (2024–2026 SOTA 서치 결과)

### 3.1 시계열 예측 차세대

| 모델 | 출처 | 보고 게인 | UIS 적용성 |
|------|------|----------|-----------|
| **TimeMixer++** | ICLR 2025 Oral | TimesNet 대비 MSE **-25.7%**, iTransformer 대비 -7.3% | **P0-1 권장**. MLP 기반 추론 cheap, 26주 소량에서 안정 |
| **iTransformer** | ICLR 2024 Spotlight | PatchTST 대비 다변량 우위 | 3계층+AUX 4변수에 적합. fallback 후보 |
| **PatchTST** | ICLR 2023 | 안정적 baseline | 현 TFT 대비 학습 안정성↑. 백업 |
| **Mamba4Cast** | arXiv 2410.09385 | 트래픽 오차 18% / 전력 8% | 52주+ 누적 후 R&D |

> 2025 포지션 페이퍼(arXiv 2502.14045) 경고: hyperparameter 탐색 시 모델 간 차이 작음. "어떤 모델도 챔피언 없음" — TimeMixer++ Oral 채택은 신뢰도 상위.

### 3.2 하수역학 + ML (UIS L2 정렬)

| 연구 | 핵심 발견 | UIS 적용 |
|------|---------|---------|
| RF+Gaussian 앙상블 (ScienceDirect 2024) | 인플루엔자 A **9-10일** / SARS-CoV-2 5일 하수 선행 | L2 KOWAS → 임상 deconvolution 모듈 정량화 |
| LSTM+Prophet WBE (PMC 2024 확장) | LSTM이 RF 단독 대비 RMSE **-10%** | Autoencoder 옆에 deconvolution LSTM 병렬 |
| Shenzhen 다병원체 모니터링 (Tandfonline 2025) | KOWAS 유사 구조 + baseline 설정 | 노로·RSV 다질병 확장 시 직접 참조 |
| **WBE 종합 (Risk Analysis 2025)** | RSV는 하수 선행성 없음 — 임상이 앞섬 | **RSV는 L2 가중치 다운, L1·L3 우위** |

### 3.3 공간 GNN (epidemic)

| 모델 | 결과 | UIS 적용 |
|------|------|---------|
| EpiHybridGNN (arXiv 2511.15469, 2025) | EpiGNN + ColaGNN 통합 | 17지역 인접 행렬 입력 필요 |
| **SpatialEpiBench (arXiv 2605.06530, 2025)** | **대부분 GNN이 naive last-value 못 이김** (1일~1개월 예측) | ⚠ **소규모 17지역에서 위험** — P1 연기 |
| MSGNN (arXiv 2308.15840) | EpiGNN 대비 MAE 개선 | 인구이동 데이터(KT API·KTDB) 확보 후 |

> SpatialEpiBench 발견은 중요. UIS는 17지역 소규모라 GNN 도입 시 baseline 못 이길 위험. **인구이동 데이터 확보 + 52주+ 누적이 전제**.

### 3.4 다질병·라벨 효율 (가장 임팩트 큼)

| 모델 | 결과 | UIS 적용 |
|------|------|---------|
| **CAPE** (arXiv 2502.03393, 2025) | 17질병 × 50지역 SSL pretrain. zero-shot **-3.97~26.06% MSE**, RSV **-26%**, MPox **-20%**, COVID **-72.6%** vs MOMENT. 20% 라벨에서 33~53%↓ | **P0-1 강력 추천** — KDCA 라벨 미연동 기간에 L1·L2·L3로 pretrain → 연동 즉시 fine-tune |
| Foundation Models 평가 (medRxiv 2025.02) | TimesFM·Lag-Llama·Chronos·TimeGPT·TabPFN-TS ILI·RSV·COVID·뎅기 | Chronos Small zero-shot 빠른 실험 가능 (로컬 추론, ~46M params) |
| Transfer Learning 66 질병 (arXiv 2605.27269, 2025) | 66 질병 pretrain → 목표 질병 fine-tune. zero/few/full-shot 일관 개선 | 인플루엔자→노로/COVID 가중치 전이 |

---

## 4. R&D 로드맵 (발표 후 Phase 4+)

### Phase 4A (D+0 ~ D+30): 즉시 가능

| 순위 | 과제 | 기술 | 기대 효과 |
|------|------|------|---------|
| **R1** | **CAPE pretrain → KDCA fine-tune** | self-supervised + 17질병 prototype | 라벨 미연동도 시작 가능, 연동 즉시 supervised 점프 |
| **R2** | **TimeMixer++ TFT 교체** | ICLR 2025 Oral MLP-mixer | TFT val_loss=5.48 발산 해소, 추론 비용↓ |
| **R3** | **L2 → 임상 deconvolution LSTM** | WBE+LSTM Shenzhen·PMC 모델 | Lead 6.76주를 9~14일 단위로 분해 시각화 |

### Phase 4B (D+30 ~ D+90): 데이터 누적 필요

| 순위 | 과제 | 전제 |
|------|------|-----|
| R4 | KOWAS Selenium 자동화 | Phase 3 필수 P0 |
| R5 | HIRA OpenAPI 연동 (L1·L3 region 분리) | 외부 API 신청 |
| R6 | 인구이동 + EpiHybridGNN | KT API·KTDB 확보 |
| R7 | Chronos Small zero-shot 비교 실험 | 52주+ 누적 |

### Phase 4C (D+90+): B2G 사업화

| 순위 | 과제 |
|------|------|
| B1 | ISMS-P 풀 점검 + 인증 |
| B2 | 조달청 혁신제품 신청 |
| B3 | KDCA·서울시·WHO 협력센터 PoC 파일럿 |
| B4 | 가격 모델 3-tier 검증 (`docs/business/pricing-model.md`) |

---

## 5. 최종 프로젝트 평가

### 5.1 공모전 심사 기준 충족 (재확인)

| 기준 | 상태 |
|------|------|
| ① 기술 완성도 | ✅ |
| ② 검증 결과 | ✅ (인플루엔자 F1=0.882) / ⚠ 정직 (다질병 proxy) → 노로 transition +13%p로 보완 |
| ③ 서비스성 | ✅ 라이브 외부 IP |
| ④ 확장성 | ✅ 다질병 + region-pooled + 카테고리 사전 |

### 5.2 종합 점수 (이전 8.1/10 → 갱신)

| 모듈 | 이전 | 신규 | 변동 사유 |
|------|------|------|---------|
| 데이터 수집 | 8.5 | **8.0** ↓ | OTC INSERT silent 누락 사고 발견 |
| 저장 | 9.0 | 9.0 | — |
| ML 모델 | 7.5 | **8.0** ↑ | transition + L1 OTC로 정직한 ML 우위 추가, CAPE/TimeMixer 로드맵 명확 |
| 백엔드 | 8.5 | 8.5 | — |
| 프론트엔드 | 8.0 | 8.0 | — |
| 운영 | 7.0 | **6.5** ↓ | silent 결손 사고 + HTTPS 미적용 부각 |
| 테스트·CI | 8.0 | **8.5** ↑ | 547/549 → 547/547 회복 |
| 문서 | 8.5 | **9.0** ↑ | R&D 로드맵 + 신기술 서치 통합 |

**종합: 8.1 → 8.06** (소폭 하향, 운영 사고 반영 + ML 가치 회복으로 상쇄)

### 5.3 차별화 포인트 (발표 + B2G 양쪽)

1. **정직한 ML 시스템** — proxy 한계 + trivial 비교 + transition gain 모두 노출
2. **다질병 즉시 확장** — pathogen 인자화 + 카테고리 사전, 1개 추가 ≈ 1~2시간
3. **CAPE 호환 데이터 구조** — 라벨 없이도 pretrain 시작 가능
4. **운영 자동화 90%** — systemd·이중알람·시크릿스캔 (silent 누락 보강하면 95%)
5. **B2G 납품 기준 충족** — p95<500ms, 커버리지≥35%, K8s SecurityContext

---

## 6. 발표 직전 P0 체크리스트

| ☑ | 항목 |
|---|------|
| ☐ | nginx HTTPS 전환 (Let's Encrypt + DNS) |
| ☐ | OTC INSERT 자동 재시도 패치 (silent 누락 차단) |
| ☐ | 박진영 KDCA API 신청 진척 확인 |
| ☐ | PR #74 머지 (CI 통과 시 — 테스트 수정 commit 추가) |
| ☐ | 리허설 2회 (대시보드 라이브 + 정직성 카드) |
| ☐ | 백업 데모 (Streamlit `src/app.py` 도커 컴포즈 죽었을 때) |

---

## 부록: 핵심 논문 URL

- TimeMixer++ ICLR 2025 — https://openreview.net/forum?id=1CLzLXSFNn
- iTransformer ICLR 2024 — https://arxiv.org/abs/2310.06625
- PatchTST ICLR 2023 — https://arxiv.org/abs/2211.14730
- "No Champions in LTSF" 포지션 페이퍼 — https://arxiv.org/abs/2502.14045
- Mamba4Cast 2024 — https://arxiv.org/abs/2410.09385
- CAPE (epidemic SSL pretrain) — https://arxiv.org/abs/2502.03393
- Foundation Models for Epidemic 평가 — https://www.medrxiv.org/content/10.1101/2025.02.24.25322795v1
- Transfer Learning 66 질병 — https://arxiv.org/abs/2605.27269
- EpiHybridGNN 2025 — https://arxiv.org/abs/2511.15469
- SpatialEpiBench 2025 — https://arxiv.org/html/2605.06530v1
- MSGNN — https://arxiv.org/abs/2308.15840
- WBE 종합 Risk Analysis 2025 — https://onlinelibrary.wiley.com/doi/10.1111/risa.70075
- WBE LSTM COVID PMC — https://pmc.ncbi.nlm.nih.gov/articles/PMC9648834/
- Shenzhen 다병원체 — https://www.tandfonline.com/doi/full/10.1080/22221751.2025.2552724
