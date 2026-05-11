# feat(uis): P0 ML reconnect + coverage 47→64% + isolation fix

## Summary
Round 1~5 통합 PR. 직전 세션 대비 주요 변경:

- **P0 ML 미연결 fix**: GET→POST /predict/tft-7d + .env 경로 수정 (ml/serve.py)
- **커버리지 폭증**: backend/ml/pipeline 주요 모듈 47%→64% (pytest --cov)
  - signals.py 44→100%, report_pdf.py 16→94%, scorer.py 37→81%, kowas_loader.py 40→87%, reproduce_validation.py 0→68%
- **약점 방어**: cv_limitations.md 130줄 추가 (단일시즌 한계, recall 0.837 정직 처리)
- **systemd 서비스**: uis-ml.service active(running), POST /predict/tft-7d 정상 확인
- **격리 fix** (035107b): asyncio.get_event_loop() → asyncio.run() 교체 (Python 3.10+ 격리 보장)

## Commits
035107b fix(test): replace get_event_loop() with asyncio.run() in test_report_pdf
5c3fab3 docs(claude-md): add Worker DoD — mandate pytest tests/ before commit
4f55b0a docs: draft PR description for w19 branch
ade818a test(api-signals): cover routes + region params + fallback (44% -> 100%)
8959b94 test(report-pdf): cover PDF generation paths (16% -> 94%)
9d3a1a7 test(ml): smoke tests for train scripts + @pytest.mark.slow marker
733c917 test(reproduce-validation): cover argparse + seed reproducibility (0% -> 68%)
cea866f infra(systemd): add uis-ml.service for ML inference
340dbbf test(prediction-service): align test mocks with POST /predict/tft-7d
1edd2bf test(kowas-loader): cover skip_db + DB INSERT + fallback paths (40% -> 87%)
63363c8 test(scorer): cover asyncpg.Pool paths (37% -> 81%)
e112583 docs(arch): add CV fold NaN limitation analysis
7528342 fix(prediction-service): match ml/serve.py endpoint contract
2ac79f7 docs: add IP action guide for SW copyright + patent TLO consultation
4c08583 feat(tests): boost coverage 39%→47%, add fallback logic, fix CI gate
d5e4a18 chore: cleanup slides artifacts, add team guide and docs

## Verification
- [x] pytest tests/ — 319 passed, 3 skipped, 0 failed
- [x] 전체 커버리지: 64% (CI gate --cov-fail-under=62 통과)
- [x] ML 서비스: POST /predict/tft-7d → 서울 [18.04] 정상
- [x] anomaly 17지역 정상 (대전 score=90.6)
- [x] CI gate --cov-fail-under=62 (45→62 상향)

## Risks
- scorer.py 임계값 미변경 (C2 recall 0.841/FAR 0.235, C3 recall 0.844/FAR 0.250 모두 거부) → recall 0.837 현행 유지
- ml/serve.py systemd 신규 도입 → 서버 재부팅 시 자동 시작 테스트 필요
- test_report_pdf 격리 사고 (전체 suite에서만 실패) → isolation fix 포함

## Roadmap
- Gate B recall 0.85 후속: 충북(0.529)·대구(0.647)·경북(0.647) L2 약함 → 지역별 차등 임계값 또는 모델 재학습
- 커버리지 70% 잔여 모듈 booster
- K8s 마이그레이션 (P1)
- KOWAS 실시간 스케줄러 안정화 (P1)
