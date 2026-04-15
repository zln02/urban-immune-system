# Urban Immune System — 팀 포트폴리오

팀 5명이 개발하면서 쌓이는 **시행착오 · 의사결정 · 마일스톤**을 자동 기록하는 공간.
Claude Code 세션 종료 시 Stop 훅이 타임라인에 append 하고, 커밋 메시지 접두어로 하위 폴더에 분류 저장.

## 구조

```
docs/portfolio/
├── README.md                   # 이 파일
├── timeline.md                 # 세션별 자동 타임라인
├── decisions/                  # ADR (Architecture Decision Record)
│   ├── _template.md
│   └── ADR-{번호}_{제목}.md
├── retrospectives/             # 주간 회고
│   └── {YYYY-WW}_회고.md
├── milestones/                 # v0.1, v0.2, ... 주요 마일스톤
│   └── {태그}_{제목}.md
└── troubleshooting/            # 시행착오 + 해결
    ├── _template.md
    └── TS-{번호}_{제목}.md
```

## 자동 기록 규칙

### 세션 종료 시 (Stop hook)
`~/.claude/hooks/append_portfolio_log.sh` 가 `timeline.md` 에 한 줄 추가:
```
- 2026-04-15 21:30 KST · ml/ · feature/pjy-p0-metrics · HEAD=abc1234 · 변경 3파일
```

### 커밋 메시지 접두어로 분류
```bash
git commit -m "decision: Prefect 으로 Kafka 교체"
# → decisions/ADR-{N}_Prefect_으로_Kafka_교체.md 자동 생성 (템플릿 복사)

git commit -m "troubleshoot: Qdrant healthcheck curl not found"
# → troubleshooting/TS-{N}_Qdrant_healthcheck_curl_not_found.md 자동 생성

git commit -m "milestone: v0.2 Phase 2 데이터 흐름 고정"
# → milestones/v0.2_Phase2_데이터_흐름_고정.md 자동 생성
```
생성된 파일은 스켈레톤만 만들어지고, 담당자가 **맥락·해결·배운 점**을 채운다.

### 주간 회고
매주 금요일 수동 작성 (자동화 X): `retrospectives/2026-W15_회고.md` 등.

## 포트폴리오 HTML 빌드

```bash
python scripts/build_portfolio.py
# → docs/portfolio/portfolio.html 생성
# 브라우저로 열어 타임라인·결정·시행착오를 한눈에
```

캡스톤 발표 시 이 `portfolio.html` 을 열어 "우리가 어떤 결정을 거쳐 왔는지"를 심사자에게 보여줄 수 있음.

## 지금까지 누적
- ADR: 0 건 (예정)
- 시행착오: 0 건
- 마일스톤: 0 건
- 회고: 0 건

첫 항목을 만들고 싶다면: `_template.md` 복사 후 내용 채우기.
