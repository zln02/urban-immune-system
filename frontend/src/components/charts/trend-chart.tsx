"use client";

import { useState } from "react";
import type { Translations } from "@/lib/i18n";

/**
 * Time-aligned 3-layer trend chart.
 * - 모든 시리즈는 동일 길이의 (number | null)[] 로 들어와야 한다.
 * - dates 길이도 같아야 한다. → 같은 X 픽셀 = 같은 날짜 보장.
 * - null 인 점은 path 가 끊어지고 호버 툴팁에서 "—" 로 표시.
 */
interface TrendChartProps {
  series: {
    pharmacy: (number | null)[];
    sewage: (number | null)[];
    search: (number | null)[];
  };
  dates: string[];
  t: Translations;
  height?: number;
}

const COLORS = {
  pharmacy: "var(--layer-pharmacy)",
  sewage: "var(--layer-sewage)",
  search: "var(--layer-search)",
} as const;

type SeriesKey = keyof typeof COLORS;

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

/** null 있는 시리즈를 path 로 변환 — null 자리는 path 끊고 다음 valid 점에서 M 로 재시작 */
function pathFromValues(
  values: (number | null)[],
  w: number,
  h: number,
  padX: number,
  padY: number
): string {
  if (values.length < 2) return "";
  const innerW = w - padX * 2;
  const innerH = h - padY * 2;
  const xAt = (i: number) =>
    values.length === 1 ? padX : padX + (i / (values.length - 1)) * innerW;
  const yAt = (v: number) => padY + (1 - v / 100) * innerH;

  let d = "";
  let drawing = false;
  values.forEach((v, i) => {
    if (v === null || !Number.isFinite(v)) {
      drawing = false;
      return;
    }
    const x = xAt(i);
    const y = yAt(v);
    d += `${drawing ? "L" : "M"} ${x} ${y} `;
    drawing = true;
  });
  return d;
}

/** null 데이터 점을 원형 마커로 표시할지 여부: 인접한 양쪽이 null 이면 단독 점이라 line 으로 안 보임 → 그릴 가치 */
function singletonPoints(values: (number | null)[]): number[] {
  const idxs: number[] = [];
  values.forEach((v, i) => {
    if (v === null || !Number.isFinite(v)) return;
    const prev = i > 0 ? values[i - 1] : null;
    const next = i < values.length - 1 ? values[i + 1] : null;
    if ((prev === null || !Number.isFinite(prev)) && (next === null || !Number.isFinite(next))) {
      idxs.push(i);
    }
  });
  return idxs;
}

