"use client";

import { useMemo, useState } from "react";
import type { SeriesData } from "@/lib/mock-data";
import type { Translations } from "@/lib/i18n";

interface TrendChartProps {
  series: SeriesData;
  t: Translations;
  height?: number;
  /** 시리즈 길이와 동일한 길이의 날짜 라벨 배열 (선택). X축·호버 표시에 사용 */
  dates?: string[];
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

function toPath(values: number[], w: number, h: number, padX: number, padY: number): string {
  if (values.length < 2) return "";
  const xs = values.map((_, i) => padX + (i / (values.length - 1)) * (w - padX * 2));
  const ys = values.map((v) => padY + (1 - v / 100) * (h - padY * 2));
  return `M ${xs[0]} ${ys[0]} ` + xs.slice(1).map((x, i) => `L ${x} ${ys[i + 1]}`).join(" ");
}

export function TrendChart({ series, t, height = 200, dates }: TrendChartProps) {
  const w = 800;
  const h = height;
  const padX = 26;
  const padY = 18;

  const [hover, setHover] = useState<{ idx: number; px: number } | null>(null);

  // 가장 긴 시리즈를 X축 길이의 기준으로 사용
  const maxLen = Math.max(series.pharmacy.length, series.sewage.length, series.search.length);

  // 날짜 라벨 5개 (start, 25%, 50%, 75%, end) — dates 가 있으면 거기서 sampling
  const dateTicks = useMemo(() => {
    if (!dates || dates.length === 0) return null;
    const n = dates.length;
    const idxs = [0, Math.floor(n * 0.25), Math.floor(n * 0.5), Math.floor(n * 0.75), n - 1];
    return idxs.map((i) => ({ idx: Math.min(i, n - 1), label: fmtDate(dates[Math.min(i, n - 1)]) }));
  }, [dates]);

  const xFromIdx = (i: number, n: number) =>
    n <= 1 ? padX : padX + (i / (n - 1)) * (w - padX * 2);

  const handleMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!dates || dates.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * w;
    if (px < padX || px > w - padX) {
      setHover(null);
      return;
    }
    const ratio = (px - padX) / (w - padX * 2);
    const idx = Math.round(ratio * (dates.length - 1));
    setHover({ idx: Math.max(0, Math.min(dates.length - 1, idx)), px });
  };

  const sampleAt = (key: SeriesKey, idx: number): number | null => {
    const arr = series[key];
    if (arr.length === 0) return null;
    // dates 길이와 시리즈 길이 다를 수 있음 — 비례 매핑
    if (!dates) return arr[Math.min(idx, arr.length - 1)];
    const t = dates.length <= 1 ? 0 : idx / (dates.length - 1);
    const ai = Math.round(t * (arr.length - 1));
    return arr[Math.max(0, Math.min(arr.length - 1, ai))];
  };

  return (
    <div>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        style={{ width: "100%", height, display: "block" }}
        aria-label="신호 시계열 차트"
        onMouseMove={handleMove}
        onMouseLeave={() => setHover(null)}
      >
        {/* Y 그리드 */}
        {[25, 50, 75].map((pct) => {
          const y = padY + (1 - pct / 100) * (h - padY * 2);
          return (
            <g key={pct}>
              <line x1={padX} y1={y} x2={w - padX} y2={y} stroke="var(--border)" strokeWidth={0.5} />
              <text x={padX - 4} y={y + 3} fontSize={9} fill="var(--text-tertiary)" textAnchor="end" fontFamily="var(--font-mono)">
                {pct}
              </text>
            </g>
          );
        })}

        {/* X축 날짜 라벨 */}
        {dateTicks &&
          dateTicks.map((tick, k) => {
            const x = xFromIdx(tick.idx, dateTicks[dateTicks.length - 1].idx + 1);
            const anchor: "start" | "middle" | "end" =
              k === 0 ? "start" : k === dateTicks.length - 1 ? "end" : "middle";
            return (
              <g key={k}>
                <line x1={x} y1={padY} x2={x} y2={h - padY} stroke="var(--border)" strokeWidth={0.4} strokeDasharray="2 4" />
                <text
                  x={x}
                  y={h - 4}
                  fontSize={9}
                  fill="var(--text-tertiary)"
                  textAnchor={anchor}
                  fontFamily="var(--font-mono)"
                >
                  {tick.label}
                </text>
              </g>
            );
          })}

        {/* 라인 */}
        {(["pharmacy", "sewage", "search"] as SeriesKey[]).map((key) => (
          <path
            key={key}
            d={toPath(series[key], w, h, padX, padY)}
            fill="none"
            stroke={COLORS[key]}
            strokeWidth={1.8}
            strokeLinejoin="round"
          />
        ))}

        {/* 호버 크로스헤어 + 점 */}
        {hover && dates && (
          <g pointerEvents="none">
            <line
              x1={hover.px}
              x2={hover.px}
              y1={padY}
              y2={h - padY}
              stroke="var(--text-secondary)"
              strokeOpacity={0.4}
              strokeWidth={1}
              strokeDasharray="3 3"
            />
            {(["pharmacy", "sewage", "search"] as SeriesKey[]).map((key) => {
              const v = sampleAt(key, hover.idx);
              if (v === null) return null;
              const cy = padY + (1 - v / 100) * (h - padY * 2);
              return (
                <circle key={key} cx={hover.px} cy={cy} r={3.5} fill={COLORS[key]} stroke="#fff" strokeWidth={1.2} />
              );
            })}
          </g>
        )}
      </svg>

      {/* 호버 툴팁 */}
      {hover && dates && (
        <div
          style={{
            marginTop: -8,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "4px 10px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            fontSize: 11,
            boxShadow: "0 1px 3px rgba(15, 23, 42, 0.06)",
          }}
        >
          <span style={{ fontWeight: 700, color: "var(--text)", fontFamily: "var(--font-mono)" }}>
            {fmtDate(dates[hover.idx])}
          </span>
          <span style={{ display: "flex", gap: 12 }}>
            {(["pharmacy", "sewage", "search"] as SeriesKey[]).map((key) => {
              const v = sampleAt(key, hover.idx);
              return (
                <span key={key} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 10, height: 2, background: COLORS[key], display: "inline-block" }} />
                  <span style={{ color: "var(--text-secondary)" }}>
                    {key === "pharmacy" ? t.layer_pharmacy : key === "sewage" ? t.layer_sewage : t.layer_search}
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: COLORS[key] }}>
                    {v === null ? "—" : v.toFixed(1)}
                  </span>
                </span>
              );
            })}
          </span>
        </div>
      )}

      {/* 범례 + 기간 */}
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
        {(["pharmacy", "sewage", "search"] as SeriesKey[]).map((key) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ width: 20, height: 2, background: COLORS[key], display: "inline-block" }} />
            <span style={{ color: "var(--text-secondary)" }}>
              {key === "pharmacy" ? t.layer_pharmacy : key === "sewage" ? t.layer_sewage : t.layer_search}
            </span>
          </div>
        ))}
        {dates && dates.length > 0 && (
          <span
            style={{
              marginLeft: "auto",
              fontSize: 10,
              color: "var(--text-tertiary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {fmtDate(dates[0])} ~ {fmtDate(dates[dates.length - 1])} · n={maxLen}
          </span>
        )}
      </div>
    </div>
  );
}
