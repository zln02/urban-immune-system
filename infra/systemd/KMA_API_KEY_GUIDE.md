# 기상청 KMA API 키 발급 가이드

## 현재 상태
- `.env` 의 `KMA_API_KEY=` 비어 있음
- 매시간 weather_collector 가 `WARNING 기상청 API 키가 없습니다 (KMA_API_KEY)` 출력 후 빈 결과 반환
- 결과: Autoencoder 의 temperature 피처가 전 지역 fallback=20.0 → 정확도 손실

## 해결: 공공데이터포털에서 무료 발급 (5분)

### 1. 회원가입·로그인
https://www.data.go.kr  → 우측 상단 회원가입

### 2. API 신청
1. 검색창에 "초단기실황" 입력
2. **"기상청_단기예보 ((구)_동네예보) 조회서비스"** 클릭
3. 우측 **"활용신청"** 버튼 → 자동 승인 (개인·비영리는 즉시 발급)

### 3. 키 복사
마이페이지 → **개발계정** → 신청한 서비스의 **"일반 인증키 (Encoding)"** 값 복사
(영문·숫자·`%` 포함 100자 안팎)

### 4. .env 적용

```bash
cd /home/wlsdud5035/urban-immune-system

# 키 추가 (값에 %, & 등 특수문자 있어도 그대로 따옴표로 감싸기)
sed -i 's|^KMA_API_KEY=.*|KMA_API_KEY="여기에_복사한_키_붙여넣기"|' .env

# 검증
grep KMA_API_KEY .env

# scheduler 재시작 (systemd 등록 후)
sudo systemctl restart uis-scheduler

# 또는 nohup 환경이면
pkill -f pipeline.collectors.scheduler
cd ~/urban-immune-system && set -a && source .env && set +a && \
  nohup .venv/bin/python -m pipeline.collectors.scheduler > /tmp/uis_scheduler.log 2>&1 &
```

### 5. 검증 (다음 정각 이후)

```bash
tail -20 /var/log/uis-scheduler.log | grep weather
# 기대: "WARNING 기상청 API 키가 없습니다" 사라지고 정상 INSERT 로그
```

```bash
# DB에 weather 데이터 들어왔는지
.venv/bin/python -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv
load_dotenv()
async def main():
    eng = create_async_engine(os.getenv('DATABASE_URL'))
    async with eng.begin() as c:
        r = await c.execute(text(
          \"SELECT region, value, time FROM layer_signals \"
          \"WHERE source LIKE '%weather%' ORDER BY time DESC LIMIT 5\"))
        for row in r: print(row)
asyncio.run(main())
"
```

## 일일 호출 한도
- 무료 등급: **10,000 건/일**
- 우리 사용량: 17지역 × 24시간 = 408 건/일 → **여유 25배**

## 한도 초과 시
공공데이터포털 → 마이페이지 → **활용신청 변경** → 일일 트래픽 상향 (자동 승인 1만~100만)
