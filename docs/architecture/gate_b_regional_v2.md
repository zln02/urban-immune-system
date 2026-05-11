# Gate B Regional Threshold Tuning v2

**작성일**: 2026-05-11  
**작성자**: 박진영 (PM / ML Lead)  
**브랜치**: feature/gate-b-regional-tuning  
**상태**: 설계안 (구현 대기)

---

## 1. 배경 및 목표

현행 Gate B (Cross-Validation Layer)는 17개 전 지역에 동일 임계값을 적용한다.

| 지표 | 현재 (v1) | 목표 (v2) |
|------|----------|----------|
| mean recall | 0.844 | **≥ 0.85** |
| mean F1 | 0.881 | ≥ 0.885 |
| mean FAR | 0.250 | ≤ 0.250 (유지) |

현행 `gate_config`:
```json
{
  "cross_validation_min_layers": 2,
  "cross_validation_layer_threshold": 20.0,
  "red_threshold": 75.0
}
```

---

## 2. 병목 지역 진단 (backtest_17regions.json 실측)

### 2-1. Bottom-3 지역 상세 지표

| 지역 | recall | precision | FAR | F1 | TP | FN | MCC | AUPRC |
|------|--------|-----------|-----|----|----|----|-----|-------|
| 충청북도 | **0.5294** | 0.9000 | 0.250 | 0.6667 | 9 | **8** | 0.220 | 0.917 |
| 대구광역시 | **0.6471** | 1.0000 | 0.000 | 0.7857 | 11 | 6 | 0.509 | 0.970 |
| 경상북도 | **0.6471** | 1.0000 | 0.000 | 0.7857 | 11 | 6 | 0.509 | 0.980 |

*21주 분석 기간, peak_week: 2025-W50*

### 2-2. 핵심 관찰

- **충청북도**: FN=8 로 3지역 중 가장 심각. Gate-off(recall_no_gate=0.875) 대비 Gate-on(0.529)의 낙폭이 -0.346으로 최대. 현행 min_layers=2 / layer_threshold=20 조합이 이 지역 신호를 과도하게 차단 중.
- **대구·경북**: FAR=0.0 (오탐 0건) 임에도 recall=0.647. 위양성을 허용해도 recall을 올릴 여지가 있음. Gate-off recall(0.875) 대비 낙폭 -0.228.
- **공통**: AUPRC ≥ 0.917로 모델 자체 순위 성능은 양호 → 문제는 이진 임계값(layer_threshold), 모델 품질이 아님.

### 2-3. 전체 지역 recall 분포 요약

```
≥ 0.94 : 경기, 인천, 대전, 광주, 충남, 부산, 세종, 제주  (8개)
0.88   : 강원, 전북, 경남                                  (3개)
0.76   : 서울                                              (1개)
0.71   : 울산, 전남                                        (2개)
≤ 0.65 : 대구, 경북, 충북                                  (3개)  ← 병목
```

---

## 3. 설계 옵션

### 옵션 A — min_score 차등 (layer_threshold 지역별 분리)

Gate B의 `cross_validation_layer_threshold` 를 지역 티어별로 분리한다.

```python
REGIONAL_GATE_CONFIG = {
    "strong": {
        # recall ≥ 0.88 지역 (12개): 현행 유지
        "regions": [...],
        "layer_threshold": 30.0,   # 현행 20 → 30 (오탐 방어 강화)
    },
    "weak": {
        # recall ≤ 0.71 지역 (5개: 충북·대구·경북·울산·전남)
        "regions": ["충청북도", "대구광역시", "경상북도", "울산광역시", "전라남도"],
        "layer_threshold": 20.0,   # 현행 유지 또는 15로 완화 검토
    }
}
```

- **장점**: 구현 단순, L2 데이터 불필요
- **단점**: 강한 지역 threshold 상향 시 FAR 소폭 상승 가능
- **충북 예상 recall 변화**: threshold 20→15 시 FN 8→4~5 (추정, 시뮬레이션 필요)

### 옵션 B — 지역별 L2 가중치 상향

