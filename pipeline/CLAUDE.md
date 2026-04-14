# pipeline/ — B 이경준·박진영 공용

## 담당자
- **역할 B — 이경준**: 수집기 구현, APScheduler 크론 등록
- **역할 B+C — 박진영**: Kafka Consumer 구현, TimescaleDB 적재

## 수집 스케줄

| 수집기 | Kafka 토픽 | 주기 | 담당 |
|-------|-----------|------|------|
| `otc_collector.py` | `uis.layer1.otc` | 매주 월 09:00 | 이경준 |
| `wastewater.py` | `uis.layer2.wastewater` | 매주 화 10:00 | 이경준 |
| `search_collector.py` | `uis.layer3.search` | 매주 월 09:05 | 이경준 |
| `weather_collector.py` | `uis.aux.weather` | 매시간 | 이경준 |

## 발표 데모 단순화 옵션
> Kafka Consumer + TimescaleDB full-pipeline이 발표 전까지 미완료될 경우:
> **cron + DB INSERT 단순화** 사용 가능 (Kafka 생략, 직접 insert)
> 이 경우 `scheduler.py`에 fallback 경로 추가, 주석으로 명시

## 수집 실패 처리 규칙
- 수집 실패 → **이전 주 값 유지** (NaN 전파 절대 금지)
- 재시도 로직: 최대 3회, 15초 간격
- 재시도 모두 실패 시 `CollectorError` 발생 + 로그 기록

```python
# 올바른 패턴 — 이전 값 fallback
async def collect_with_fallback(prev_value: float) -> float:
    try:
        return await collect_otc_weekly()
    except CollectorError:
        logger.warning("수집 실패, 이전 주 값 유지: %s", prev_value)
        return prev_value
```

## 정규화 규칙
- 수집 직후 `normalization.min_max_normalize()` 반드시 호출
- 계층 간 정규화 **독립** 적용 (L1·L2·L3 각각 별도 min/max)
- `normalization.py` 수정 시 팀 전체 공지 필수 (경보 점수 기준 변경)

## Kafka Producer 설정 — 변경 금지
```python
# kafka_producer.py
acks = "all"    # 변경 금지 (데이터 손실 방지)
retries = 3     # 변경 금지
```

## Kafka Consumer — [CRITICAL]

> **[CRITICAL]** Producer만 존재, Consumer 미구현 시 TimescaleDB 적재 불가.
> 해결: Consumer 그룹 구현 + DB INSERT 배치 처리 + 오류 재시도 + Consumer lag 모니터링

- Consumer 그룹: `group_id = "uis-consumer-group"`
- DB INSERT 배치 처리: 100건 또는 5초 간격 중 먼저 도달하는 조건
- 오류 재시도: 3회, 지수 백오프 (15s → 30s → 60s)
- Consumer lag 모니터링: 100건 초과 시 알림

## 새 수집기 추가 체크리스트
- [ ] `pipeline/collectors/<name>_collector.py` 생성
- [ ] Kafka 토픽 `uis.<layer>.<name>` 추가 (`docker-compose.yml` 업데이트)
- [ ] `normalization.min_max_normalize()` 호출 확인
- [ ] `scheduler.py`에 크론 잡 등록
- [ ] `tests/test_<name>_collector.py` 작성
- [ ] `.env.example`에 필요한 환경변수 추가

## KOWAS PDF — [CRITICAL] 자동화 (B 역할 최우선)

> **[CRITICAL]** Selenium/Playwright로 KOWAS PDF 자동 크롤링 파이프라인 완성
> B 역할의 최우선 과제. 실패 시 수동→반자동으로 단계적 전환.

- **Phase 1 (1~2주)**: Selenium/Playwright KOWAS PDF 자동 다운로드 프로토타입 구현
- PDF 저장 경로: `pipeline/data/kowas/`
- PDF 구조 변경 감지 시 `PDFParseError` 발생 (silent fail 금지)
- **수동 Fallback**: 자동화 실패 시 수동 다운로드 → `pipeline/data/kowas/` 저장 후 파싱

## 권장 스킬
- `/simplify` — 수집기 코드 리뷰 후 품질 개선
