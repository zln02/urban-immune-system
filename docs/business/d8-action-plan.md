# 캡스톤 중간발표 D-8 작업 플랜 (5/7 발표 기준)

> 작성: 2026-04-29 · 발표: 2026-05-07 · 잔여 8일

## 우선순위 매트릭스

| # | 작업 | 분류 | 소요 | 담당 |
|---|---|---|---|---|
| 1 | TFT 실데이터 prod 전환 | ML | 4~5일 | 박진영 |
| 2 | 외부 자문 자료 발송 | 행정 | 2일 + 5일 회수 | 박진영 |
| 3 | 발표 리허설 2~3회 | 발표 | 2일 (분산) | 전원 |
| 4 | 데모 백업 영상 인코딩 | 데모 | 1일 | 김나영 |
| 5 | S07E 본문 복귀 | 슬라이드 | 5분 | 자동 완료 |
| 6 | 데모 시나리오 동선 | 발표 | 1일 | 박진영·김나영 |

---

## 1. TFT 실데이터 prod 전환 (★★★)

### 현재 상태 (진단 완료)

✅ 인프라 80% 완성:
- 엔드포인트 3개: `/predict/tft-7d|14d|21d`
- 체크포인트 자동 로드 (`tft_synth/tft_best-v2.ckpt` · 79K params · val_loss 1.88)
- Attention top-3 반환

⚠ 미완 — 합성 데이터로 추론:
- `ml/serve.py:_make_tft_predictions` 가 `_make_dataframe(seed=42)` 합성 사용
- 실 DB `layer_signals` 26주 누적 데이터 미사용

### Day-by-day 계획

**D-7 (4/30~5/1)**: 실데이터 추론 함수 작성
- `ml/serve.py:_make_tft_predictions` 안 `_make_dataframe` 호출을 DB 쿼리로 교체
- 쿼리: `SELECT layer, region, time, value FROM layer_signals WHERE region=$1 ORDER BY time` → wide-format pivot
- TFT TimeSeriesDataSet 구조와 호환되도록 변환

**D-5 (5/2~5/3)**: 실데이터 재학습
```bash
cd ~/urban-immune-system && source .venv/bin/activate
python -m ml.tft.train_real --epochs 50 --regions all
# 출력: ml/checkpoints/tft_real/tft_best.ckpt
```
- CPU 머신이라 학습 6~10시간 예상 — 야간 실행
- early stopping val_loss patience=10

**D-3 (5/4~5/5)**: 검증 + 메트릭 리포트
- `ml/reproduce_validation.py --model=tft_real` 추가
- F1·MAE·attention top-3 비교 (synth vs real)
- 결과를 `analysis/outputs/tft_real_validation.json`

**D-1 (5/6)**: 슬라이드 업데이트 + 라이브 시연 검증
- S07F TFT 카드 attention top-3 실측 결과로 갱신
- /predict/tft-14d 엔드포인트 라이브 호출 (curl 데모)

### Fallback (학습 실패 또는 시간 부족)
- 합성 학습된 `tft_best-v2.ckpt` 그대로 사용
- S07F 카드에 "synth 학습 · real 데이터 fine-tuning Phase 2" 솔직 표기
- 현 75% 완성 상태 유지 (S09)

---

## 2. 외부 자문 자료 발송 (★★★)

### 발송 대상

| 기관 | 부서 | 채널 | 주안점 |
|---|---|---|---|
| **질병관리청 (KDCA)** | 감염병관리과 / 역학조사과 | 공문 + 이메일 | 모델 검증 · 임상 활용 가능성 |
| **한국인터넷진흥원 (KISA)** | ISMS-P 사전 컨설팅 신청 | 신청서 | 정보보호 인증 사전 의견 |

### 발송 패키지 (zip)

