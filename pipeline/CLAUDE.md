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
- 수집 직후 `normalization.min_max_normalize()` 반드시 호출 (KOWAS L2 / 자체 스케일 신호용)
- 계층 간 정규화 **독립** 적용 (L1·L2·L3 각각 별도 min/max)
- `normalization.py` 수정 시 팀 전체 공지 필수 (경보 점수 기준 변경)

### Naver L1·L3 예외 — 슬라이딩 윈도우 min-max 금지
**[CRITICAL — 2026-04-27 사고 재발 방지]** Naver datalab/shopping ratio 는 이미 자체 정규화(peak=100 기준 0~100 비율)다.
- **금지**: 수집된 ratio 위에 다시 `min_max_normalize` 적용 — 비수기 마지막 주가 0 으로 박히는 zero-collapse 발생
- **올바름**: ratio 그대로 0~100 스케일 사용. clamp 만 적용 (`max(0, min(100, raw))`)
- 사고 케이스: `pipeline/collectors/naver_backfill.backfill_layer` 가 56주 raw 위에 min-max 재정규화 → 04-27 raw=0.98 (낮은 비수기) 가 value=0 으로 박힘 → 17개 시·도 모두 0 → scorer 게이트 B 통과 불가
- 회귀 방지 테스트: `tests/test_naver_data_quality.py::TestBackfillZeroCollapse`

### Naver source 라벨 통일 정책
**[CRITICAL]** OTC 는 `source='naver_shopping_insight'` 로 단일화. legacy `naver_shopping` 금지.
- 두 source 가 한 region 시계열에 섞이면 정규화 스케일이 달라 등락 왜곡 (2026-04-13 92.83 → 04-24 44.52 → 04-27 94.51 사고)
- 신규 collector(`otc_collector.collect_otc_weekly`) + backfill(`naver_backfill.run_backfill`) 둘 다 동일 source 라벨 → 멱등 DELETE 가 같은 (layer, source) 기준이라 일관 정리
- 회귀 방지 테스트: `tests/test_naver_data_quality.py::TestSourceUnification`

### Naver 단일값 → 17 region broadcast 의무
**[CRITICAL]** 네이버 쇼핑인사이트·데이터랩은 region 파라미터 미지원 → 전국 단일값.
- 수집 후 반드시 `SIDO_ALL` (17개 시·도) 모두에 동일 값 fan-out 적재
- 단일 region 만 적재하면 `/alerts/regions` 16 region 결손 + dashboard 지도 회색
- UI 측에선 "전국 단일값" caveat label 노출 + HIRA 연동 후 Phase 2 차등화
- 회귀 방지 테스트: `tests/test_naver_data_quality.py::TestOtcRegionBroadcast`

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
