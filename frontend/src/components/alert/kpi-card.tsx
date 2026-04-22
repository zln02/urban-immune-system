import { Spark } from "@/components/charts/spark";
import type { RiskToken } from "@/lib/risk";

interface KpiCardProps {
  label: string;
  value: string | number;
  unit?: string;
  delta?: string;
  total?: string | number;
  tone?: RiskToken;
  sparkData?: readonly number[];
  sparkColor?: string;
}

/**
 * KPI 스코어 카드 — 상단 3px tone 바, tabular-nums 대형 숫자, 델타/총량/스파크라인.
 */
export function KpiCard({
  label,
  value,
  unit,
  delta,
  total,
  tone = "safe",
  sparkData,
  sparkColor,
}: KpiCardProps) {
  const toneColor = `var(--risk-${tone})`;
  return (
    <div
      className="uis-card"
      style={{
        padding: "18px 20px",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderTop: `3px solid ${toneColor}`,
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minHeight: 120,
      }}
    >
      <div
        className="t-label-02"
        style={{
          color: "var(--text-secondary)",
          textTransform: "uppercase",
          letterSpacing: 0.32,
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span className="t-num-lg" style={{ color: "var(--text)" }}>
          {value}
        </span>
        {unit && (
          <span style={{ fontSize: 14, color: "var(--text-tertiary)" }}>{unit}</span>
        )}
        {total !== undefined && (
          <span style={{ fontSize: 14, color: "var(--text-tertiary)" }}>{delta}</span>
        )}
      </div>
      {total === undefined && delta && (
        <div className="t-label-02" style={{ color: toneColor, fontWeight: 500 }}>
          {delta}
        </div>
      )}
      {sparkData && (
        <div style={{ marginTop: 2 }}>
          <Spark data={sparkData} color={sparkColor ?? toneColor} width={180} height={24} />
        </div>
      )}
    </div>
  );
}