```
uis-advisory-package-2026-W18.zip
├── README.md                     # 자문 요청 개요 + 우리 팀 정체성
├── walk_forward_backtest.pdf     # 17지역 F1 0.841·5.9주·Granger p=0.021
├── architecture_diagram.pdf      # S05 6단계 시스템 + S05A 데이터 근거
├── reproduce_command.txt         # `python -m ml.reproduce_validation`
├── demo_url.txt                  # http://34.158.197.122:3000/dashboard
├── code_snapshot.tar.gz          # pipeline/scorer.py + ml/xgboost/model.py
├── slides_pdf.pdf                # 27장 슬라이드 PDF export
└── DPIA_draft.md                 # 개인정보 영향평가 초안 (KISA 용)
```

### Day-by-day

**D-7 (4/30)**: 패키지 빌드 스크립트 작성
- `scripts/build_advisory_package.sh` — reportlab + LibreOffice export
- 자료 정합성 검증 (수치 일치)

**D-6 (5/1)**: 공문 초안 + 지도교수 검토
- KDCA: "감염병 조기경보 모델 임상 활용 자문 요청" 1쪽
- KISA: "ISMS-P 사전 컨설팅 신청서" 표준 양식
- 지도교수 공동 서명

**D-5 (5/2)**: 발송
- KDCA: 우편 (등기) + 이메일 (감염병관리과 공식)
- KISA: 온라인 사전 컨설팅 신청 시스템

**D-1 (5/6)**: 회수 확인
- 답변 도착 시 S13B 슬라이드에 "○월○일 자문 회신 완료" 표기 갱신
- 미회신 시 "발송 완료, 회신 대기" 그대로 표기 (정직)

### 발송 자료 자동 생성 명령
```bash
cd ~/urban-immune-system
source .venv/bin/activate
python scripts/build_review_pdf.py        # 검증 리포트 PDF
bash scripts/sync-slides.sh                # 슬라이드 PDF export
zip -r uis-advisory-package-W18.zip docs/business/advisory/
```

---

## 3. 발표 리허설 2~3회 (★★)

### 시간 배분표 (15분 목표 · 27장)

| 묶음 | 슬라이드 | 시간 | 누적 |
|---|---|---|---|
| 도입 | S01·S02·S03·S04 | 30s × 4 = 2:00 | 2:00 |
| 시스템 | S05·S05A | 40s × 2 = 1:20 | 3:20 |
| 검증 정직 | S06·S07 | 30s × 2 = 1:00 | 4:20 |
| **코드 (8장)** | S07A·A2·E·B·C·D·D2·F | 35s × 8 = 4:40 | 9:00 |
| 솔직 | S08·S09 | 25s × 2 = 0:50 | 9:50 |
| 데모 | S10·S10A | 60s × 2 = 2:00 | 11:50 |
| 메트릭 | S11 | 50s × 1 = 0:50 | 12:40 |
| 검증/자문 | S12·S12B·S13B | 35s × 3 = 1:45 | 14:25 |
| 마무리 | S14·S15·S16 | 25s × 3 = 1:15 | **15:40** |

→ 코드 슬라이드 평균 35s 유지가 핵심.

### 리허설 일정

- **D-5 (5/2)**: 1차 — 시간 측정, 멘트 자연스러움
- **D-3 (5/4)**: 2차 — Q&A 5분 추가, 백업 영상 동작 확인
- **D-1 (5/6)**: 3차 — 발표장 환경 (프로젝터·소리), 의상

### 체크리스트
- [ ] 노트북 풀스크린(F) 단축키 동작 확인
- [ ] `Ctrl+Shift+R` 강력 새로고침 후 26씬 모두 로드
- [ ] WiFi 끊김 대비 — 슬라이드 정적 PDF export 백업
- [ ] 마이크·HDMI 어댑터 준비
- [ ] 데모 데이터 — `python -m pipeline.scorer --backfill 2025-09-01 2026-03-31` 사전 실행

---

## 4. 데모 백업 영상 인코딩 (★★)

