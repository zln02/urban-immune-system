import type { SeriesData } from "@/lib/mock-data";
import type { Translations } from "@/lib/i18n";

interface TrendChartProps {
  series: SeriesData;
  t: Translations;
  height?: number;
}

function toPath(values: number[], w: number, h: number, pad = 16): string {
  if (values.length < 2) return "";
  const xs = values.map((_, i) => pad + (i / (values.length - 1)) * (w - pad * 2));
  const ys = values.map((v) => pad + (1 - v / 100) * (h - pad * 2));
  return `M ${xs[0]} ${ys[0]} ` + xs.slice(1).map((x, i) => `L ${x} ${ys[i + 1]}`).join(" ");
}

const COLORS = {
  pharmacy: "var(--layer-pharmacy)",
  sewage:   "var(--layer-sewage)",
  search:   "var(--layer-search)",
};

export function TrendChart({ series, t, height = 200 }: TrendChartProps) {
  const w = 800;
  const h = height;

  return (
    <div>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        style={{ width: "100%", height, display: "block" }}
        aria-label="신호 시계열 차트"
      >
        {/* Grid lines */}
        {[25, 50, 75].map((pct) => {
          const y = 16 + (1 - pct / 100) * (h - 32);
          return (
            <g key={pct}>
              <line x1={16} y1={y} x2={w - 16} y2={y} stroke="var(--border)" strokeWidth={0.5} />
              <text x={12} y={y + 4} fontSize={8} fill="var(--text-tertiary)" textAnchor="end">
                {pct}
              </text>
            </g>
          );
        })}
        {/* Lines */}
        {(["pharmacy", "sewage", "search"] as const).map((key) => (
          <path
            key={key}
            d={toPath(series[key], w, h)}
            fill="none"
            stroke={COLORS[key]}
            strokeWidth={1.8}
            strokeLinejoin="round"
          />
        ))}
      </svg>
      {/* Legend */}
      <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 11 }}>
        {(["pharmacy", "sewage", "search"] as const).map((key) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ width: 20, height: 2, background: COLORS[key], display: "inline-block" }} />
            <span style={{ color: "var(--text-secondary)" }}>
              {key === "pharmacy" ? t.layer_pharmacy : key === "sewage" ? t.layer_sewage : t.layer_search}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
