# 팀원 GitHub 협업 가이드 (실전)

> v1.0 | 2026-04-21 | 박진영
> 이 문서는 팀원 4명(이경준·이우형·김나영·박정빈)이 **실제로 첫 PR 을 머지**할 수 있도록 step-by-step.

---

## 0. 현재 상태 진단 (솔직히)

| 항목 | 상태 | 액션 |
|---|---|---|
| GitHub Collaborator | 2명 초대 완료 (zln02·dsadsa2311245·ughyeon123-source), **2명 미초대** | 박진영: 김나영·박정빈 초대 (아래 §1) |
| Branch Protection | 🔴 없음 (main/develop 직접 push 가능) | 박진영: 웹 UI 설정 (§2) |
| 열린 이슈 | 🔴 **0건** — 팀원이 뭘 할지 모름 | 오늘 생성 (§3) |
| 팀원 커밋 | 🔴 **0건** (zln02 외) | 이번 주 각자 1건 목표 |
| CODEOWNERS 매핑 | 🟡 @zln02 만 가리킴 | 실제 계정 확인 후 갱신 (§1) |

---

## 1. 박진영(PM) 이 **오늘 30분 내** 해야 할 것

### 1-1. 미초대 팀원 2명 초대
```
https://github.com/zln02/urban-immune-system/settings/access
→ "Add people" 클릭
→ 김나영 GitHub 계정 입력 → Role: Write
→ 박정빈 GitHub 계정 입력 → Role: Maintain
```

### 1-2. 기존 2명 계정 확인
- `dsadsa2311245`, `ughyeon123-source` 가 누군지 팀 Discord/카톡에서 물어보기
- 확인되면 `.github/CODEOWNERS` 파일의 `@zln02` 를 해당 팀원 계정으로 교체

### 1-3. Branch Protection 활성화 (필수 — B2G 규정)
```
Settings > Branches > Add rule

브랜치: main
  [v] Require a pull request before merging
      Required approving reviews: 2
      [v] Require review from Code Owners
  [v] Require status checks to pass
      필수 체크: backend-lint, backend-test, pipeline-lint, ml-lint,
                 frontend-lint, legacy-test, Trivy FS Scan, CodeQL
  [v] Require linear history
  [v] Include administrators

브랜치: develop
  [v] Require a pull request before merging
      Required approving reviews: 1
  [v] Require status checks to pass (동일 6개)
```

### 1-4. Labels 준비 (자동 생성 스크립트 실행)
```bash
cd ~/urban-immune-system
bash scripts/setup_github_labels.sh
```

### 1-5. Secrets 등록
```
Settings > Secrets and variables > Actions > New repository secret
  NAVER_CLIENT_ID · NAVER_CLIENT_SECRET · KMA_API_KEY
  OPENAI_API_KEY · ANTHROPIC_API_KEY
  GCP_PROJECT_ID · GCP_WORKLOAD_IDENTITY_PROVIDER · GCP_SERVICE_ACCOUNT
```

---

## 2. 팀원 각자 **오늘 해야 할 것** (15분)

### 공통 온보딩
```bash
# 1) GitHub 초대 이메일 수락
# 2) SSH 공개키를 박진영에게 전달 (authorized_keys 등록용)
# 3) 서버 접속
ssh wlsdud5035@34.64.124.90
cd ~/urban-immune-system
git fetch origin

# 4) 자기 모듈에서 Claude Code 기동 (배지 확인)
cd <모듈>       # backend / pipeline / src / frontend / infra / tests
claude
```

### 당장 자기 이슈 확인
```bash
gh issue list --assignee @me
```
→ 아래 §3 에서 박진영이 미리 생성한 이슈 1개가 각자 assign 됨

---

## 3. 팀원별 첫 기여 이슈 (박진영이 오늘 생성)

| # | 담당 | 제목 | 난이도 | 예상 시간 | 시작 파일 |
|---|---|---|---|---|---|
| #3 | **이경준** (Backend) | `[backend] /api/v1/signals/latest 실 DB 쿼리 활성화` | 🟡 중 | 3~4h | `backend/app/api/signals.py` |
| #4 | **이우형** (Pipeline) | `[pipeline] Kafka Consumer 1개 구현 → TimescaleDB 적재` | 🟡 중 | 4~6h | `pipeline/collectors/kafka_consumer.py` (신규) |
| #5 | **김나영** (Frontend) | `[src] validation 탭 JSON 연동 동작 검증 + PDF 다운로드 버튼` | 🟢 쉬움 | 2~3h | `src/tabs/validation.py`, `src/tabs/report.py` |
| #6 | **박정빈** (DevOps/QA) | `[infra] Branch Protection 설정 + Dependabot 활성화 + 테스트 커버리지 리포트` | 🟢 쉬움 | 2h | `.github/`, `docs/business/isms-p-checklist.md` |

