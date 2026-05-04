import type { RegionCode } from "./korea-regions";

export interface AlertRecord {
  id: string;
  region: string;
  regionCode: RegionCode;
  level: 1 | 2 | 3 | 4;
  time: string;
  summary: string;
}

export interface DistrictData {
  risk: 1 | 2 | 3 | 4;
  cases: number;
  change: number;
}

export interface SeriesData {
  pharmacy: number[];
  sewage: number[];
  search: number[];
}

function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function makeSeries(seed: number, len: number, base: number, amp: number): number[] {
  const rand = rng(seed);
  const arr: number[] = [];
  let v = base;
  for (let i = 0; i < len; i++) {
    v += (rand() - 0.48) * amp;
    arr.push(Math.max(0, Math.min(100, v)));
  }
  return arr;
}

export const mockSeries: SeriesData = {
  pharmacy: [
    ...makeSeries(1, 45, 30, 8),
    ...makeSeries(2, 15, 65, 12),
  ],
  sewage: [
    ...makeSeries(3, 42, 25, 6),
    ...makeSeries(4, 18, 72, 10),
  ],
  search: [
    ...makeSeries(5, 48, 20, 7),
    ...makeSeries(6, 12, 58, 15),
  ],
};

export const mockDistricts: Record<RegionCode, DistrictData> = {
  JB: { risk: 4, cases: 2847, change: 38.4 },
  JN: { risk: 4, cases: 1923, change: 31.2 },
  GJ: { risk: 3, cases: 1104, change: 18.7 },
  GN: { risk: 3, cases: 987,  change: 14.3 },
  CB: { risk: 2, cases: 654,  change: 9.1  },
  CN: { risk: 2, cases: 543,  change: 7.8  },
  DJ: { risk: 2, cases: 421,  change: 6.5  },
  GG: { risk: 2, cases: 3102, change: 5.2  },
  SL: { risk: 2, cases: 4821, change: 4.8  },
  IC: { risk: 1, cases: 892,  change: 2.1  },
  GW: { risk: 1, cases: 312,  change: 1.4  },
  SJ: { risk: 1, cases: 87,   change: 0.9  },
  GB: { risk: 1, cases: 743,  change: 1.8  },
  DG: { risk: 1, cases: 1021, change: 2.3  },
  US: { risk: 1, cases: 398,  change: 1.2  },
  BS: { risk: 1, cases: 1432, change: 2.7  },
  JJ: { risk: 1, cases: 189,  change: 0.6  },
};

export const mockAlerts: AlertRecord[] = [
  {
    id: "ALT-2026-0428-001",
    region: "전북특별자치도",
    regionCode: "JB",
    level: 4,
    time: "2026-04-28 08:42",
    summary: "3계층 동시 초과 — OTC 78, 하수 82, 검색 71",
  },
  {
    id: "ALT-2026-0428-002",
    region: "전라남도",
    regionCode: "JN",
    level: 4,
    time: "2026-04-28 09:05",
    summary: "인접 지역 확산 패턴 — 14일 선행 탐지 신호",
  },
  {
    id: "ALT-2026-0427-003",
    region: "광주광역시",
    regionCode: "GJ",
    level: 3,
    time: "2026-04-27 14:30",
    summary: "OTC + 검색 트렌드 동시 상승 감지",
  },
  {
    id: "ALT-2026-0426-004",
    region: "경상남도",
    regionCode: "GN",
    level: 3,
    time: "2026-04-26 11:15",
    summary: "하수 바이오마커 임계값 (72) 도달",
  },
];
