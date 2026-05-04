# systemd 서비스 등록

## 목적
APScheduler 기반 데이터 수집·앙상블·RAG 배치를 systemd 서비스로 등록해
GCP VM 재부팅 시 자동 재시작·실패 시 15초 후 자동 복구되게 한다.

## 설치 (1회, sudo 필요)

```bash
# 1) 기존 nohup 프로세스 종료
pkill -f "pipeline.collectors.scheduler"

# 2) 서비스 파일 시스템에 복사
sudo cp /home/wlsdud5035/urban-immune-system/infra/systemd/uis-scheduler.service \
        /etc/systemd/system/uis-scheduler.service

# 3) 로그 파일 준비 (소유권 wlsdud5035)
sudo touch /var/log/uis-scheduler.log
sudo chown wlsdud5035:wlsdud5035 /var/log/uis-scheduler.log

# 4) 활성화 + 즉시 시작
sudo systemctl daemon-reload
sudo systemctl enable uis-scheduler
sudo systemctl start uis-scheduler

# 5) 상태 확인
sudo systemctl status uis-scheduler
tail -f /var/log/uis-scheduler.log
```

## 운영 명령

| 명령 | 설명 |
|---|---|
| `sudo systemctl status uis-scheduler` | 가동 상태 |
| `sudo systemctl restart uis-scheduler` | 재시작 (`.env` 변경 후) |
| `sudo systemctl stop uis-scheduler` | 정지 |
| `sudo journalctl -u uis-scheduler -f` | systemd 로그 실시간 |
| `tail -f /var/log/uis-scheduler.log` | APScheduler stdout 로그 |

## 보안 옵션

서비스 파일에 다음 하드닝 적용됨:
- `NoNewPrivileges=true` — 권한 상승 금지
- `ProtectSystem=full` — `/usr`, `/boot` 읽기 전용
- `ProtectHome=read-only` — `/home` 읽기 전용 (단 `ReadWritePaths` 로 프로젝트 디렉토리만 쓰기 허용)
- `PrivateTmp=true` — `/tmp` 격리

## 주의

- `.env` 변경 시 반드시 `sudo systemctl restart uis-scheduler` 실행 (EnvironmentFile은 시작 시점에만 로드)
- 가상환경 경로 변경 시 `ExecStart=` 라인 수정 필요
