# Model Card — Urban Immune System (UIS)

> 마지막 갱신: 2026-05-03 · 발표 D-4 시점 기준
> 형식: Hugging Face Model Card 표준 + Mitchell et al. (2019) "Model Cards for Model Reporting" 권고
> Canonical 메트릭 출처: `analysis/outputs/backtest_17regions.json` (17지역 walk-forward 5-fold gap=4주)

본 카드는 B2G(질병관리청·지자체) 납품 후보 시스템의 정직성 확보용 표준 문서이다. 발표·자문·심사 자리에서 인용 가능한 단일 출처.

---

## 1. Model Details

### 1.1 모델 구성 (앙상블)

| 모델 | 역할 | 체크포인트 | 학습 데이터 | 파라미터 |
|---|---|---|---|---|
| **XGBoost** | 주모델 (회귀 + 게이트 B) | `ml/checkpoints/xgb_best.joblib` | 17지역 × 26주 실데이터 | n_estimators=200, depth=4 |
| **TFT (real)** | 7/14/21일 선행 예측 + Attention 해석 | `ml/checkpoints/tft_real/tft_best.ckpt` | 17지역 × 26주 실데이터 | 70K (재학습 후) |
| **TFT (synth)** | Attention 검증 보조 | `ml/checkpoints/tft_synth/tft_best-v2.ckpt` | 합성 104주 | 148K |
| **Autoencoder** | 신종 패턴 이상탐지 (라벨 없음) | `ml/checkpoints/autoencoder/model.pt` | 17지역 정상 패턴 | (재구성 99p) |
| **RAG (Claude Haiku)** | 경보 리포트 생성 | Qdrant `epidemiology_docs` 20건 | WHO·ECDC·KCDC 가이드 | top_k=5 |

### 1.2 개발 정보
- **개발자**: 박진영(PM/ML), 이경준(Backend), 이우형(Data), 김나영(Frontend), 박정빈(DevOps/QA)
- **소속**: Urban Immune System 캡스톤 팀 (학부, 5명)
- **공개일**: 2026-05-07 (중간발표 시점, v0.2)
- **모델 버전**: 0.2.0 (`backend/app/main.py` `version="0.2.0"`)
- **라이선스**: MIT (소스코드). 단 학습 데이터·임베딩 자료는 별도 라이선스 (§7 참조)
- **연락처**: GitHub Issues `zln02/urban-immune-system`

### 1.3 의도된 사용 (Intended Use)
- **1차 용도**: 보건당국 의사결정 보조 자료 (광역 단위 감염병 위험도 지수)
- **사용 주체**: 질병관리청, 광역 지자체 역학조사과, WHO 협력센터
- **결정 권한**: AI 단독 결정 금지 — 모든 경보는 보건 전문가 검토 후 정책 결정
- **금지 용도**:
  - 임상 진단·처방·치료 결정
  - 개인별 감염 여부 판단
  - 공중보건 정책 자동 발령
  - 의료기기 (의료기기법 제2조 비해당, `advisory_pdf.py:192,377` 면책 고지 강제)

---

## 2. Performance (17지역 walk-forward, gap=4주, 5-fold)

### 2.1 핵심 지표 (Canonical: `analysis/outputs/backtest_17regions.json` summary)

| 지표 | 값 | 목표 | 충족 |
|---|---|---|---|
| F1 (mean) | **0.882** | ≥ 0.80 | ✅ |
| Recall (mean) | **0.837** | ≥ 0.85 | ⚠️ 미달 (직전 0.768→0.837 향상) |
| Precision (mean) | **0.949** | ≥ 0.90 | ✅ |
| FAR (gate ON) | **0.206** | ≤ 0.30 | ✅ |
| FAR (gate OFF) | 0.602 | — | (게이트 효과 65.8% 감소) |
| MCC | **0.595** | ≥ 0.50 | ✅ |
| Balanced Accuracy | **0.816** | ≥ 0.75 | ✅ |
| AUPRC | **0.973** | ≥ 0.85 | ✅ |
| Lead time (평균) | **6.47주** | ≥ 4주 | ✅ |
| Lead time (최장) | 9주 (세종) | — | — |

