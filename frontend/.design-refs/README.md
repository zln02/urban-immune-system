# .design-refs/ — 외부 디자인 레퍼런스 스냅샷

> Claude Design 에 업로드용 · Claude Code 가 `Read` 할 때 컨텍스트 주입용.

## 파일

| 파일 | 출처 | 용도 |
|---|---|---|
| `ibm-carbon.md` | VoltAgent/awesome-design-md `ibm/` (getdesign CDN) | IBM Carbon 디자인 시스템 상세 명세 (332줄) |

## 관리 정책

- 업데이트 주기: 상용화 방향 변경 시 또는 분기 1회
- 업데이트 방법: `npx getdesign@latest add ibm` 재실행 → 덮어쓰기
- 여기 있는 파일은 **참조 전용**. 실제 코드에 직접 import 하지 않는다.
- 새 레퍼런스 추가 시 위 표도 업데이트.

## 추가 후보 (필요 시)

- Vercel (`npx getdesign@latest add vercel`)
- ClickHouse (`npx getdesign@latest add clickhouse`)
- KRDS Figma library v1.0.0 (https://www.krds.go.kr 에서 수동 다운로드)

## 왜 여기에?

`frontend/` 스코프 안에 두면 frontend 에이전트가 자동으로 컨텍스트로 인식.
루트에 두면 backend/pipeline 까지 혼란. `.design-refs/` (숨김) 로 접근성과 분리 동시 확보.
