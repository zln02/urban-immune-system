# 3계층 데이터 처리 명세

## 아키텍처 원칙

```
[수집] → [Kafka 토픽] → [정규화(0-100)] → [TimescaleDB] → [앙상블] → [경보]
  L1           L2             L3
 약국         하수도          검색
1-2주 선행   2-3주 선행    1-2주 선행
```

> **핵심 규칙**: 어떤 단일 계층도 단독 경보 발령 금지. 반드시 2개 이상 계층 교차검증 필요.
> Google Flu Trends 과대예측 실패 교훈 — L3 단독 사용 절대 금지.

---

## Layer 1: 약국 OTC (Pharmacy)

**소스**: 네이버 쇼핑인사이트 API  
**Kafka 토픽**: `uis.layer1.otc`  
**수집 주기**: 매주 월요일 09:00  
**색상**: `#be185d` (마젠타)

```python
# pipeline/collectors/otc_collector.py

# 모니터링 키워드 — 임의 추가 금지, config.py에서 관리
OTC_KEYWORDS = ["감기약", "해열제", "종합감기약", "타이레놀", "판콜"]

# API 타임아웃 15초 고정 — 변경 시 scheduler.py 재검토 필요
TIMEOUT_SEC = 15

# 반환 타입 명시 필수
async def collect_otc_weekly() -> dict[str, float]:
    """네이버 쇼핑인사이트에서 주간 OTC 구매 트렌드 수집.

    Returns:
        region → 정규화 지수 (0-100)
    Raises:
        CollectorError: API 인증 실패 또는 타임아웃
    """
```

**처리 규칙**:
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` 환경변수 필수 (하드코딩 금지)
- 응답이 비어 있으면 이전 주 값 유지 (NaN 전파 금지)
- 수집 후 즉시 `normalization.min_max_normalize()` 적용

---

## Layer 2: 하수도 바이오마커 (Wastewater)

**소스**: KOWAS (한국 하수도감시 시스템) PDF  
**Kafka 토픽**: `uis.layer2.wastewater`  
**수집 주기**: 매주 화요일 10:00  
**색상**: `#047857` (청록)

```python
# pipeline/collectors/wastewater.py

# PDF 파싱 — pdfplumber 사용
# [CRITICAL] Phase 1 (1~2주): Selenium/Playwright 자동 다운로드 프로토타입 구현 필수
# Fallback: 자동화 실패 시 수동 다운로드 → pipeline/data/kowas/ 저장

def parse_kowas_pdf(pdf_path: str) -> list[WastewaterReading]:
    """KOWAS PDF에서 인플루엔자 바이러스 농도 추출.

    Args:
        pdf_path: pipeline/data/kowas/ 하위 PDF 절대경로
    Returns:
        WastewaterReading 리스트 (region, copies_per_ml, date)
    Raises:
        PDFParseError: 파싱 실패 또는 예상 테이블 구조 불일치
    """
```

**처리 규칙**:
- 단위: copies/mL → Min-Max 정규화 (전체 레코드 기준)
- PDF 구조 변경 감지 시 즉시 `PDFParseError` 발생 (silent fail 금지)
- PDF 저장 경로: `pipeline/data/kowas/`
- **[CRITICAL]** Selenium/Playwright 자동 크롤링 파이프라인 구현 (B 역할 최우선)

---

## Layer 3: 검색 트렌드 (Search/SNS)

**소스**: 네이버 DataLab API (쇼핑인사이트와 다른 엔드포인트)  
**Kafka 토픽**: `uis.layer3.search`  
**수집 주기**: 매주 월요일 09:05  
**색상**: `#1d4ed8` (파랑)

```python
# pipeline/collectors/search_collector.py

# L3 전용 키워드 — L1 키워드와 의도적으로 분리 (구매 vs 증상탐색)
SEARCH_KEYWORDS = ["독감 증상", "인플루엔자", "고열 원인", "몸살 원인", "타미플루"]

# DataLab API — 쇼핑인사이트와 다른 엔드포인트/인증
DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
```

**처리 규칙**:
- L1 OTC 키워드와 혼용 금지 (구매행동 ≠ 증상탐색)
- L3 단독 경보 발령 절대 금지 — 반드시 L1 또는 L2와 교차검증
- 트렌드 지수 급등(>80/100) 단독 감지 시 `YELLOW` 이하로만 설정 가능

---

## Auxiliary: 기상 데이터

