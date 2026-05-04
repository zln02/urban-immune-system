"use client";

import { useQuery } from "@tanstack/react-query";
import { API_BASE } from "@/lib/api";

export interface SignalPoint {
  time: string;
  value: number;
}

export interface SignalTimeseriesResponse {
  layer: string;
  region: string;
  data: SignalPoint[];
}

async function fetchTimeseries(
  layer: "otc" | "wastewater" | "search",
  region: string,
  days: number,
): Promise<SignalTimeseriesResponse> {
  const url = `${API_BASE}/api/v1/signals/timeseries?layer=${layer}&region=${encodeURIComponent(region)}&days=${days}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`signals/timeseries ${layer} ${res.status}`);
  return res.json();
}

// 백엔드 /signals/timeseries 의 region 파라미터는 min_length=2.
// 빈 문자열 또는 1글자 region 으로 호출하면 422 발생 → enabled 가드.
const isValidRegion = (region: string): boolean => region.trim().length >= 2;

/** Layer 2 KOWAS 하수 시계열 (TimescaleDB 직접 조회) */
export function useWastewaterSeries(region: string, days = 365) {
  return useQuery<SignalTimeseriesResponse, Error>({
    queryKey: ["signals", "wastewater", region, days],
    queryFn: () => fetchTimeseries("wastewater", region, days),
    staleTime: 60 * 60 * 1000,
    retry: 1,
    enabled: isValidRegion(region),
  });
}

/** 단일 layer 일반 사용 */
export function useSignalSeries(layer: "otc" | "wastewater" | "search", region: string, days = 365) {
  return useQuery<SignalTimeseriesResponse, Error>({
    queryKey: ["signals", layer, region, days],
    queryFn: () => fetchTimeseries(layer, region, days),
    staleTime: 60 * 60 * 1000,
    retry: 1,
    enabled: isValidRegion(region),
  });
}
