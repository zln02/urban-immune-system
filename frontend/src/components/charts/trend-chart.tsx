"use client";

import { useMemo, useRef, useState } from "react";
import type { SeriesBundle } from "@/lib/mock-data";
import type { Dict } from "@/lib/i18n";

interface TrendChartProps {
  series: SeriesBundle;
  t: Dict;
  height?: number;
  showForecast?: boolean;
}

/**
 * 3-Layer 교차검증 시계열 + 21일 예측 (95% CI).
 * Train/Test 분할선, 경보 구간 음영, 호버 판독값 포함.
 *
 * Phase 2 후반에 ECharts 5 로 교체 예정 — 지금은 의존성 최소 SVG 수제.
 */
export function TrendChart({ series, t, height = 260, showForecast = true }: TrendChartProps) {
  const W = 860;
  const H = height;
  const padL = 48;
  const padR = 16;
  const padT = 16;
  const padB = 36;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const totalDays = series.days + (showForecast ? 21 : 0);
  const yMax = 140;
  const yMin = 0;
  const xAt = (i: number) => padL + (i / (totalDays - 1)) * plotW;
  const yAt = (v: number) => padT + (1 - (v - yMin) / (yMax - yMin)) * plotH;
  const toPath = (arr: readonly number[]) =>
    arr.map((v, i) => `${i === 0 ? "M" : "L"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)}`).join(" ");

  const [hoverX, setHoverX] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const dayIdxFromX = (clientX: number) => {
    if (!svgRef.current) return null;
    const rect = svgRef.current.getBoundingClientRect();
    const ratio = (clientX - rect.left) / rect.width;
    const i = Math.round(((padL + ratio * W - padL) / plotW) * (totalDays - 1));
    return Math.max(0, Math.min(totalDays - 1, i));
  };

  const alertZoneStart = 45;
  const testStart = series.days - 14;

  const ciPoly = useMemo(() => {
    if (!showForecast) return "";
    const fcst = series.forecast;
    const top = fcst.ci
      .map((pair, i) => `${xAt(series.days + i)} ${yAt(pair[1])}`)
      .join(" L ");
    const bot = fcst.ci
      .slice()
      .reverse()
      .map((pair, i) => `${xAt(series.days + fcst.ci.length - 1 - i)} ${yAt(pair[0])}`)
      .join(" L ");
    return `M ${top} L ${bot} Z`;
  }, [series, showForecast, totalDays]);

  const layers = [
    {
      key: "pharmacy",
      color: "var(--layer-pharmacy)",
      data: series.pharmacy,
      label: t.layer_pharmacy,
    },
    { key: "sewage", color: "var(--layer-sewage)", data: series.sewage, label: t.layer_sewage },
    { key: "search", color: "var(--layer-search)", data: series.search, label: t.layer_search },
  ];

  return (
    <div style={{ width: "100%", position: "relative" }}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", display: "block" }}
        onMouseMove={(e) => setHoverX(dayIdxFromX(e.clientX))}
        onMouseLeave={() => setHoverX(null)}
        role="img"
        aria-label={t.trend_title}
      >
        {/* Gridlines */}
        {[0, 35, 70, 105, 140].map((v) => (
          <g key={v}>
            <line
              x1={padL}
              y1={yAt(v)}
              x2={W - padR}
              y2={yAt(v)}
              stroke="var(--border)"
              strokeWidth="0.5"
              strokeDasharray="2 3"
            />
            <text
              x={padL - 8}
              y={yAt(v) + 3}
              textAnchor="end"
              fontSize="10"
              fill="var(--text-tertiary)"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {v}
            </text>
          </g>
        ))}

        {/* 경보 구간 */}
        <rect
          x={xAt(alertZoneStart)}
          y={padT}
          width={xAt(series.days - 1) - xAt(alertZoneStart)}
          height={plotH}
          fill="var(--risk-alert-10)"
          opacity="0.6"
        />

        {/* Train/Test 분할 */}
        <line
          x1={xAt(testStart)}
          y1={padT}
          x2={xAt(testStart)}
          y2={H - padB}
          stroke="var(--text-tertiary)"
          strokeWidth="0.75"
          strokeDasharray="3 3"
        />
        <text
          x={xAt(testStart) + 4}
          y={padT + 10}
          fontSize="9"
          fill="var(--text-tertiary)"
        >
          {t.trend_test} →
        </text>

        {showForecast && (
          <>
            <line
              x1={xAt(series.days - 1)}
              y1={padT}
              x2={xAt(series.days - 1)}
              y2={H - padB}
              stroke="var(--text)"
              strokeWidth="1"
            />
            <text
              x={xAt(series.days - 1) + 4}
              y={H - padB - 4}
              fontSize="9"
              fontWeight="600"
              fill="var(--text)"
            >
              {t.trend_forecast} →
            </text>
            <path d={ciPoly} fill="var(--layer-search)" opacity="0.12" />
          </>
        )}

        {layers.map((l) => (
          <path
            key={l.key}
            d={toPath(l.data)}
            fill="none"
            stroke={l.color}
            strokeWidth="1.75"
          />
        ))}

        {showForecast &&
          (() => {
            const pts: [number, number][] = [
              [series.days - 1, series.search[series.days - 1]],
              ...series.forecast.mean.map((v, i): [number, number] => [series.days + i, v]),
            ];
            const path = pts
              .map(([x, y], i) => `${i === 0 ? "M" : "L"} ${xAt(x)} ${yAt(y)}`)
              .join(" ");
            return (
              <path
                d={path}
                fill="none"
                stroke="var(--layer-search)"
                strokeWidth="1.75"
                strokeDasharray="4 3"
              />
            );
          })()}

        {[0, 15, 30, 45, 60, 75]
          .filter((i) => i < totalDays)
          .map((i) => {
            const daysFromToday = i - (series.days - 1);
            const label =
              daysFromToday === 0
                ? t.trend_test === "검증"
                  ? "오늘"
                  : "Today"
                : daysFromToday > 0
                ? `+${daysFromToday}${t.trend_test === "검증" ? "일" : "d"}`
                : `${daysFromToday}${t.trend_test === "검증" ? "일" : "d"}`;
            return (
              <text
                key={i}
                x={xAt(i)}
                y={H - padB + 16}
                textAnchor="middle"
                fontSize="9"
                fill="var(--text-tertiary)"
              >
                {label}
              </text>
            );
          })}

        {hoverX !== null &&
          (() => {
            const isForecast = hoverX >= series.days;
            return (
              <g>
                <line
                  x1={xAt(hoverX)}
                  y1={padT}
                  x2={xAt(hoverX)}
                  y2={H - padB}
                  stroke="var(--text)"
                  strokeWidth="0.75"
                  opacity="0.5"
                />
                {layers.map((l) => {
                  const v = isForecast ? null : l.data[hoverX];
                  if (v == null) return null;
                  return (
                    <circle
                      key={l.key}
                      cx={xAt(hoverX)}
                      cy={yAt(v)}
                      r="3"
                      fill={l.color}
                      stroke="var(--bg)"
                      strokeWidth="1.5"
                    />
                  );
                })}
              </g>
            );
          })()}
      </svg>

      <div style={{ display: "flex", gap: 16, fontSize: 12, marginTop: 8, flexWrap: "wrap" }}>
        {layers.map((l) => (
          <div key={l.key} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span
              style={{ width: 14, height: 2, background: l.color, display: "inline-block" }}
            />
            <span style={{ fontWeight: 500 }}>{l.label}</span>
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              width: 14,
              height: 2,
              background:
                "linear-gradient(90deg,var(--layer-search) 60%, transparent 60%)",
              backgroundSize: "6px 2px",
              display: "inline-block",
            }}
          />
          <span style={{ color: "var(--text-secondary)" }}>
            {t.trend_forecast} · {t.ci95}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 14, height: 10, background: "var(--risk-alert-10)" }} />
          <span style={{ color: "var(--text-secondary)" }}>
            {t.trend_test === "검증" ? "경보 구간" : "Alert window"}
          </span>
        </div>
      </div>
    </div>
  );
}