scorer.py의 레이어별 가중치 `w2` (L2 신호)를 약한 지역에 한해 상향한다.

```python
# 현행
LAYER_WEIGHTS = {"w1": 0.35, "w2": 0.35, "w3": 0.30}

# 약한 지역 오버라이드
WEAK_REGION_WEIGHTS = {"w1": 0.30, "w2": 0.50, "w3": 0.20}
```

- **장점**: recall 회복에 L2 신호가 충분히 풍부할 경우 정밀도 유지 가능
- **단점**: L2 (SNS/뉴스 레이어) 데이터 밀도가 낮은 지역에서는 역효과 가능
- **전제 조건**: 약한 5개 지역의 L2 mean score ≥ 0.3 임을 사전 확인 필요

---

## 4. 권고 (결정 트리)

```
L2 데이터 밀도 체크
  └─ 약한 5개 지역 L2 mean ≥ 0.3 ?
        ├─ YES → 옵션 B (L2 가중치 0.40→0.50)
        │         + 옵션 A 보조 적용 (threshold 20→15)
        └─ NO  → 옵션 A 단독 (threshold 20→15)
                  (L2 데이터 확보 전까지 구조 단순하게)
```

**현 시점 권고**: 충북의 L2 데이터 빈약 가능성 높음 (내륙 소도시, SNS 밀도 낮음).  
→ **옵션 A 우선 적용**, 백테스트 재실행 후 recall delta 확인 후 옵션 B 병행 검토.

---

## 5. 구현 영향 범위

| 파일 | 변경 내용 | 담당 |
|------|----------|------|
| `backend/app/config.py` | `REGIONAL_GATE_CONFIG` dict 추가, 지역 티어 매핑 | 이경준 (Backend) |
| `ml/anomaly/scorer.py` | `get_layer_weights(region)` 함수 추가, 약한 지역 w2 오버라이드 | 박진영 (ML) |
| `analysis/scripts/backtest_regional.py` | 신규 임계값으로 재백테스트 스크립트 | 박진영 (ML) |
| `tests/test_gate_b_regional.py` | 지역별 임계값 분기 단위 테스트 | 박정빈 (QA) |

---

## 6. 리스크 및 완화

### 6-1. FAR 증가

threshold 완화 시 오탐이 늘어날 수 있다. 현행 참고 수치:

| 지역 | 현행 FAR | gate-off FAR |
|------|---------|-------------|
| 충청북도 | 0.250 | 0.231 |
| 대구광역시 | 0.000 | 0.308 |
| 경상북도 | 0.000 | 0.308 |

threshold 완화 후 FAR 상한: **0.30 이하** 유지를 기준으로 삼는다.  
(전체 mean FAR 허용 상한 = 0.27, 현행 대비 +0.02 마진)

### 6-2. 다중 기준 충돌

FAR-recall 트레이드오프: 제주(FAR=0.75)처럼 recall=1.0이지만 FAR 폭등 패턴을 참고하면,  
무조건 threshold 낮추기는 위험. B2G 납품 기준(오탐 최소화) 상 **FAR ≤ 0.30 하드 캡** 권장.

### 6-3. C2/C3 FAR 참고

- C2 시나리오 FAR: 0.235
- C3 시나리오 FAR: 0.250

옵션 A 적용 후 weekly FAR 모니터링에서 C3(0.250) 초과 시 threshold 재조정 필요.

---

## 7. 다음 단계

- [ ] L2 mean score 확인 (`analysis/scripts/l2_density_check.py` 신규 작성)
- [ ] 옵션 A threshold 15 적용 후 `backtest_17regions.py` 재실행
- [ ] recall ≥ 0.85 달성 확인 + FAR ≤ 0.27 검증
- [ ] `backend/app/config.py` + `ml/anomaly/scorer.py` 구현 (PR 별도)
- [ ] `tests/test_gate_b_regional.py` 커버리지 ≥ 70% 확인

---

*이 문서는 설계 검토용이며 코드 변경을 포함하지 않는다.*
