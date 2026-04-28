"use client";

import { useQuery } from "@tanstack/react-query";

export interface LeadTimeSummary {
  region: string;
  signal_lead_weeks: { l1_otc: number; l2_wastewater: number; l3_search: number; composite: number };
  ccf_max: { l1_otc: number; l2_wastewater: number; l3_search: number; composite: number };
  granger_p: { l1_otc: number; l2_wastewater: number; l3_search: number; composite: number };
}

export interface BacktestSummary {
  total_regions: number;
  ok_regions: number;
  mean_recall: number;
  mean_precision: number;
  mean_f1: number;
  mean_far_with_gate: number;
}

interface BacktestFile {
  summary: BacktestSummary;
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json() as Promise<T>;
}

export function useLeadTime() {
  return useQuery<LeadTimeSummary, Error>({
    queryKey: ["analysis", "lead_time"],
    queryFn: () => fetchJson<LeadTimeSummary>("/data/lead_time_summary.json"),
    staleTime: 5 * 60 * 1000,
  });
}

export function useBacktest17() {
  return useQuery<BacktestFile, Error>({
    queryKey: ["analysis", "backtest_17"],
    queryFn: () => fetchJson<BacktestFile>("/data/backtest_17regions.json"),
    staleTime: 5 * 60 * 1000,
  });
}
