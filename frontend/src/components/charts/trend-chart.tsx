import type { SeriesData } from "@/lib/mock-data";
import type { Translations } from "@/lib/i18n";

interface TrendChartProps {
  series: SeriesData;
  t: Translations;
  height?: number;
}

const W = 800;
const PT = 20;
const PB = 28;
const PL = 32;
const PR = 20;

function getPoints(values: number[], w: number, h: number) {
  if (values.length === 0) return [];
  const n = values.length;
  const iw = w - PL - PR;
  const ih = h - PT - PB;
  return values.map((v, i) => ({
    x: PL + (n === 1 ? iw / 2 : (i / (n - 1)) * iw),
    y: PT + (1 - Math.min(100, Math.max(0, v)) / 100) * ih,
  }));
}

function toLinePath(pts: { x: number; y: number }[]): string {
  if (pts.length < 2) return "";
  let d = `M ${pts[0].x},${pts[0].y}`;
  for (let i = 1; i < pts.length; i++) {
    const cpx = (pts[i].x - pts[i - 1].x) * 0.4;
    d += ` C ${pts[i - 1].x + cpx},${pts[i - 1].y} ${pts[i].x - cpx},${pts[i].y} ${pts[i].x},${pts[i].y}`;
  }
  return d;
}

function toAreaPath(pts: { x: number; y: number }[], h: number): string {
  const line = toLinePath(pts);
  if (!line || pts.length === 0) return "";
  const bottom = h - PB;
  return `${line} L ${pts[pts.length - 1].x},${bottom} L ${pts[0].x},${bottom} Z`;
}

const LINE_KEYS = ["pharmacy", "sewage", "search"] as const;

const COLORS: Record<string, string> = {
  pharmacy: "var(--layer-pharmacy)",
  sewage: "var(--layer-sewage)",
  search: "var(--layer-search)",
};

export function TrendChart({ series, t, height = 200 }: TrendChartProps) {
  const h = height;

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${h}`}
        style={{ width: "100%", height, display: "block" }}
        aria-label="신호 시계열 차트"
      >
        <style>{`
          @keyframes uis-draw {
            from { stroke-dashoffset: 3000; }
            to   { stroke-dashoffset: 0; }
          }
          @keyframes uis-fadein {
            from { opacity: 0; }
            to   { opacity: 1; }
          }
          @keyframes uis-pulse {
            0%, 100% { r: 4; opacity: 1; }
            50%       { r: 6.5; opacity: 0.55; }
          }
          .uis-line-0 {
            stroke-dasharray: 3000; stroke-dashoffset: 3000;
            animation: uis-draw 1.4s cubic-bezier(.4,0,.2,1) forwards;
          }
          .uis-line-1 {
            stroke-dasharray: 3000; stroke-dashoffset: 3000;
            animation: uis-draw 1.4s cubic-bezier(.4,0,.2,1) 0.25s forwards;
          }
          .uis-line-2 {
            stroke-dasharray: 3000; stroke-dashoffset: 3000;
            animation: uis-draw 1.4s cubic-bezier(.4,0,.2,1) 0.5s forwards;
          }
          .uis-area-0 { opacity: 0; animation: uis-fadein 1s ease 0.5s forwards; }
          .uis-area-1 { opacity: 0; animation: uis-fadein 1s ease 0.7s forwards; }
          .uis-area-2 { opacity: 0; animation: uis-fadein 1s ease 0.9s forwards; }
          .uis-dot    { animation: uis-pulse 2.4s ease-in-out infinite; }
        `}</style>

        <defs>
          {LINE_KEYS.map((key) => (
            <linearGradient key={key} id={`uis-grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLORS[key]} stopOpacity="0.35" />
              <stop offset="100%" stopColor={COLORS[key]} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>

        {/* Grid */}
        {[25, 50, 75].map((pct) => {
          const y = PT + (1 - pct / 100) * (h - PT - PB);
          return (
            <g key={pct}>
              <line
                x1={PL} y1={y} x2={W - PR} y2={y}
                stroke="var(--border)" strokeWidth={0.5} strokeDasharray="4 4"
              />
              <text x={PL - 6} y={y + 4} fontSize={9} fill="var(--text-tertiary)" textAnchor="end">
                {pct}
              </text>
            </g>
          );
        })}

        {/* Baseline */}
        <line x1={PL} y1={h - PB} x2={W - PR} y2={h - PB} stroke="var(--border)" strokeWidth={0.5} />
        <text x={PL} y={h - PB + 14} fontSize={9} fill="var(--text-tertiary)" textAnchor="start">이전</text>
        <text x={W - PR} y={h - PB + 14} fontSize={9} fill="var(--text-tertiary)" textAnchor="end">현재</text>

        {/* Area fills */}
        {LINE_KEYS.map((key, idx) => (
          <path
            key={key}
            className={`uis-area-${idx}`}
            d={toAreaPath(getPoints(series[key], W, h), h)}
            fill={`url(#uis-grad-${key})`}
          />
        ))}

        {/* Lines */}
        {LINE_KEYS.map((key, idx) => (
          <path
            key={key}
            className={`uis-line-${idx}`}
            d={toLinePath(getPoints(series[key], W, h))}
            fill="none"
            stroke={COLORS[key]}
            strokeWidth={2.2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {/* Pulsing dot at latest value */}
        {LINE_KEYS.map((key) => {
          const pts = getPoints(series[key], W, h);
          const last = pts[pts.length - 1];
          if (!last) return null;
          return (
            <circle
              key={key}
              className="uis-dot"
              cx={last.x}
              cy={last.y}
              r={4}
              fill={COLORS[key]}
            />
          );
        })}
      </svg>

      {/* Legend */}
      <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 11 }}>
        {LINE_KEYS.map((key) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ width: 20, height: 2.5, background: COLORS[key], display: "inline-block", borderRadius: 2 }} />
            <span style={{ color: "var(--text-secondary)" }}>
              {key === "pharmacy" ? t.layer_pharmacy : key === "sewage" ? t.layer_sewage : t.layer_search}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
