# nginx 리버스 프록시 (외부 :80 → 대시보드)

> 외부 노출은 nginx 인증 게이트 경유만. Next.js 대시보드는 loopback 유지 (ISMS-P).

## 구성 요약
- **외부**: TCP 80 (HTTP, Basic Auth)
- **백엔드**: 127.0.0.1:3000 (Next.js · loopback)
- **인증**: htpasswd (계정명 `admin`)
- **SSE**: `proxy_buffering off` + `proxy_read_timeout 3600s` (실시간 스트림)
- **로그**: `/var/log/nginx/uis_access.log` · `uis_error.log` (ISMS-P 접근통제 증적)

## 재배포 (서버 재구축 시)

```bash
# 1) nginx + apache2-utils 설치
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx apache2-utils

# 2) Basic Auth 계정 생성 (비번은 별도 전달 — 평문 커밋 금지)
sudo htpasswd -c /etc/nginx/.uis_htpasswd admin
sudo chown root:www-data /etc/nginx/.uis_htpasswd
sudo chmod 640 /etc/nginx/.uis_htpasswd   # www-data 읽기 권한 — 미부여 시 nginx 500

# 3) 설정 파일 배포
sudo cp infra/nginx/uis-dashboard.conf /etc/nginx/sites-available/uis-dashboard.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/uis-dashboard.conf /etc/nginx/sites-enabled/uis-dashboard.conf

# 4) 문법 검사 + 시작 + 부팅 등록
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
```

## 검증
```bash
curl -s -o /dev/null -w "no-auth: %{http_code}\n"   http://127.0.0.1/                    # → 401
curl -s -o /dev/null -w "auth /:  %{http_code}\n" -u admin:PW http://127.0.0.1/          # → 307
curl -s -o /dev/null -w "/dashboard: %{http_code}\n" -u admin:PW http://127.0.0.1/dashboard  # → 200
```

## 보안 후속 (운영 전 필수)
- [ ] HTTPS 적용 (도메인 + Let's Encrypt) — 현재 HTTP라 Basic Auth 평문 전송
- [ ] 임시 비번 교체 (`sudo htpasswd /etc/nginx/.uis_htpasswd admin`)
- [ ] 소스 IP 제한 (현재 `0.0.0.0/0` 공개 + 인증) → 팀 IP allow-list 또는 GCP IAP

## 운영툴 접근 (SSH 터널)
`docker-compose.yml` 의 데이터 평면 포트가 loopback 바인딩이라 외부 직접 접속 불가.
운영자는 SSH 포트 포워딩으로 접근:
```bash
ssh -L 8080:127.0.0.1:8080 wlsdud5035@REDACTED-HOST   # kafka-ui
ssh -L 5432:127.0.0.1:5432 wlsdud5035@REDACTED-HOST   # TimescaleDB
ssh -L 6333:127.0.0.1:6333 wlsdud5035@REDACTED-HOST   # Qdrant
```
