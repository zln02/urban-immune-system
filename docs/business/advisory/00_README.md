# Urban Immune System — 외부 자문 요청 패키지

> 발송일: 2026-05-02 (예정)
> 발송 주체: 동신대학교 컴퓨터공학과 캡스톤 디자인 팀
> PM: 박진영 (wlsdud5035@gmail.com)
> 발표일: 2026-05-07 (중간발표 1주 후)

## 패키지 구성

| 파일 | 내용 | 발송 대상 |
|---|---|---|
| `00_README.md` | 본 문서 — 자문 요청 개요 | 공통 |
| `10_kdca_request_letter.md` | 질병관리청 자문 요청 공문 초안 | KDCA |
| `11_kisa_consult_application.md` | KISA ISMS-P 사전 컨설팅 신청서 | KISA |
| `20_walk_forward_backtest.pdf` | 17지역 walk-forward 백테스트 검증 리포트 | 공통 |
| `21_architecture_summary.md` | 시스템 구조 요약 (1장 분량) | 공통 |
| `22_dpia_draft.md` | 개인정보 영향평가 (DPIA) 초안 | KISA |
| `30_reproduce_command.txt` | 누가 돌려도 같은 수치를 내는 1줄 명령 | 공통 |
| `31_demo_url.txt` | 라이브 대시보드 + 슬라이드 URL | 공통 |
| `40_code_snapshot.tar.gz` | 핵심 코드 (게이트 B + walk-forward) | 공통 |

## 자문 요청 핵심 (한 줄)

> "동신대학교 학부생 5인 팀이 만든 3계층 비의료 신호 기반 감염병 조기경보 시스템(F1=0.841·5.9주 선행)에 대해, 임상 활용 가능성(KDCA) 및 정보보호 인증 적정성(KISA) 자문을 요청드립니다."

## 본 시스템 핵심 차별점

1. **3계층 교차검증 게이트 B** — 단일신호 단독 경보를 코드 4줄로 영원히 차단 (Google Flu 2013 실패 교훈)
2. **17지역 walk-forward 검증** — F1 0.841 / Precision 0.96 / 평균 5.9주 선행 (Granger p=0.021)
3. **재현 가능성** — `python -m ml.reproduce_validation` 1줄 명령으로 누가 돌려도 같은 수치
4. **B2G 신뢰성 강제** — 면책 조항(ISMS-P 2.9 / EU AI Act 13·14조) 코드 강제 삽입

## 자문 자료 회수 후 처리 계획

- 5/2 발송 → 5/6 회수 목표 (1주)
- 회신 도착 시 발표 슬라이드 S13B "외부 자문 회신 완료" 표기
- 미회신 시 "발송 완료, 회신 대기" 정직 표기
- 회신 내용에 따라 Phase 2 로드맵(2026 H2) 우선순위 조정

## 연락처

- 이메일: wlsdud5035@gmail.com (PM)
- 데모: http://34.158.197.122:3000/dashboard
- 슬라이드: http://34.158.197.122:3000/slides/index.html
- 깃허브: (내부 비공개 — 자문 회신 후 액세스 제공 검토)
