# TS-001: Qdrant 컨테이너 healthcheck 실패 (curl not found)

- **발생**: 2026-04-15 17:00 KST
- **모듈**: infra (docker-compose)
- **담당자**: @zln02 (박진영) · @park-jungbin 영역
- **심각도**: 🟡 Major (데모 시 Qdrant unhealthy 표시)

## 증상
`sudo docker compose ps` 에서 uis-qdrant 가 `unhealthy` 상태. 로그:
```
/bin/sh: 1: curl: not found
```
healthcheck 가 매번 실패해 컨테이너가 ready 상태로 올라오지 못함.

## 원인 추적
- **시도 1**: Qdrant 공식 이미지에 curl 이 있는지 확인 → `docker exec uis-qdrant which curl` → **미설치**
- **시도 2**: wget 있는지 확인 → **없음**
- **시도 3**: Qdrant 이미지는 distroless 에 가까움, 네트워크 도구 의존 불가
- **근본 원인**: `docker-compose.yml` 의 healthcheck 가 `curl -sf http://localhost:6333/readyz` 인데 이미지에 curl 미설치

## 해결
`docker-compose.yml` healthcheck 를 bash TCP probe 로 교체:
```yaml
healthcheck:
  test: ["CMD-SHELL", "bash -c 'exec 3<>/dev/tcp/127.0.0.1/6333' >/dev/null 2>&1 || exit 1"]
```
커밋: [aa874ca](https://github.com/zln02/urban-immune-system/commit/aa874ca)

## 배운 점 (재발 방지)
1. **공식 이미지 의존 유틸 미설치 가능성 항상 확인** — `docker exec <container> which <tool>`
2. **TCP 레벨 probe 가 HTTP 보다 안전** — bash 의 `/dev/tcp` 는 외부 의존 없음
3. **distroless 이미지 트렌드 인지** — 2025 이후 이미지 사이즈 최소화 경향, 디버깅 도구 부재 기본
4. **healthcheck 실패 로그 반드시 확인** — `docker inspect <container> --format '{{json .State.Health}}'`

## 관련 커밋 / PR
- aa874ca (docker-compose.yml healthcheck 수정)
- PR #2 포함
