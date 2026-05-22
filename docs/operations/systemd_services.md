# UIS systemd Services Inventory

> 마지막 갱신: 2026-05-22 · uis-frontend.service 정식 등록 (수동 instance → systemd 교체)

## Active Services (2026-05-22)

| Service | Port | After | Status |
|---------|------|-------|--------|
| `uis-docker.service` | docker stack | network.target | active (oneshot) |
| `uis-backend.service` | 8001 (loopback) | uis-docker | active |
| `uis-ml.service` | 8002 (loopback) | network.target | active |
| `uis-scheduler.service` | — (job runner) | network.target | active |
| `uis-frontend.service` | 3000 (loopback) | uis-backend | active |

모든 listen socket 은 `127.0.0.1` (loopback) — 외부 접근은 nginx 리버스 프록시 경유 (Phase 2 DNS 작업과 연동).

## Restart Policy

```ini
Restart=on-failure
RestartSec=5
StartLimitBurst=5
StartLimitIntervalSec=120
```

5초 후 자동 재시작, 120초 윈도 내 5회 실패 시 정지 (crash loop 가드).

## Resource Limits (uis-frontend)

```ini
MemoryMax=1G
CPUQuota=80%
```

Next.js 14.2.35 production server 기준 정상 메모리는 100~200MB. 비정상 누수 시 OOM kill → restart 자동.

## Security (모든 서비스 공통)

- listen 인터페이스 `127.0.0.1` 만 (외부 노출 금지)
- `User=wlsdud5035` (non-root)
- 환경변수는 `.env` 또는 `.env.production` 의 `EnvironmentFile=-` 로 주입 (- prefix: 파일 없어도 startup 실패 안 함)

## 로그

```bash
journalctl -u uis-frontend.service -f          # 실시간
journalctl -u uis-frontend.service --since "1h ago" --no-pager
```

`SyslogIdentifier=uis-frontend` 로 다른 서비스와 구분.

## 운영 명령어 모음

```bash
# 상태
systemctl status uis-frontend.service --no-pager

# 재시작 (코드 변경 후)
sudo systemctl restart uis-frontend.service

# 로그 꼬리
journalctl -u uis-frontend.service -f

# 일시 정지 (재부팅 시 다시 시작)
sudo systemctl stop uis-frontend.service

# 영구 비활성 (재부팅 후에도 안 시작)
sudo systemctl disable uis-frontend.service

# 새 build 후 적용
cd /home/wlsdud5035/urban-immune-system/frontend
npm run build && sudo systemctl restart uis-frontend.service
```

## 의존성 (Wants/After)

```
network.target
  └─ uis-docker.service (Kafka + TimescaleDB + Qdrant + kafka-ui)
       └─ uis-backend.service (FastAPI :8001)
            └─ uis-frontend.service (Next.js :3000)
  └─ uis-ml.service (FastAPI :8002, 별도 의존성)
  └─ uis-scheduler.service (APScheduler 3-Layer 수집)
```

`uis-frontend.service` 는 `Wants=uis-backend.service` — backend 가 살아있어야 API 호출 가능. backend 가 죽어도 frontend 자체는 계속 동작 (SSR 에서 backend 에러 페이지 렌더).

## 등록 이력

| 날짜 | 작업 |
|------|------|
| 2026-05-22 | `uis-frontend.service` 정식 등록 — 기존 수동 `npm run start` (PID 2032102, 4-19:54 실행) 교체 |

## 참고

- 단위 파일 canonical: `infra/systemd/uis-frontend.service` (이 레포)
- 실 install 경로: `/etc/systemd/system/uis-frontend.service`
- 변경 동기화 절차:
  1. `infra/systemd/uis-frontend.service` 편집 + 커밋
  2. `sudo cp infra/systemd/uis-frontend.service /etc/systemd/system/`
  3. `sudo systemctl daemon-reload`
  4. `sudo systemctl restart uis-frontend.service`
