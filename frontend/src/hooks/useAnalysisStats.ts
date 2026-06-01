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
  mean_lead_weeks?: number;
  n_regions_with_lead?: number;
}

interface BacktestFile {
  summary: BacktestSummary;
}

export interface TftRegressionMetric {
  n: number;
  n_dropped_nan?: number;
  mae: number | null;
  mape_percent: number | null;
  rmse: number | null;
  mean_true: number;
  mean_pred: number;
}

export interface TftRegressionEvaluation {
  checkpoint: string;
  n_sequences: number;
  prediction_length: number;
  overall: TftRegressionMetric;
  by_horizon: Record<string, TftRegressionMetric>;
  by_region: Record<string, Record<string, TftRegressionMetric>>;
}

export interface TftRegressionFile {
  generated_at: string;
  purpose: string;
  target_semantics: string;
  data_summary: {
    n_rows: number;
    n_regions: number;
    regions: string[];
    time_idx_max: number;
  };
  evaluations: Record<string, TftRegressionEvaluation>;
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

export function useTftRegression() {
  return useQuery<TftRegressionFile, Error>({
    queryKey: ["analysis", "tft_regression_17"],
    queryFn: () =>
      fetchJson<TftRegressionFile>("/data/tft_regression_backtest_17regions.json"),
    staleTime: 5 * 60 * 1000,
  });
}

export interface CovidBacktestSummary {
  primary_evaluation: string;
  note: string;
  pooled_f1: number;
  pooled_precision: number;
  pooled_recall: number;
  pooled_far: number;
  pooled_mcc: number;
  pooled_auprc: number;
  pooled_n: number;
  pooled_n_pos: number;
}

export interface CovidBacktestFile {
  generated_at: string;
  purpose: string;
  honesty_note: string;
  config: Record<string, unknown>;
  summary: CovidBacktestSummary;
}

export function useCovidBacktest() {
  return useQuery<CovidBacktestFile, Error>({
    queryKey: ["analysis", "covid_backtest_17"],
    queryFn: () =>
      fetchJson<CovidBacktestFile>("/data/backtest_xgboost_covid_17regions.json"),
    staleTime: 5 * 60 * 1000,
  });
}
