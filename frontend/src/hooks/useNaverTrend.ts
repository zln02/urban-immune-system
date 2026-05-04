"use client";

import { useQuery } from "@tanstack/react-query";

export interface TrendPoint {
  date: string;
  raw: number;
  value: number; // 0~1 정규화
}

export interface TrendResponse {
  series: TrendPoint[];
  startDate: string;
  endDate: string;
  layer: "otc" | "search";
}

async function fetchTrend(layer: "otc" | "search", weeks = 12): Promise<TrendResponse> {
  const res = await fetch(`/api/naver/${layer}?weeks=${weeks}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `Naver ${layer} API error ${res.status}`);
  }
  return res.json();
}

/** Layer 1 (OTC 쇼핑인사이트) 트렌드 — 12주 */
export function useOtcTrend(weeks = 12) {
  return useQuery<TrendResponse, Error>({
    queryKey: ["naver", "otc", weeks],
    queryFn: () => fetchTrend("otc", weeks),
    staleTime: 60 * 60 * 1000, // 1시간 (네이버 DataLab 실시간성 한계)
    retry: 2,
  });
}

/** Layer 3 (데이터랩 검색어) 트렌드 — 12주 */
export function useSearchTrend(weeks = 12) {
  return useQuery<TrendResponse, Error>({
    queryKey: ["naver", "search", weeks],
    queryFn: () => fetchTrend("search", weeks),
    staleTime: 60 * 60 * 1000,
    retry: 2,
  });
}
