# 팀원 온보딩 (Discord DM 용)

> 각자 본인 파일 읽으세요. **5분 안에 시작** 가능하게 복사-붙여넣기 명령 포함.

---

## 🎯 본인 파일 열기

| 팀원 | 역할 | 이슈 | 파일 |
|---|---|---|---|
| 👑 박진영 | PM / ML Lead | — | [박진영.md](박진영.md) |
| 🖥 이경준 | Backend | [#3](https://github.com/zln02/urban-immune-system/issues/3) | [이경준.md](이경준.md) |
| 🔥 이우형 | Data Engineer | [#4 (critical)](https://github.com/zln02/urban-immune-system/issues/4) | [이우형.md](이우형.md) |
| 📱 김나영 | Frontend | [#5](https://github.com/zln02/urban-immune-system/issues/5) | [김나영.md](김나영.md) |
| 🛡 박정빈 | DevOps / QA | [#6](https://github.com/zln02/urban-immune-system/issues/6) | [박정빈.md](박정빈.md) |

---

## 📖 모두 먼저 읽을 것 (5분)

1. **[../team-explainer.md](../team-explainer.md)** — 탐정 3명 비유 (이 프로젝트 뭐하는지)
2. **[../collaboration-guide.md](../collaboration-guide.md)** — GitHub 협업 규칙

---

## 🎯 공통 구조 (4명 모두 동일)

각 온보딩 파일은 다음 순서로 구성:
1. 이번 주 목표 한 줄
2. 지금 상태 (버그·할 것)
3. **5분 안에 시작** (복사-붙여넣기 명령)
4. **Claude 에게 붙여넣을 프롬프트** (1개 이상)
5. 완료 증명 5-6단계
6. 자주 막히는 지점 FAQ
7. 보너스 (여유 있을 때)

---

## 🆘 공통 FAQ (4명 공통)

### "SSH 접속 안 돼요"
```bash
# 본인 공개키를 박진영에게 먼저 전달했는지 확인
cat ~/.ssh/id_ed25519.pub  # 또는 id_rsa.pub
# 이 출력을 박진영 DM 으로
# 박진영이 authorized_keys 에 추가하면 접속 가능
```

### "git push permission denied"
```bash
gh auth login --git-protocol https --web
gh auth setup-git
```

### "Claude 명령어가 없어요"
```bash
# 서버에는 이미 설치됨. 로컬에서 쓰고 싶으면:
npm install -g @anthropic-ai/claude-code
# 또는 공식 설치 스크립트
```

### "venv 가 이상해요"
```bash
cd ~/urban-immune-system
source .venv/bin/activate
which python  # /home/wlsdud5035/urban-immune-system/.venv/bin/python 이어야
```

### "에러 났는데 어떻게 해요"
1. 30분 이상 고민하지 말기
2. 에러 메시지 **전체** 복사
3. Discord `#uis-help` 에 붙여넣기
4. Claude 에게 먼저 물어보기: `cd <모듈> && claude` → 에러 붙여넣기

---

## 🎯 W18 공통 목표

- [ ] 전원 SSH 접속 성공 + `cd <모듈> && claude` 배지 확인
- [ ] 팀원 4명 각자 PR 1건 open
- [ ] 최소 1건 develop 머지
- [ ] 주간 일지 작성 (docs/weekly-reports/2026-W18/)
- [ ] authored-by 포스트 1편씩

달성 시 "박진영 원맨쇼" 우려 완전 해소.

---

## 📊 성공 지표 (스코어보드)

박진영이 월요일 오전 `python scripts/update_scoreboard.py W18` 실행 → 자동 집계

총점 = 커밋×1 + PR머지×5 + PR리뷰×2 + 테스트LoC/10 + 이슈×1

**1위 → 다음 회의 아젠다 선택권 (15분)**
