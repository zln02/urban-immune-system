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

async function apiFetch<T>(path: string): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status} ${path}`);
  return res.json() as Promise<T>;
}

export const fetchSignalTimeseries = (url: string) => apiFetch<{ data?: { time: string; value: number }[]; series?: unknown[] }>(url);
export const fetchCurrentAlert = (url: string) => apiFetch<Record<string, unknown>>(url);
export const fetchLatestSignals = (url: string) => apiFetch<Record<string, unknown>>(url);
export const fetchForecast = (url: string) => apiFetch<Record<string, unknown>>(url);

export function timeseriesUrl(layer: "otc" | "wastewater" | "search", region: string, days = 365): string {
  return `/api/v1/signals/timeseries?layer=${layer}&region=${encodeURIComponent(region)}&days=${days}`;
}

export function currentAlertUrl(region: string): string {
  return `/api/v1/alerts/current?region=${encodeURIComponent(region)}`;
}
