"use client";

import { useQuery } from "@tanstack/react-query";
import { API_BASE } from "@/lib/api";

export type AlertLevel = "GREEN" | "YELLOW" | "ORANGE" | "RED";

export interface RegionAlert {
  region: string;
  composite: number;
  alert_level: AlertLevel;
  l1: number;
  l2: number;
  l3: number;
  layers_above_30: number;
  latest_time: string | null;
}

interface RegionAlertsResponse {
  window_days: number;
  count: number;
  alerts: RegionAlert[];
}

async function fetchRegionAlerts(days = 28): Promise<RegionAlertsResponse> {
  const res = await fetch(`${API_BASE}/api/v1/alerts/regions?days=${days}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`alerts/regions ${res.status}`);
  return res.json();
}

/** 17 시·도 일괄 경보 조회 — alert-table용 */
export function useRegionAlerts(days = 28) {
  return useQuery<RegionAlertsResponse, Error>({
    queryKey: ["alerts", "regions", days],
    queryFn: () => fetchRegionAlerts(days),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });
}
