import type { ReactNode } from "react";
import { InfoTooltip } from "@/components/ui/info-tooltip";

interface LayerCardProps {
  title: string;
  sub: string;
  data: number[];
  value: number;
  change: number;
  color: string;
  icon: ReactNode;
  /** "전국 단일값" 같은 제약 표기. 회색 chip 으로 렌더 + tooltip */
  caveatLabel?: string;
  caveatTooltip?: { title: string; body: string };
}

function Spark({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const w = 120;
  const h = 32;
  const pad = 2;
  const xs = data.map((_, i) => pad + (i / (data.length - 1)) * (w - pad * 2));
  const max = Math.max(...data, 1);
  const ys = data.map((v) => pad + (1 - v / max) * (h - pad * 2));
  const d = `M ${xs[0]} ${ys[0]} ` + xs.slice(1).map((x, i) => `L ${x} ${ys[i + 1]}`).join(" ");
  const fillD =
    d +
    ` L ${xs[xs.length - 1]} ${h - pad} L ${xs[0]} ${h - pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden style={{ flexShrink: 0 }}>
      <path d={fillD} fill={color} fillOpacity={0.12} />
      <path d={d} fill="none" stroke={color} strokeWidth={1.8} strokeLinejoin="round" />
    </svg>
  );
}

export function LayerCard({ title, sub, data, value, change, color, icon, caveatLabel, caveatTooltip }: LayerCardProps) {
  const isUp = change >= 0;
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${color}`,
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ color }}>{icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
            <span>{title}</span>
            {caveatLabel && (
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 600,
                  padding: "1px 6px",
                  background: "var(--bg-sub)",
                  color: "var(--text-tertiary)",
                  border: "1px solid var(--border)",
                  letterSpacing: 0.2,
                  whiteSpace: "nowrap",
                }}
              >
                {caveatLabel}
              </span>
            )}
            {caveatTooltip && (
              <InfoTooltip title={caveatTooltip.title} body={caveatTooltip.body} size={12} />
            )}
          </div>
          <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{sub}</div>
        </div>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: isUp ? "var(--risk-warning)" : "var(--risk-safe)",
          }}
        >
          {isUp ? "▲" : "▼"} {Math.abs(change).toFixed(1)}%
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <span
          style={{
            fontSize: 26,
            fontWeight: 700,
            color,
            fontFamily: "var(--font-mono)",
            lineHeight: 1,
          }}
        >
          {value.toFixed(1)}
        </span>
        <Spark data={data} color={color} />
      </div>
    </div>
  );
}