### 2.2 지역별 lead time
세종 9주 / 부산·제주 8주 / 서울 7주 / 경기·인천 등 12지역 6주.

### 2.3 통계적 선행성 (Granger 인과검정, 서울 단일 분석)
- composite p = 0.021 (< 0.05 ✅)
- L3 검색 p = 0.007 (가장 강함)
- L1 OTC p = 0.103 (약한 선행)
- L2 하수 p = 0.267 (데이터 부족)
- 출처: `analysis/outputs/lead_time_summary.json`

### 2.4 운영 성능
- API p95 latency = **13ms** (목표 500ms 대비 97% 여유, `tests/load/results/uis_stats.csv`)
- 17개 시·도 동시 처리, 통합 테스트 113건 + 부하 테스트 통과

---

## 3. Training Data

### 3.1 출처
| 계층 | 소스 | 주기 | 단위 |
|---|---|---|---|
| L1 OTC | 네이버 쇼핑인사이트 (감기약·해열제·종합감기약·타이레놀·판콜) | 주 1 (월 09:00) | 전국 단일값 → 17지역 broadcast |
| L2 하수 | KOWAS PDF (인플루엔자 RT-PCR copies/mL) | 주 1 (화 10:00) | 광역 단위 |
| L3 검색 | 네이버 DataLab (독감 증상·인플루엔자·고열·몸살·타미플루) | 주 1 (월 09:05) | 전국 단일값 → 17지역 broadcast |
| AUX | 기상청 KMA (기온) | 시간 단위 | 광역 단위 |

### 3.2 한계
- **L1·L3 17지역 broadcast 한계**: 네이버 API는 전국 단일값만 제공. 17지역 동일값 복제 (`pipeline/collectors/otc_collector.py` zero-collapse 핫픽스 `07c9c5a` 이후). HIRA OpenAPI 연동(Phase 3)으로 시·군·구 분리 예정.
- **L2 KOWAS 자동 크롤링**: 현 PDF 수동 추출 → Phase 3 Selenium 자동화 예정.
- **데이터 기간**: 26주 (2025-09 ~ 2026-03 인플루엔자 시즌). TFT 발산 위험 → 12주 추가 누적 후 (12,2)→(24,3) 재시도.

### 3.3 전처리
- Min-Max 정규화 0~100 (계층별 독립 적용)
- 빈 리스트 → `[]` 반환, 상수값 입력 → `[50.0]*n` (ZeroDivision 방지)
- L1·L3 zero-collapse 방어: 비수기 raw=0.98 → value=0 사고 회귀 테스트 (`test_naver_data_quality.py::TestBackfillZeroCollapse`)

---

## 4. Evaluation

### 4.1 검증 방법
- **시간순 walk-forward**: `TimeSeriesSplit(n_splits=5, gap=4)` — 4주 갭으로 미래 누출 차단
- **합성 vs 실측 분리 평가**: `ml/outputs/validation.json` 의 fold 1-3 NaN 은 합성 데이터 양성 클래스 부재 (104주에서 4 fold 비양성), 실측 17지역은 모두 양성 클래스 충분
- **재현 명령**: `python -m ml.reproduce_validation` 1줄로 시드 고정 (`pl.seed_everything(42, workers=True)` + `deterministic=True`)

### 4.2 게이트 B (Cross-Validation Gate)
- **규칙**: 2개 이상 계층이 ≥ 30 점 (`_CROSS_VALIDATION_LAYER_THRESHOLD=30.0`, `_CROSS_VALIDATION_MIN_LAYERS=2`) 충족 시에만 YELLOW 이상 발령
- **L3 단독 경보 절대 금지** (Google Flu Trends 과대예측 교훈)
- **Ablation**: 게이트 ON FAR 0.206 vs 게이트 OFF FAR 0.602 → **65.8% 감소**

