import type { ReactNode } from "react";
import { Spark } from "@/components/charts/spark";

interface LayerCardProps {
  title: string;
  sub: string;
  data: readonly number[];
  value: number;
  change: number;
  color: string;
  icon: ReactNode;
}

/**
 * 3-Layer 단일 신호 카드 — 아이콘·제목·부제·최신값·Δ%·스파크라인.
 */
export function LayerCard({ title, sub, data, value, change, color, icon }: LayerCardProps) {
  return (
    <div
      className="uis-card"
      style={{
        padding: "var(--sp-4)",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        position: "relative",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, color }}>
            {icon}
            <span
              className="t-label-02"
              style={{ textTransform: "uppercase", letterSpacing: 0.32 }}
            >
              {title}
            </span>
          </div>
          <div
            className="t-label-01"
            style={{ color: "var(--text-tertiary)", marginTop: 2 }}
          >
            {sub}
          </div>
        </div>
        <span style={{ width: 4, height: 16, background: color }} />
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span className="t-num-md" style={{ color }}>
          {value.toFixed(1)}
        </span>
        <span
          className="t-label-02"
          style={{
            color: change > 0 ? "var(--risk-warning)" : "var(--risk-safe)",
          }}
        >
          {change > 0 ? "▲" : "▼"} {change > 0 ? "+" : ""}
          {change.toFixed(1)}%
        </span>
      </div>
      <Spark data={data} color={color} width={240} height={36} />
    </div>
  );
}