export function TrendChart({ series, dates, t, height = 200 }: TrendChartProps) {
  const w = 800;
  const h = height;
  const padX = 30;
  const padY = 20;
  const innerW = w - padX * 2;
  const innerH = h - padY * 2;

  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const n = dates.length;
  const xAt = (i: number) => (n <= 1 ? padX : padX + (i / (n - 1)) * innerW);
  const yAt = (v: number) => padY + (1 - v / 100) * innerH;

  // X축 라벨: 5개 (start/25%/50%/75%/end). n 작으면 적게.
  const tickCount = Math.min(5, n);
  const tickIdxs =
    tickCount <= 1
      ? [0]
      : Array.from({ length: tickCount }, (_, k) => Math.round((k / (tickCount - 1)) * (n - 1)));

  // 데이터 가용성 카운트 (각 레이어가 실제로 몇 주에 데이터를 가졌나)
  const validCounts = (Object.keys(series) as SeriesKey[]).reduce(
    (acc, k) => ({ ...acc, [k]: series[k].filter((v) => v !== null && Number.isFinite(v)).length }),
    {} as Record<SeriesKey, number>
  );

  const handleMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (n === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * w;
    if (px < padX || px > w - padX) {
      setHoverIdx(null);
      return;
    }
    const ratio = (px - padX) / innerW;
    const idx = Math.round(ratio * (n - 1));
    setHoverIdx(Math.max(0, Math.min(n - 1, idx)));
  };

  return (
    <div>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        style={{ width: "100%", height, display: "block" }}
        aria-label="신호 시계열 차트"
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        {/* Y 그리드 */}
        {[25, 50, 75].map((pct) => {
          const y = yAt(pct);
          return (
            <g key={pct}>
              <line x1={padX} y1={y} x2={w - padX} y2={y} stroke="var(--border)" strokeWidth={0.5} />
              <text
                x={padX - 4}
                y={y + 3}
                fontSize={9}
                fill="var(--text-tertiary)"
                textAnchor="end"
                fontFamily="var(--font-mono)"
              >
                {pct}
              </text>
            </g>
          );
        })}

        {/* X축 날짜 라벨 */}
        {tickIdxs.map((i, k) => {
          const x = xAt(i);
          const anchor: "start" | "middle" | "end" =
            k === 0 ? "start" : k === tickIdxs.length - 1 ? "end" : "middle";
          return (
            <g key={k}>
              <line
                x1={x}
                y1={padY}
                x2={x}
                y2={h - padY}
                stroke="var(--border)"
                strokeWidth={0.4}
                strokeDasharray="2 4"
              />
              <text
                x={x}
                y={h - 4}
                fontSize={9}
                fill="var(--text-tertiary)"
                textAnchor={anchor}
                fontFamily="var(--font-mono)"
              >
                {fmtDate(dates[i])}
              </text>
            </g>
          );
        })}

        {/* 각 시리즈: line + singleton marker */}
        {(Object.keys(series) as SeriesKey[]).map((key) => (
          <g key={key}>
            <path
              d={pathFromValues(series[key], w, h, padX, padY)}
              fill="none"
              stroke={COLORS[key]}
              strokeWidth={1.8}
              strokeLinejoin="round"
            />
            {singletonPoints(series[key]).map((i) => {
              const v = series[key][i];
              if (v === null) return null;
              return <circle key={i} cx={xAt(i)} cy={yAt(v)} r={2.4} fill={COLORS[key]} />;
            })}
          </g>
        ))}

        {/* 호버 크로스헤어 + 점 */}
        {hoverIdx !== null && (
          <g pointerEvents="none">
            <line
              x1={xAt(hoverIdx)}
              x2={xAt(hoverIdx)}
              y1={padY}
              y2={h - padY}
              stroke="var(--text-secondary)"
              strokeOpacity={0.4}
              strokeWidth={1}
              strokeDasharray="3 3"
            />
            {(Object.keys(series) as SeriesKey[]).map((key) => {
              const v = series[key][hoverIdx];
              if (v === null || !Number.isFinite(v)) return null;
              return (
                <circle
                  key={key}
                  cx={xAt(hoverIdx)}
                  cy={yAt(v)}
                  r={3.6}
                  fill={COLORS[key]}
                  stroke="#fff"
                  strokeWidth={1.2}
                />
              );
            })}
          </g>
        )}
      </svg>

      {/* 호버 툴팁 (그래프 아래) */}
      {hoverIdx !== null && (
        <div
          style={{
            marginTop: -8,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "5px 10px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            fontSize: 11,
            boxShadow: "0 1px 3px rgba(15, 23, 42, 0.06)",
            flexWrap: "wrap",
            gap: 8,
          }}
        >
          <span style={{ fontWeight: 700, color: "var(--text)", fontFamily: "var(--font-mono)" }}>
            {fmtDate(dates[hoverIdx])} (W{getISOWeek(dates[hoverIdx])})
          </span>
          <span style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {(Object.keys(series) as SeriesKey[]).map((key) => {
              const v = series[key][hoverIdx];
              const missing = v === null || !Number.isFinite(v);
              return (
                <span key={key} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 10, height: 2, background: COLORS[key], display: "inline-block" }} />
                  <span style={{ color: "var(--text-secondary)" }}>
                    {key === "pharmacy" ? t.layer_pharmacy : key === "sewage" ? t.layer_sewage : t.layer_search}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontWeight: 700,
                      color: missing ? "var(--text-tertiary)" : COLORS[key],
                    }}
                  >
                    {missing ? "— (no data)" : (v as number).toFixed(1)}
                  </span>
                </span>
              );
            })}
          </span>
        </div>
      )}

      {/* 범례 + 데이터 가용성 메타 */}
      <div
        style={{
          display: "flex",
          gap: 16,
          marginTop: 8,
          fontSize: 11,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        {(Object.keys(series) as SeriesKey[]).map((key) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ width: 20, height: 2, background: COLORS[key], display: "inline-block" }} />
            <span style={{ color: "var(--text-secondary)" }}>
              {key === "pharmacy" ? t.layer_pharmacy : key === "sewage" ? t.layer_sewage : t.layer_search}
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                color: "var(--text-tertiary)",
                marginLeft: 2,
              }}
              title="실제 데이터가 존재하는 주 / 전체 주"
            >
              ({validCounts[key]}/{n})
            </span>
          </div>
        ))}
        {n > 0 && (
          <span
            style={{
              marginLeft: "auto",
              fontSize: 10,
              color: "var(--text-tertiary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {fmtDate(dates[0])} ~ {fmtDate(dates[n - 1])} · ISO 주간 정렬
          </span>
        )}
      </div>
    </div>
  );
}

/** ISO 8601 주차 번호 — 호버 툴팁에 노출 */
function getISOWeek(iso: string): number {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 0;
  const tmp = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  tmp.setUTCDate(tmp.getUTCDate() + 4 - (tmp.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
  return Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}
