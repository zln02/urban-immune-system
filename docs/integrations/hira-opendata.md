# 심평원(HIRA) 보건의료빅데이터개방시스템 연동 가이드

> **포털**: <https://opendata.hira.or.kr/home.do>
> **상태**: 미연동 (2026-04-28 기준) — Phase 2 (W18~W20) 우선 작업
> **소유자**: 박진영 (PM/ML Lead) + 이우형 (Backend, OpenAPI 연동)
> **인용**: Slide 5 (제외 항목), Slide 6 (스코프 축소), `docs/business/sales-targets.md` §8

## 1. 왜 필요한가

| 이유 | 설명 |
|---|---|
| **L1 신뢰도 보강** | 현재 L1(약국 OTC)은 네이버 쇼핑인사이트 1개 출처. 심평원 처방·약국 청구 데이터로 **이중 출처(triangulation)** 확보 시 false positive 감소. |
| **B2G 신뢰도** | "공모전 시점에는 심평원 API 미접근" → Phase 2 에서 정식 접근 시 **공식 의료 청구 통계 기반** 차별점 발생. |
| **임상 확진 라벨** | 우리 walk-forward 검증의 ground truth(임상 확진 발생 시계열)를 KDCA ILINet + **심평원 외래 청구** 와 교차해 신뢰도 향상. |
| **PoC 1순위 KDCA 정합성** | KDCA 자체가 심평원과 데이터 협력 — 심평원 데이터를 인용하면 KDCA PoC 제안 시 친화도 ↑. |

## 2. 심평원 데이터 종류

### 2.1 OpenAPI (실시간 호출 가능)

| 서비스 | 우리 활용 | 우선순위 |
|---|---|---|
| **병원/약국 정보** | 약국 위치·운영시간 (L1 OTC 대비 약국 분포 정규화) | 중 |
| **국민관심질병 통계** | 인플루엔자·코로나19 등 외래 빈도 시·군·구 단위 | **최우선** |
| **다빈도 상병 통계** | ICD-10 코드별 진료 건수 (호흡기 J00~J22) | **최우선** |
| **의약품 처방 정보** | 항바이러스제·해열제 처방 빈도 (L1 보강) | 상 |
| **요양기관 현황** | 시·군·구별 의료기관 밀도 (정규화 기준선) | 하 |

### 2.2 보건의료빅데이터 (HIRA Bigdata Hub, 별도 신청)
- 표본 데이터셋 (Sample Patient DB) — 외래·입원 청구 100만명 표본
- **연구 신청 필요** — IRB 면제 대상이지만 데이터 활용 신청서·서약서 제출
- 처리 시간: 통상 4~6주
- 비용: 무료 (학술·공공 목적)

## 3. 인증·신청 절차

### 3.1 OpenAPI (즉시 사용 가능)
1. <https://opendata.hira.or.kr/home.do> 회원가입
2. 마이페이지 → **"활용 신청"** → 서비스별 신청서 제출
3. 승인 (통상 1~3 영업일) → **인증키(serviceKey) 발급**
4. `.env` 에 `HIRA_SERVICE_KEY=...` 추가 (절대 git commit 금지)
5. 일일 호출 제한: 서비스당 **10,000건/일** (트래픽 초과 시 차단)

### 3.2 Bigdata Hub (정형 데이터셋)
1. <https://opendata.hira.or.kr> → "분석 환경" → 연구 신청
2. **연구계획서** (배경·목적·분석 설계·결과 활용) 제출
3. 보안서약서 + 개인정보 보호 서약 (가명처리 데이터지만 의무)
4. 분석은 **HIRA 보안 분석실** 원격 환경에서만 가능 (다운로드 금지)
5. 결과물 외부 반출 시 **재식별 위험 검토** 통과 필수

## 4. 코드 구조 (Phase 2 구현 계획)

```python
# pipeline/collectors/hira_collector.py (신규)

# 환경변수 — backend/app/config.py 의 Settings 에 등록
# HIRA_SERVICE_KEY = settings.hira_service_key
HIRA_BASE_URL = "https://apis.data.go.kr/B551182"  # 공공데이터포털 경유

INTERESTED_DISEASES = {
    "J09": "조류인플루엔자",
    "J10": "인플루엔자(분리됨)",
    "J11": "인플루엔자(미분리)",
    "B34": "바이러스 감염",
    "U07.1": "COVID-19",
}

async def collect_hira_disease_weekly(
    sigungu_code: str,  # 시·군·구 행정코드
    week: str,          # YYYY-WNN
) -> dict[str, int]:
    """심평원 국민관심질병 외래 빈도 수집.

    Returns:
        {disease_code: 외래 건수}
    Raises:
        CollectorError: 인증 실패·일일 한도 초과·스키마 변경
    """
```

### 4.1 Kafka 토픽
- 신규 토픽: `uis.aux.hira_outpatient` (보존 168시간, 기존 L1~L3·기상과 별도 AUX 계층)
- **L1 보강 신호**로 사용 — 단독 경보 발령 금지 (3-Layer 교차검증 원칙 유지)