**소스**: 기상청 초단기 예측 API (KMA)  
**Kafka 토픽**: `uis.aux.weather`  
**수집 주기**: 매시간

**처리 규칙**:
- 기온: -20°C ~ 40°C → 0-100 정규화
- 기상 데이터는 TFT 입력 피처 전용 — 경보 점수 직접 기여 금지
- 인과관계 아닌 상관관계: "저온·저습 → 독감 상관" (인과 주장 금지)

---

## 정규화 (Normalization)

```python
# pipeline/collectors/normalization.py

def min_max_normalize(values: list[float]) -> list[float]:
    """모든 계층 신호를 0-100으로 스케일링.

    Args:
        values: 원시 신호값 리스트
    Returns:
        0-100 정규화값 (빈 리스트 또는 상수 입력 처리 포함)
    """
```

**규칙**:
- 빈 리스트 입력 → `[]` 반환 (예외 발생 금지)
- 상수값(모두 동일) 입력 → `[50.0] * n` 반환 (ZeroDivision 방지)
- 계층 간 정규화 독립 적용 (L1·L2·L3 각각 별도 min/max)

---

## 앙상블 경보 로직

```
composite_score = w1 * l1_score + w2 * l2_score + w3 * l3_score

기본 가중치: w1=0.35, w2=0.40, w3=0.25
(L2 하수도 최고 가중치 — 가장 빠른 선행지표)

경보 레벨:
  GREEN  : composite < 30
  YELLOW : 30 ≤ composite < 55
  ORANGE : 55 ≤ composite < 75  (미래 확장)
  RED    : composite ≥ 75
```

**규칙**:
- 가중치는 `backend/app/config.py` 에서만 관리 (하드코딩 금지)
- `YELLOW` 이상 경보는 반드시 2개 이상 계층이 30 이상이어야 발령
- DB 모델 `alert_level` 컬럼: `'GREEN' | 'YELLOW' | 'RED'` 외 값 저장 금지

---

## Kafka 토픽 규칙

| 토픽 | 계층 | 보존 |
|------|------|------|
| `uis.layer1.otc` | L1 약국 | 168시간 |
| `uis.layer2.wastewater` | L2 하수도 | 168시간 |
| `uis.layer3.search` | L3 검색 | 168시간 |
| `uis.aux.weather` | 기상 | 168시간 |

```python
# kafka_producer.py 사용 규칙
# acks="all", retries=3 고정 — 변경 금지 (데이터 손실 방지)
# 직렬화: JSON UTF-8 (바이너리 직렬화 도입 시 버전 헤더 추가)
```

---

## 데이터베이스

### TimescaleDB 하이퍼테이블

```sql
-- layer_signals: 모든 계층 원시 신호
-- 파티셔닝: time (weekly)
-- 인덱스: (time, layer), (layer, region, time DESC)
layer VARCHAR(10)        -- 'L1' | 'L2' | 'L3' | 'AUX' 외 값 삽입 금지
value DOUBLE PRECISION   -- 반드시 0-100 사이 (정규화 후 삽입)
```

### 마이그레이션 규칙

- 스키마 변경: `infra/db/init.sql` + SQLAlchemy ORM 동시 수정
- `NOT NULL` 컬럼 추가: 기본값 필수 또는 배포 순서 관리
- 하이퍼테이블 파티션 변경: 데이터 손실 위험 — 반드시 확인 후 진행

---

## 계층별 파일 위치

| 작업 | 위치 |
|------|------|
| 수집 로직 변경 | `pipeline/collectors/` |
| 정규화 변경 | `pipeline/collectors/normalization.py` |
| DB 스키마 변경 | `infra/db/init.sql` + ORM 모델 동시 수정 |
| API 엔드포인트 | `backend/app/api/` |
| 경보 가중치 변경 | `backend/app/config.py` |
| ML 하이퍼파라미터 | `ml/configs/model_config.yaml` |
| 상수·색상 | `src/config.py` (Streamlit) / `backend/app/config.py` (API) |

### 새 수집기 추가 시 체크리스트

- [ ] `pipeline/collectors/<name>_collector.py` 생성
- [ ] Kafka 토픽 `uis.<layer>.<name>` 추가 (docker-compose.yml 업데이트)
- [ ] `normalization.min_max_normalize()` 호출 확인
- [ ] `scheduler.py`에 크론 잡 등록
- [ ] `tests/test_<name>_collector.py` 작성
- [ ] `.env.example`에 필요한 환경변수 추가