라이브 데모 사고(WiFi 끊김·서버 다운) 대비.

### 녹화 시나리오 (3분 영상)

1. **0:00~0:30** — 대시보드 진입 (`http://34.158.197.122:3000/dashboard`)
2. **0:30~1:00** — 17지역 지도 인터랙션 (서울 클릭 → 위험도 상세)
3. **1:00~1:30** — 시계열 차트 (composite 26주 추세)
4. **1:30~2:30** — Claude RAG 리포트 SSE 생성 (한 줄씩 흘러나오는 것)
5. **2:30~3:00** — 팬데믹 조기탐지 탭 (이상탐지 결과)

### 녹화 명령 (Linux)
```bash
# 화면 녹화 (ffmpeg + x11grab)
ffmpeg -f x11grab -s 1920x1080 -i :0.0 -framerate 30 \
       -c:v libx264 -preset fast -crf 23 \
       demo-backup-2026-05-07.mp4
```

### 권장 형식
- 1920×1080, mp4, H.264, 30fps
- 음성 없음 (발표 멘트와 충돌)
- 5분 이하 (USB 보관 + 발표 PC 미리 복사)

---

## 5. S07E 본문 복귀 (★) — ✅ 완료

5/7 일정으로 8일 추가 확보 → S07E (5단계 흐름) SCENES 배열 복귀.
- 위치: S07A2 직후
- 26장 → **27장**
- Chrome total 27, counter `01 / 27` 갱신
- 노트도 추가됨

---

## 6. 데모 시나리오 동선 (★)

### 발표자 시점 동선

**1. 대시보드 진입 (S10 슬라이드 도중)**
- 김나영: 노트북 좌측 모니터 — 슬라이드
- 김나영: 노트북 우측 모니터 — `http://34.158.197.122:3000/dashboard`
- 발표 슬라이드는 외부 키보드로 → 키 누름

**2. 라이브 시연 (S10A 자동 발송 직전)**
- 박진영: "지금 보시는 화면이 라이브로 도는 모습입니다"
- 클릭 시퀀스:
  1. 17지역 지도 → 서울 호버 (위험도 카드 펼침)
  2. 시계열 차트 → "26주 누적 곡선"
  3. RAG 리포트 카드 → SSE 스트리밍 시작 (Claude 답변 한 줄씩 출력)
  4. 팬데믹 조기탐지 탭 클릭 → 이상탐지 결과
- 시간: 60~90초

**3. 자동 발송 슬라이드 (S10A)**
- "운영 단계에서는 RED 경보가 뜨면 부처 4곳에 자동 발송됩니다"
- 슬라이드 mock UI로 충분 (라이브 X)

### 사고 대비 동선 (Plan B)
- WiFi 끊김 → 백업 mp4 영상 재생 ("녹화본으로 보여드리겠습니다")
- 서버 다운 → 슬라이드 mock UI 만으로 진행 (S10에 mock UI 박혀 있음)
- 노트북 freeze → 휴대폰 핫스팟 + 백업 PDF

---

## 종합 D-8 일정 (Gantt 요약)

```
4/29 (D-8) │ S07E 복귀 ✓ · TFT 진단 ✓
4/30 (D-7) │ TFT 실데이터 함수 작성 · 자문 패키지 빌드
5/1  (D-6) │ TFT 실데이터 함수 작성 · 자문 공문 초안
5/2  (D-5) │ TFT 실학습 야간 시작 · 자문 발송 · 리허설 1차
5/3  (D-4) │ TFT 학습 모니터링 · 데모 영상 녹화
5/4  (D-3) │ TFT 검증 · 리허설 2차 · Q&A 정리
5/5  (D-2) │ S07F 갱신 · 데모 동선 최종 점검
5/6  (D-1) │ 리허설 3차 (발표장 환경) · 자문 회신 확인
5/7  (D-0) │ 본 발표 + Q&A 5분
```
