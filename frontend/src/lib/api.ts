// 백엔드 base URL — useAlertStream 과 동일 키(NEXT_PUBLIC_API_BASE_URL) 사용
// 우리 백엔드는 8001 (8000은 사이드 게임 프로젝트 점유)
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

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