**각 이슈에 자세한 스펙·수용 기준·참고 링크 포함** — Issue 제목을 클릭하면 확인.

---

## 4. 첫 PR 만드는 법 (팀원 공용 5단계)

```bash
# 1) 최신 develop 동기화
cd ~/urban-immune-system
git fetch origin
git checkout develop
git pull origin develop

# 2) 자기 feature 브랜치 생성
git switch -c feature/<이니셜>-<작업명>
# 예: feature/ljn-signals-db-query  (이경준)
#     feature/lwh-kafka-consumer     (이우형)
#     feature/nyk-pdf-download       (김나영)
#     feature/pjb-branch-protection  (박정빈)

# 3) Claude 에게 도움 요청하며 작업
cd <모듈> && claude
# → "이슈 #3 내용대로 signals.py 실 DB 쿼리 붙여줘"

# 4) 로컬 검증
pytest tests/ -q
ruff check .

# 5) 커밋 + push + PR
git add -A
git commit -m "feat(<scope>): <한 줄 요약>

Closes #<이슈번호>

- 변경점 1
- 변경점 2
"
git push -u origin feature/<이니셜>-<작업명>
gh pr create --base develop --fill
```

### PR 템플릿이 자동 뜸
`.github/pull_request_template.md` 가 강제하는 체크리스트:
- [ ] pytest 통과
- [ ] ruff lint 통과
- [ ] SQL 파라미터 바인딩 (ISMS-P)
- [ ] CORS allowlist · 기본 비밀번호 없음
- [ ] 영향받는 `docs/business/` 문서 검토

---

## 5. 리뷰 에티켓 (모두)

### 좋은 리뷰
- 24시간 내 응답 (급할 땐 Discord 에서 재촉 OK)
- `nit:` 접두어는 머지 블록 아님 (개선 제안)
- `suggestion:` 접두어로 대안 코드 제시
- LGTM 만 쓰지 말고 **"왜 승인하는지 한 줄"** 남기기

### 승인 규칙
- `develop` PR: CODEOWNER 1명 승인 → 머지 가능
- `main` PR: CODEOWNER + 박진영 2명 승인 필수
- 자기 PR 은 자기가 머지 (but 승인은 타인이)

---

## 6. 주간 일지 연동

매주 **일요일 22:00 KST** 까지:
```bash
cp docs/weekly-reports/_template.md docs/weekly-reports/2026-W18/<이름>.md
# 채우기 → 본인 브랜치에서 커밋 → develop PR 에 포함
```

박진영이 월요일 오전:
```bash
/weekly-report W18                           # SUMMARY 자동 병합
python scripts/update_scoreboard.py W18      # 기여도 집계
```

---

## 7. FAQ

### Q. git push 할 때 인증 에러
```bash
gh auth login --git-protocol https --web
gh auth setup-git
```

### Q. 내 모듈이 아닌 코드를 건드려야 한다
- Discord `#uis-dev` 에 먼저 멘션 → 담당자 동의 후 작업
- PR 에 해당 담당자를 `Reviewers` 로 추가

### Q. 테스트가 깨진다
- `pytest tests/ -v --tb=short` 로 스택 트레이스 확인
- 본인 변경 때문이면 수정, 기존부터 깨진 거면 박정빈 호출

### Q. CI 가 계속 실패한다
- PR 페이지 "Checks" 탭 → 실패 Job 로그 확인
- 대부분: ruff (`ruff check --fix .`) 또는 테스트 누락

### Q. 내 이슈가 어려워서 혼자 못 풀겠다
- Discord `#uis-help` 에 증상 복붙 → Claude 에게 먼저 물어보고 그래도 안 되면 팀원 호출

---

## 8. 성공 조건 (이번 주 W18)

- [ ] 팀원 4명 전부 서버 접속 + `cd <모듈> && claude` 배지 확인
- [ ] 팀원 4명 각자 **PR 1건 open** (이슈 #3-6)
- [ ] PR 최소 1건 이상 develop 머지
- [ ] 팀원 4명 각자 주간 일지 (docs/weekly-reports/2026-W18/) 작성
- [ ] Branch Protection main·develop 활성화
- [ ] Scoreboard W18 첫 집계

**이거 달성하면 캡스톤 팀으로 진짜 가동 시작.** 현재 "박진영 원맨쇼" → "5인 협업" 전환점.

---

## 참고
- 킥오프 PDF: `docs/meeting-notes/2026-04-15_팀킥오프.pdf`
- 팀원별 CLI 가이드: `docs/meeting-notes/setup-per-role.md`
- 포트폴리오 자동 메모리: `docs/portfolio/`