### 4.3 비교 (글로벌 시스템)
| 시스템 | 신호 수 | 특징 | UIS 차이 |
|---|---|---|---|
| BlueDot | 단일 (뉴스) | 발병 보고 NLP | UIS는 비의료 신호 3계층 |
| CDC NWSS | 단일 (하수) | 미국 하수 감시 | UIS는 OTC + 검색 추가 |
| HealthMap | 단일 (뉴스·SNS) | 클러스터링 | UIS는 통계적 선행성 검증 |
| WHO EIOS | 다중 (뉴스 등) | 국제 통합 | UIS는 국내 광역 단위 |
| KCDC ILINet | 단일 (보건소 표본) | 임상 기반 | UIS는 비의료 선행 신호 |

---

## 5. Limitations

### 5.1 데이터 제약
- 단일 질병 (인플루엔자) 학습. 다른 호흡기 감염병 (코로나·RSV) 일반화 미검증
- 26주 단일 시즌 → 시즌 간 변동성 미검증
- 한국 17개 광역 단위. 시·군·구 미세 단위 미지원 (Phase 3 HIRA OpenAPI)
- 인구 100만 미만 광역 (세종·제주) 표본 크기 제한

### 5.2 모델 한계
- **Recall 0.837** 은 목표 0.85 미달 (게이트 B 보수적 정책 trade-off)
- **TFT-real** val_loss 9.59 (데이터 부족 capacity 축소). 발표 데모는 XGBoost 주모델 + TFT attention 시각화만 사용
- **Autoencoder synthetic 평가** F1=0.097, Precision=0.051 (인공 spike 기준) — 발표 인용 금지. 실 17지역 추론은 1/17 anomaly 정상화 (`ff17dfa` 99p 핫픽스)

