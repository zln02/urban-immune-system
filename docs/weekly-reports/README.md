# 주간 보고서 (Weekly Reports)

> 작성 규칙과 제출 절차를 정리한 가이드. 교수님 제출본 포함.

## 폴더 구조

```
docs/weekly-reports/
├── README.md                    # (이 파일)
├── _template.md                 # 팀원 공용 템플릿
├── guides/                      # 팀원별 이번 주 작업 가이드
│   ├── 이경준_W17.md
│   ├── 이우형_W17.md
│   ├── 김나영_W17.md
│   └── 박정빈_W17.md
├── 2026-W17/                    # 4/20 ~ 4/26
│   ├── 박진영.md
│   ├── 이경준.md
│   ├── 이우형.md
│   ├── 김나영.md
│   ├── 박정빈.md
│   └── SUMMARY.md               # ← 교수님 제출본
└── 2026-W18/                    # 4/27 ~ 5/3
```

## 네이밍 규칙

- 주차 폴더: `YYYY-WNN` (ISO 8601 주차, 월요일 시작)
- 팀원 파일: `{팀원이름}.md` (한글 그대로)
- 통합본: `SUMMARY.md`
- 가이드: `guides/{팀원이름}_W{주차}.md`

## 작성 톤 가이드

교수님이 비전공자 관점에서 읽으시는 것 전제.

| 팀원 | 톤 | 예시 |
|---|---|---|
| 박진영 (PM/ML) | 전문 | "TFT 모델 attention weight 재현" |
| 이경준 (Backend) | 중급 | "백엔드 서버(FastAPI)에 감사 로그 기록 기능 추가" |
| 이우형 (Pipeline) | 중급 | "데이터 수집 파이프라인(Kafka)에서 네이버 API 카테고리 ID 확정" |
| 김나영 (Frontend) | 중급 | "화면 상단에 위험도 경보 표시 컴포넌트 연결" |
| 박정빈 (DevOps/QA) | 비기술 | "테스트 계획서 초안 작성 및 ISMS-P 점검 항목 확인" |

**공통 규칙**
1. 기술 용어는 처음 나올 때 괄호로 풀어 설명 — 예: "RAG(Retrieval-Augmented Generation; 검색한 문서를 참고해 AI가 답변하는 기법)"
2. 단락 3줄 이내 권장
3. 표·리스트 활용 (긴 문장 지양)
4. 이모지 1~2개까지 허용 (과하지 않게)

## 제출 절차

1. 매주 금요일 21:00까지 각 팀원이 본인 파일 채움
2. 박진영이 SUMMARY.md 작성 (팀 전체 진행 + 블로커 + 다음 주 목표)
3. 박진영이 교수님께 `SUMMARY.md` + PDF 변환본 통합 전달
4. GitHub 커밋 (브랜치: `docs/weekly-W17`)

## PDF 변환 (제출용)

```bash
# 루트에서
python3 scripts/reports_to_pdf.py 2026-W17
# 결과: docs/weekly-reports/2026-W17/SUMMARY.pdf
```

## 포맷 보존 주의

- 모든 보고서는 **Markdown 원본**이 진실의 원천. `.docx`/`.pdf`는 생성물.
- PPTX/HWP/Excel 사용 안 함 — 셀 깨짐·폰트 의존 제거.
- 표는 파이프(`|`) 문법만 사용, HTML 테이블 금지.

## 자동 생성

```bash
/weekly-report W17
```
→ git log + PR 목록 + setup-per-role.md를 참고해 5인 초안 자동 생성.

## 관련 문서

- `docs/meeting-notes/setup-per-role.md` — 팀원별 이번 주 작업 canonical
- `docs/portfolio/retrospectives/_template.md` — KPT 양식 (재사용)
- `docs/business/legal-review/` — 법적 검토 로그 (병행)
- `~/.claude/projects/-home-wlsdud5035/memory/retro_YYYY-WNN.md` — 회고 메모리
