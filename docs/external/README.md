# External API Specifications

KDCA 및 외부 공공 API 인터페이스 정의서 보관소. 코드에서 참조할 때 출처를 명시할 수 있도록 원본 명세서를 함께 저장한다.

## 자료 목록

| 파일 | 출처 | 용도 |
|---|---|---|
| `api-specs/전수신고 감염병 발생현황 API 인터페이스 정의서_v.1.0.xlsx` | KDCA / data.go.kr publicDataPk=15139178 (EIDAPIService) | L1/L3 1·2·3급 감염병 라벨 수집 — `pipeline/collectors/kdca_label_collector.py` PascalCase 경로 매핑 근거 |

## 참고

- KDCA 4급 표본감시 (인플루엔자·COVID·노로 등) 는 별도 포털 (`dportal.kdca.go.kr/pot/is/st/influ.do`) — API 가 아닌 CSV 다운로드. `pipeline/collectors/kdca_sentinel_parser.py` 가 처리.
- KOWAS 하수감시 PDF 는 `pipeline/data/kowas/` 에 원본 보관, `pipeline/collectors/wastewater.py` 에서 파싱.
- API 키 (`KDCA_API_KEY`, `NAVER_CLIENT_ID/SECRET`, `KMA_API_KEY`) 는 `.env` 에서만 관리, 명세서 자체는 키를 포함하지 않으므로 commit 안전.
