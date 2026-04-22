## 변경 요약

## 관련 Issue
Closes #

## 테스트 방법
```bash
# 예: 
pytest tests/
curl http://localhost:8000/...
```

## 체크리스트
- [ ] `pytest tests/` 통과
- [ ] `ruff check` 통과 (해당 모듈)
- [ ] 타입 힌트 추가 (public 함수)
- [ ] SQL 쿼리는 파라미터 바인딩 사용 (`$1`/`:param`)
- [ ] CORS `*` 없음, `ALLOWED_ORIGINS` allowlist
- [ ] 기본 비밀번호(`changeme`, `password` 등) 없음
- [ ] API 키·토큰 로그 마스킹
- [ ] 영향받는 `docs/business/` 문서 확인 (ISMS-P, 가격, 로드맵 등)
- [ ] 테스트 커버리지 감소 없음

## 스크린샷 (UI 변경 시)

## 추가 노트
