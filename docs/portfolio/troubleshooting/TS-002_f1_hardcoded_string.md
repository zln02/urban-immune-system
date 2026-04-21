# TS-002: README F1=0.71 주장이 계산 없이 하드코딩 문자열이었던 문제

- **발생**: 2026-04-21 (감사 중 발견)
- **모듈**: ml / docs
- **담당자**: @zln02 (박진영)
- **심각도**: 🔴 Blocker (캡스톤 심사 Q1 치명타 가능성)

## 증상
README 에 `"F1=0.71 · Precision=1.00 (오경보 0건) · Granger p<0.05"` 주장이 있으나, 심사위원이 "계산 코드 어디 있나요?" 물어도 답할 수 없는 상태.

## 원인 추적
- **시도 1**: `grep 0.71 src/` → `src/tabs/validation.py` L43 에서 발견
- **시도 2**: 해당 라인 확인 → **하드코딩된 문자열 배열**
  ```python
  "F1-Score": ["0.00", "0.62", "0.33", "0.71", "0.71", "0.71"]
  ```
- **시도 3**: `grep "0.05" src/` → `correlation.py` L20-30 에 `p < 0.05` **HTML 텍스트만** 박힘
- **시도 4**: `grep -r "f1_score\|grangercausalitytests" .` → 호출 0건
- **근본 원인**: sklearn/statsmodels 실제 호출 없이 값이 기획 단계에서 고정된 채 운영

## 해결
1. `analysis/notebooks/performance_measurement.py` 신규 작성:
   - sklearn `f1_score`, `matthews_corrcoef`, `average_precision_score`
   - statsmodels `grangercausalitytests(maxlag=4)`
   - 재현성 위해 `seed=42` 합성 데이터 사용 (실데이터 확보 시 `--real` 플래그 예정)
2. `ml/outputs/validation.json` · `correlation.json` 자동 생성
3. `src/tabs/validation.py`, `correlation.py` → JSON 로드 + 동적 렌더로 교체
4. README 수치 교체: **F1=0.643 · MCC=0.442 · AUPRC=0.885 · FP=10** (합성 데이터 기반, 재현 가능)
5. "Precision=1.00 오경보 0건" 단독 표기 삭제

커밋: [4102916](https://github.com/zln02/urban-immune-system/commit/4102916)

## 배운 점 (재발 방지)
1. **수치 주장은 반드시 재현 코드와 함께** — README 수치 업데이트 시 `scripts/` 또는 `notebooks/` 에 실행 경로 명시
2. **CI 에 수치 재현 테스트 추가** — 노트북 실행 → JSON 출력 → README 수치 grep 일치 검증
3. **Precision 단독 보고 위험** — 클래스 불균형 시 자동 1.00 나옴. MCC/AUPRC + N 병기 원칙
4. **공모전 주장 ≠ 실측 수치** — 기획서 제출 직후 실측 코드를 즉시 붙여야 함

## 재발 방지 액션
- [ ] `tests/test_metrics_reproducibility.py` 추가: 노트북 실행 → JSON 수치가 README 표와 일치하는지 검증
- [ ] `.github/workflows/ci.yml` 에 `metrics-check` Job 추가
- [ ] 매주 월요일 `scripts/update_metrics_history.py` 실행 → `metrics-history.md` append

## 관련 커밋 / PR
- 4102916 (P0 복구 + 팔레트 + 스코어보드)
- PR #2 포함
- 관련 FAQ: FAQ-002 (F1 측정 방법)
