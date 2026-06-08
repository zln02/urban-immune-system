# 데모 백업 자료 — 2026-06-17 최종발표

> 생성: 2026-06-08 (D-9) · 발표 D-day fail-safe 용. 발표장 네트워크 끊김 / dev 서버 다운 / 외부 IP 차단 등 모든 케이스 대비.

## 📦 캡처 목록 (7장)

| 파일 | 화면 | 용도 |
|---|---|---|
| `01_landing.png` | 루트 `/` 랜딩 | 인트로 / B2G 비전 슬라이드 보조 |
| `02_dashboard_influenza.png` | `/dashboard` 인플루엔자 viewport (1920×1080) | **메인 데모 — 17지역 지도 + F1 0.907 KPI** |
| `03_dashboard_influenza_full.png` | 위 full scroll | 검증 매트릭스·Granger·SHAP 포함 (전체 자료) |
| `04_dashboard_covid.png` | COVID-19 viewport | **다질병 시연 — F1 0.68** |
| `04_dashboard_covid_full.png` | COVID full scroll | 다질병 정직성 caveat 포함 |
| `05_dashboard_norovirus.png` | 노로바이러스 viewport | **다질병 시연 — F1 0.70** |
| `05_dashboard_norovirus_full.png` | 노로 full scroll | transition target 우위 검증 |

## 🎬 발표 시연 큐 (12분 흐름 기준)

### 0:00–3:00 인트로 + 문제 정의 (슬라이드만)
- S01 COVER → S05A DATA RATIONALE (슬라이드 deck 그대로)

### 3:00–6:00 데모 ← 라이브 시연 시도, fail-safe = PNG
1. **메인 대시보드 열기** ← `02_dashboard_influenza.png` 백업
   - 17지역 지도 (시안색 강조)
   - KPI: **F1 0.907 / Lead 6.76주 / Composite 19.58**
   - 발화: "임상보다 6.76주 먼저, F1 0.907 (KDCA 라벨 기준 0.96)"

2. **검증 매트릭스 스크롤** ← `03_dashboard_influenza_full.png` 백업
   - Precision 0.940 / Recall 0.882 / FAR 0.250
   - Granger composite p=0.021 / L3 p=0.007

3. **pathogen 셀렉터 클릭 — COVID** ← `04_dashboard_covid.png` 백업
   - F1=0.68 + "베타" 라벨
   - 발화: "OTC 신호 약함, transition target 으로 0.55→0.68 개선"

4. **pathogen 셀렉터 클릭 — 노로** ← `05_dashboard_norovirus.png` 백업
   - F1=0.70, 단기 폭발 패턴
   - 발화: "한 시스템, 세 질병 검증 — 캡스톤 평가 4번째 항목 ✅"

### 6:00–9:00 검증 결과 + 정직성 (슬라이드)
- S11 → S11A → **S11B (다질병) ← 위 PNG 보조** → S12 → S12A → S13B/C/D

### 9:00–12:00 마무리 (슬라이드)
- S15 6주 회고 → S14A 9주 Evolution → S14 비전 → S16 팀 → S16A Q&A

## 🔧 발표장 환경 체크리스트 (발표 30분 전)

```bash
# 1. 시연 환경 사전 검증
ssh wlsdud5035@34.47.113.176
curl -s http://localhost:3000/dashboard -o /dev/null -w "frontend %{http_code}\n"
curl -s http://localhost:8001/api/v1/health -o /dev/null -w "backend %{http_code}\n"

# 2. 외부 노출 URL (Basic Auth)
# http://34.47.113.176  → 401 (Auth prompt) → admin:<PW>

# 3. fail-safe — 이 디렉토리 PNG 들 노트북 로컬에 미리 다운로드
scp -r wlsdud5035@34.47.113.176:~/urban-immune-system/docs/runbook/demo-backup-2026-06-08/*.png ./presentation_backup/
```

## ⚠️ 알려진 임시 한계 (사전 공유)

발표 시연 시 자연스럽게 언급될 한계 — 슬라이드 S13C/D 정직성과 일치:

- **L1/L3 전국 단일값 → 17지역 broadcast** (네이버 API 제약) — 지도에서 시도별 색이 같아 보일 수 있음
- **L2 carry-forward 60.7%** (PR #82 audit) — 트렌드 그래프에서 같은 값 연속 보이면 정직 언급
- **F1=0.907 = self-proxy** + V11.6 KDCA 0.96 — KPI 카드 옆 caveat 라인 명시

## 📂 관련 자료

- 슬라이드 22 scene 캡처: `/home/wlsdud5035/.claude/jobs/c42ab097/tmp/slides/all_*.png` (배포 폴더 X, 임시 캐시)
- V12 메트릭 노트: `presentation/V12_metric_notes.md`
- KOWAS audit: `analysis/outputs/kowas_carry_forward_audit.json`
- KDCA validation: `analysis/outputs/label_validation_influenza.json`
- KDCA 재학습: `analysis/outputs/backtest_xgboost_influenza_kdca_17regions.json`
