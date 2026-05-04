# 데모 영상 백업 가이드 (2026-05-07 중간발표)

> ℹ️ IP `34.47.113.176`은 static 예약 완료(`uis-capstone-ip`, 2026-05-04). VM 재시작에도 유지. 발표 후 release 시 재예약 필요.

> 목적: 발표 당일 GCP·인터넷 장애 시 즉시 폴백할 3분 데모 영상을 미리 녹화한다.
> 녹화 시점: D-1 (2026-05-06). 발표 직전 코드 freeze 후.

## 0. 사전 조건

- 5개 서비스 healthy (D-4 e2e 통과 확인됨)
  - TimescaleDB :5432 / Qdrant :6333 / FastAPI :8001 / Next.js :3000 / Streamlit :8501
- 슬라이드 D-day 표기 갱신 완료 (`frontend/public/slides/`)
- 발표자 로컬 PC: 디스크 5GB+, OBS 또는 QuickTime, 마이크 점검 완료

## 1. SSH 터널 (로컬 PC ↔ GCP)

발표자 PC에서:

```bash
# 5개 포트 한꺼번에 포워딩 (별도 터미널 유지)
ssh -L 3000:localhost:3000 \
    -L 8001:localhost:8001 \
    -L 8501:localhost:8501 \
    -L 6333:localhost:6333 \
    -L 5432:localhost:5432 \
    wlsdud5035@34.47.113.176
```

> static IP 예약 완료 — 발표 직전 `gcloud compute addresses describe uis-capstone-ip` 로 status=`IN_USE` 재확인.

## 2. 데모 시나리오 (총 ~3분, 5 컷)

| # | 컷 | URL / 액션 | 시간 | 설명 (자막용) |
|---|----|-----------|------|----------|
| 1 | 슬라이드 인트로 | `http://localhost:3000/slides/index.html` 또는 발표 자료 첫 장 | 20초 | "Urban Immune System — 3계층 비의료 신호 감염병 조기경보" |
| 2 | 메인 대시보드 | `http://localhost:3000/dashboard` | 40초 | 17지역 지도 → 부산 클릭 → KPI 카드 + Granger·CCF 패널 |
| 3 | 팬데믹 조기탐지 탭 | 같은 페이지 탭 전환 | 30초 | Autoencoder 재구성 오차 17지역 → 임계값 99p 1/17 정상화 |
| 4 | SSE RAG 리포트 | "AI 리포트 생성" 버튼 → SSE 스트림 | 50초 | Claude Haiku 출력 KDCA 9섹션 라이브 스트리밍 (첫 청크 5초 이내) |
| 5 | PDF 4페이지 다운로드 | "PDF 다운로드" 버튼 | 20초 | 한글 폰트(NanumGothic) 정상, 백테스트 차트 4페이지 |

**총 2분 40초.** 인트로/아웃트로 합쳐 3분 이내.

## 3. 녹화 명령

### 옵션 A — OBS (권장, macOS/Windows)

1. 1920×1080 60fps 프리셋
2. 소스: 브라우저 윈도우 캡처 (Chrome/Firefox 별도 창, 다른 알림 OFF)
3. 마이크 OFF (자막 후처리)
4. 단축키: F9 시작/정지

### 옵션 B — QuickTime (macOS)

```
파일 → 새로운 화면 기록 → 영역 선택 (브라우저만)
```

### 옵션 C — ffmpeg (Linux 서버 직접 녹화, GUI 없음 → 비권장)

```bash
# Xvfb 가상 디스플레이로 띄울 경우만
Xvfb :99 -screen 0 1920x1080x24 &
DISPLAY=:99 google-chrome --kiosk http://localhost:3000/dashboard &
ffmpeg -y -f x11grab -s 1920x1080 -i :99 -t 180 -c:v libx264 \
       -preset veryfast -pix_fmt yuv420p /tmp/uis-demo-2026-05-07.mp4
```

## 4. 후처리

- 출력 파일: `uis-demo-2026-05-07_v1.mp4` (1080p, H.264, 100MB 이내)
- 자막: 위 5컷 표의 "설명" 컬럼을 `.srt` 로 변환 (선택)
- 검수: 처음부터 끝까지 1회 시청 — UI 흔들림·타이밍 자연스러움 확인

## 5. 백업 미디어

| 위치 | 용도 |
|---|---|
| 발표자 노트북 로컬 디스크 | 1차 |
| USB 메모리 (FAT32, 다른 노트북에서도 인식) | 2차 (현장 노트북 장애 대비) |
| Google Drive `UIS/캡스톤/2026-05-07_demo/` | 3차 (네트워크 살아있다면) |

## 6. 발표 당일 폴백 시퀀스

라이브 데모가 실패하면:

1. **0~5초** — "잠시 영상으로 대체합니다" 한 마디
2. 슬라이드 대신 영상 풀스크린 재생 (Keynote/PPT 자동 재생 슬라이드 별도 준비)
3. 영상 종료 후 → Q&A 슬라이드로 전환
4. 라이브 복구를 시도하지 말 것 (시간 낭비, 발표 흐름 깨짐)

## 7. 체크리스트 (D-1 저녁)

- [ ] SSH 터널 5포트 정상
- [ ] 5개 컨테이너 healthy
- [ ] 시나리오 1회 리허설 (3분 이내 성공)
- [ ] 녹화본 1080p, 100MB 이내, 자체 시청 1회
- [ ] USB·Drive 업로드 완료
- [ ] 발표용 PPT/Keynote에 영상 삽입 (자동재생 슬라이드)
