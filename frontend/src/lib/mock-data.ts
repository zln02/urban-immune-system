/**
 * 대시보드 데모용 목 데이터 — Backend API 연결 전까지 사용.
 * API 연결 후: lib/api/client.ts 로 교체.
 */

import type { RegionCode } from "./korea-regions";

export interface RiskInfo {
  risk: 1 | 2 | 3 | 4;
  change: number;
  cases: number;
}

export interface AlertItem {
  id: string;
  district: RegionCode;
  level: 3 | 4;
  issued: string;
  confidence: number;
  signals: 1 | 2 | 3;
}

export interface SeriesBundle {
  days: number;
  pharmacy: number[];
  sewage: number[];
  search: number[];
  forecast: { mean: number[]; ci: [number, number][] };
}

const DAYS = 60;

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function genSeries(
  seed: number,
  base: number,
  amp: number,
  rampStart: number,
  rampPeak: number,
): number[] {
  const r = seededRandom(seed);
  const out: number[] = [];
  for (let i = 0; i < DAYS; i++) {
    const weekly = Math.sin((i / 7) * Math.PI * 2) * amp * 0.3;
    const noise = (r() - 0.5) * amp * 0.8;
    const t = i >= rampStart ? (i - rampStart) / (DAYS - rampStart) : 0;
    const ramp = t > 0 ? (rampPeak - base) * Math.pow(t, 1.8) : 0;
    out.push(Math.max(0, base + weekly + noise + ramp));
  }
  return out;
}

function genForecast(last: number, slope: number, days: number) {
  const mean: number[] = [];
  const ci: [number, number][] = [];
  for (let i = 1; i <= days; i++) {
    const v = last + slope * i + Math.sin(i / 3) * 2;
    const w = 4 + i * 0.9;
    mean.push(v);
    ci.push([v - w, v + w]);
  }
  return { mean, ci };
}

const pharmacy = genSeries(7, 42, 6, 38, 88);
const sewage = genSeries(13, 28, 4, 32, 72);
const search = genSeries(29, 55, 10, 45, 118);

export const mockSeries: SeriesBundle = {
  days: DAYS,
  pharmacy,
  sewage,
  search,
  forecast: genForecast(search[DAYS - 1], 1.4, 21),
};

/** 전국 17개 시도 위험도 — Jeolla 권역(JB·JN·GJU) L4 경보. */
export const mockDistricts: Record<RegionCode, RiskInfo> = {
  SEL: { risk: 2, change: 3.2,  cases: 28 },
  INC: { risk: 2, change: 2.1,  cases: 14 },
  GG:  { risk: 3, change: 7.8,  cases: 62 },
  GW:  { risk: 1, change: 0.4,  cases: 6 },
  SJ:  { risk: 2, change: 3.1,  cases: 9 },
  DJ:  { risk: 2, change: 2.8,  cases: 18 },
  CB:  { risk: 2, change: 4.4,  cases: 22 },
  CN:  { risk: 3, change: 8.8,  cases: 34 },
  JB:  { risk: 4, change: 16.8, cases: 72 },
  JN:  { risk: 4, change: 14.2, cases: 58 },
  GJU: { risk: 4, change: 12.6, cases: 41 },
  GB:  { risk: 2, change: 2.1,  cases: 16 },
  DG:  { risk: 2, change: 3.9,  cases: 20 },
  GN:  { risk: 3, change: 6.2,  cases: 28 },
  US:  { risk: 1, change: 1.1,  cases: 5 },
  BS:  { risk: 2, change: 2.7,  cases: 17 },
  JJ:  { risk: 1, change: -0.2, cases: 3 },
};

export const mockAlerts: AlertItem[] = [
  { id: "A-2026-0428-01", district: "JB",  level: 4, issued: "2026-04-28 09:14", confidence: 0.93, signals: 3 },
  { id: "A-2026-0428-02", district: "JN",  level: 4, issued: "2026-04-28 09:21", confidence: 0.89, signals: 3 },
  { id: "A-2026-0428-03", district: "GJU", level: 4, issued: "2026-04-28 09:26", confidence: 0.86, signals: 3 },
  { id: "A-2026-0427-04", district: "CN",  level: 3, issued: "2026-04-27 18:42", confidence: 0.76, signals: 2 },
];
