const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status} ${path}`);
  return res.json() as Promise<T>;
}

export const fetchSignalTimeseries = (url: string) => apiFetch<{ series: unknown[] }>(url);
export const fetchCurrentAlert = (url: string) => apiFetch<Record<string, unknown>>(url);
export const fetchLatestSignals = (url: string) => apiFetch<Record<string, unknown>>(url);
export const fetchForecast = (url: string) => apiFetch<Record<string, unknown>>(url);
