# 회의록 / 팀 온보딩 자료

## 규칙
- 파일명: `YYYY-MM-DD_제목.md` (예: `2026-04-15_팀킥오프.md`)
- 주간 정기 회의: 매주 이곳에 추가
- 킥오프/발표 자료: `.pptx` + `.pdf` 동시 보관 (PDF 는 배포용, PPTX 는 편집용)
- 음성 전사: 별도 `transcripts/` 폴더 (추가 예정)

## 목록
- `2026-04-15_팀킥오프.md` — 팀 5명 역할·GitHub 협업 규칙·환경 세팅·캡스톤 1등 진입 플랜
- `setup-per-role.md` — 팀원별 SSH·venv·Claude Code 실습 가이드

## 생성 파이프라인
```bash
# MD → PPTX 자동 생성
python scripts/gen_kickoff_pptx.py

# PPTX → PDF 변환
libreoffice --headless --convert-to pdf docs/meeting-notes/2026-04-15_팀킥오프.pptx \
  --outdir docs/meeting-notes/
```
