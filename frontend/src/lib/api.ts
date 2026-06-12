// 백엔드 base URL 우선순위:
//   1) NEXT_PUBLIC_API_BASE_URL 환경변수 (명시 설정 시 최우선)
//   2) 클라이언트 런타임: 빈 문자열 → 같은 origin 의 Next.js proxy (/api/v1/*) 사용
//      외부에서 8001 직접 차단된 환경에서도 동작
//   3) SSR 기본값: localhost:8001 직접
// 우리 백엔드는 8001 (8000은 사이드 게임 프로젝트 점유)
function resolveApiBase(): string {
  const env = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (env) return env;
  if (typeof window !== "undefined") return ""; // relative URL → /api/v1/* 프록시
  return "http://localhost:8001";
}
export const API_BASE = resolveApiBase();