### 4.2 정규화·DB
- 시·군·구별 인구 10만명당 외래 빈도로 환산 후 0~100 Min-Max 정규화
- TimescaleDB `layer_signals` 테이블에 `layer='AUX_HIRA'` 로 적재
- ORM: `backend/app/models/layer_signal.py` 의 layer 컬럼 enum 확장 필요

## 5. 법·규제 점검 (ISMS-P 관점)

| 항목 | 평가 |
|---|---|
| **개인정보 포함 여부** | 집계 통계만 사용 → **비식별 데이터** (개인정보보호법 적용 외) |
| **데이터 라이선스** | 공공데이터포털 OpenAPI = **출처 표시 후 자유 이용** (CC-BY 유사) |
| **재판매 금지 조항** | 네이버 API 와 달리 심평원 OpenAPI 는 **재판매 명시적 금지 없음** — 다만 가공 후 제공 시 출처 명시 필수 |
| **로그 보존** | API 호출 로그 6개월 이상 보존 (ISMS-P 2.9 충족) |
| **감염병예방법 호환** | 심평원 데이터는 **공식 보고 기반** — 우리 시스템이 "보조 지표"임을 더 명확히 입증 |

## 6. 일정·산출물

| 시점 | 작업 | 담당 |
|---|---|---|
| **W18 (5/4~5/10)** | OpenAPI 활용 신청 + 인증키 발급 + `.env.example` 키 추가 | 이우형 |
| **W19 (5/11~5/17)** | `hira_collector.py` 구현 + 단위 테스트 (Mock) + Kafka 토픽 추가 | 이우형 |
| **W20 (5/18~5/24)** | walk-forward 검증에 HIRA AUX 신호 반영 → F1 변화 측정 | 박진영 |
| **W21 (5/25~5/31)** | Bigdata Hub 연구 신청서 작성·제출 (4~6주 대기) | 박진영 |
| **W26 (6월말)** | Bigdata Hub 분석 환경 접근 → 표본 청구 데이터로 백테스트 | 박진영 |

### 산출물
- `pipeline/collectors/hira_collector.py`
- `tests/test_hira_collector.py` (Mock 사용)
- `docs/integrations/hira-opendata.md` (이 문서, 갱신)
- `docs/architecture.md` 의 Layer 다이어그램에 AUX_HIRA 추가
- Slide 6 의 "제외" 표에서 "심평원 API" 항목 → "**Phase 2 연결 완료**" 로 갱신

## 7. 리스크·완화

| 리스크 | 완화 |
|---|---|
| 활용 신청 반려 | 학술·공공 보건 목적 명시 → 통상 승인. 반려 시 사유 보강 후 재신청 |
| 일일 한도 초과 | 시·군·구 250개 × 5질병 = 1,250건/일 → 한도(10,000) 내 안전 |
| API 스키마 변경 | `pdfplumber` 처럼 **스키마 변경 감지 → 즉시 PDFParseError 류 명시적 예외** (silent fail 금지) |
| Bigdata Hub 신청 4~6주 지연 | OpenAPI 만으로 W20 walk-forward 검증 진행 가능 (Hub 는 강화용) |
| 시·군·구 행정코드 변경 | 통계청 표준 SIDO 코드 매핑 테이블 별도 관리 (`pipeline/data/sgg_codes.csv`) |

## 8. 발표(중간/최종) 반영

### 중간발표 (4/30) — **언급만**
- Slide 5 의 "심평원 처방약 + K-WBE API" 가 미접근 상태임을 솔직 인정 (**현재 상태 유지**)
- Q&A 대비: "심평원 연결은 Phase 2 W18~W20 작업 — 활용 신청서는 발표 다음 날 즉시 제출 예정" 답변 준비

### 최종발표 (6월 초) — **연결 결과 시연**
- Slide 6 의 "제외" 표에서 심평원 항목 제거, "추가" 표에 **"심평원 OpenAPI L1 보강 (W18~W20)"** 추가
- F1 walk-forward 재측정 결과 (HIRA AUX 추가 전 0.643 → 추가 후 ?) 비교 표
- 라이브 데모: Streamlit 검증 탭에 "L1 보강: 심평원 외래 빈도" 라인 추가

## 9. 참고 링크

- 메인 포털: <https://opendata.hira.or.kr/home.do>
- OpenAPI 가이드: <https://opendata.hira.or.kr/op/opc/selectOpenData.do>
- 공공데이터포털 (B551182): <https://www.data.go.kr/data/15001062/openapi.do>
- Bigdata Hub 연구신청: <https://opendata.hira.or.kr/op/opb/selectMockExmptManageList.do>
- 표본자료셋 안내: HIRA-NPS (National Patient Sample) 100만명 표본 외래/입원

---

*최종 갱신: 2026-04-28 — Phase 2 (W18~W20) 작업 완료 후 v1.0 정식 발행. 발표 자료(Slide 5/6) 동시 갱신.*