### 5.3 운영 한계
- **인증 미들웨어 추가됨** (#42, ISMS-P 2.5.1). production 1+ API key 강제. 단 사용자 권한 분리(RBAC) 미구현
- **감사로그·Rate limit 추가됨** (#42). 다만 다중 인스턴스 확장 시 Redis 백엔드 교체 필요
- ISMS-P 정식 인증 미취득 (Phase 4 예정)
- KOSA SW사업자 신고 미진행 (조달청 등록 6개월 전 필요)

---

## 6. Ethical Considerations

### 6.1 의료기기 비해당
- 처리 데이터: 약국 OTC 구매 지수 (집계), 하수 바이러스 농도 (집계), 검색어 트렌드 (집계)
- 출력: 광역 단위 위험도 지수 + AI 보조 리포트
- 임상 진단·치료 의도 없음 (의료기기법 제2조 비해당)
- 다층 면책 고지: `advisory_pdf.py:192,377`, `report_pdf.py`, `CHATBOT_KNOWLEDGE.md`

### 6.2 개인정보
- 모든 입력 데이터는 광역 단위 집계 통계 (수십만~수천만 인구 평균)
- 개인 식별자 (PI) 컬럼 부재 (`infra/db/init.sql` 검증)
- 다른 정보와 결합해도 특정 개인 식별 불가 (개인정보보호법 제2조 1호 비해당, 자체 검토)
- DPIA 초안: `docs/business/advisory/22_dpia_draft.md` (Phase 4 변호사 검토)

### 6.3 신고 의무 안내
- RED 경보는 감염병예방법 제11조·15조의 신고 의무를 **대체하지 않음**. 본 시스템은 의사결정 보조 자료이며, 법정 감염병 의심 시 보건당국 신고 필요. (납품 계약서 명시 예정 — P2)

### 6.4 편향 및 공정성
- **지역 편향**: L1·L3 broadcast 한계로 인구 적은 광역(세종·제주)이 대도시(서울·경기) 신호에 끌려갈 가능성. Phase 3 HIRA OpenAPI 로 보정 예정
- **계절 편향**: 인플루엔자 시즌(9~3월) 학습 → 비시즌 일반화 미검증
- **언어 편향**: L3 검색 키워드 한국어 한정 → 외국인 거주 지역 대표성 제한

---

## 7. License & Usage Terms

### 7.1 소스코드
- MIT License (`LICENSE`)
- Copyright (c) 2026 Urban Immune System Team

### 7.2 학습 데이터·임베딩 라이선스
| 자료 | 라이선스 | 재배포 가능 여부 | 비고 |
|---|---|---|---|
| 네이버 쇼핑인사이트·DataLab | 네이버 개발자센터 이용약관 | ❌ 재판매·재배포 금지 (제9조) | Tier B 건당 리포트 사업화 보류 (P2 공식 질의) |
| KOWAS PDF (환경부·KCDC) | 공공데이터법 제17조 | 출처 명시 시 2차 이용 가능 | 프론트엔드 출처 표기 추가 (P2) |
| KMA 기상 API | 기상청 공공데이터 | 비영리·교육 가능, 상업적 이용 별도 협의 | — |
| RAG 임베딩 (WHO·ECDC·KCDC 가이드) | 각 기관 별도 약관 | 인용·요약 가능, 원문 재배포 금지 | 출처 자동 인용 |

### 7.3 모델 체크포인트
- `ml/checkpoints/` 는 .gitignore (용량 + 학습 데이터 라이선스 보호)
- 납품 시 별도 패키지 (Tier C PoC 종료 산출물)

---

## 8. Reproducibility

### 8.1 환경
- Python 3.11 / PyTorch 2.x / pytorch-forecasting 1.0 / pytorch-lightning 2.x
- TimescaleDB / Kafka KRaft / Qdrant
- 단일 노드: GCP e2-standard-2 (4 vCPU, 16GB RAM), Debian 12

### 8.2 1줄 재현 명령
```bash
python -m ml.reproduce_validation
```
시드: `pl.seed_everything(42, workers=True)` + Trainer `deterministic=True`. 동일 환경에서 동일 수치 재현 보장.

### 8.3 단계별 재학습
```bash
# XGBoost 주모델
python -m ml.xgboost.train_real
# TFT 실데이터
python -m ml.tft.train_real --epochs 30 --min-weeks 14
# Autoencoder
python -m ml.anomaly.train_synth
```

---

## 9. Versions & Changelog

| 버전 | 일자 | 주요 변경 |
|---|---|---|
| 0.1 (alpha) | 2026-04-15 | Streamlit MVP + 합성 데이터 |
| 0.2.0 (캡스톤 중간) | 2026-05-07 | 17지역 실데이터 + 게이트 B + RAG + ISMS-P 미들웨어 + Granger 검정 |
| 0.3 (예정) | 2026-06 | 최종 발표 + 1개 추가 질병 시연 + ISMS-P self-assessment |
| 1.0 (예정) | 2026-Q4 | KDCA·서울시 PoC 완료 + 조달청 혁신제품 신청 |

---

## 10. Contact & Citation

### 10.1 인용
```bibtex
@misc{uis2026,
  title  = {Urban Immune System: Cross-Validated 3-Layer Early Warning for Infectious Disease},
  author = {Park, Jinyoung and Lee, Kyungjun and Lee, Woohyung and Kim, Nayoung and Park, Jeongbin},
  year   = {2026},
  url    = {https://github.com/zln02/urban-immune-system}
}
```

### 10.2 버그·문의
- GitHub Issues: https://github.com/zln02/urban-immune-system/issues
- B2G PoC 협력 문의: 발표 후 외부 자문 패키지(`docs/business/uis-advisory-package-W18.zip`) 발송

---

> 본 모델 카드는 B2G 납품·자문 자료 표준 첨부 문서이다. 변경 시 `analysis/outputs/backtest_17regions.json` summary 와 1:1 대조 후 갱신.
