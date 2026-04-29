import type { ReactNode } from "react";

type Tone = "safe" | "caution" | "warning" | "alert";

interface KpiCardProps {
  label: string;
  value: string | number;
  total?: number;
  unit?: string;
  delta?: string;
  tone?: Tone;
  sparkData?: number[];
  sparkColor?: string;
  /** 라벨 옆에 ⓘ 도움말 아이콘 등 우측 슬롯 */
  labelSuffix?: ReactNode;
  /** true 이면 값·spark 영역을 스켈레톤으로 대체 */
  isLoading?: boolean;
  /** true 이면 우상단에 DEMO 뱃지 표시 */
  isDemo?: boolean;
}

const TONE_COLOR: Record<Tone, string> = {
  safe:    "var(--risk-safe)",
  caution: "var(--risk-caution)",
  warning: "var(--risk-warning)",
  alert:   "var(--risk-alert)",
};

function Spark({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const w = 60;
  const h = 22;
  const pad = 2;
  const xs = data.map((_, i) => pad + (i / (data.length - 1)) * (w - pad * 2));
  const max = Math.max(...data, 1);
  const ys = data.map((v) => pad + (1 - v / max) * (h - pad * 2));
  const d = `M ${xs[0]} ${ys[0]} ` + xs.slice(1).map((x, i) => `L ${x} ${ys[i + 1]}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden>
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

export function KpiCard({ label, value, total, unit, delta, tone = "safe", sparkData, sparkColor, labelSuffix, isLoading = false, isDemo = false }: KpiCardProps) {
  const color = TONE_COLOR[tone];
  return (
    <div
      role="group"
      aria-label={`${label}: ${value}${unit ?? ""}`}
      style={{
        position: "relative",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderTop: `3px solid ${color}`,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      {isDemo && (
        <span
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.08em",
            padding: "2px 6px",
            background: "var(--risk-caution)",
            color: "#fff",
            borderRadius: 3,
          }}
          aria-label="시뮬레이션 데이터"
        >
          DEMO
        </span>
      )}
      <div className="t-label-01" style={{ color: "var(--text-tertiary)", display: "flex", alignItems: "center" }}>
        <span>{label}</span>
        {labelSuffix}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        {isLoading ? (
          <div
            className="animate-pulse"
            style={{ width: "60%", height: 28, background: "var(--border)", borderRadius: 4 }}
            aria-label="로딩 중"
          />
        ) : (
          <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
            <span
              style={{
                fontSize: 28,
                fontWeight: 700,
                lineHeight: 1,
                color,
                fontFamily: "var(--font-mono)",
              }}
            >
              {value}
            </span>
            {total !== undefined && (
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                /{total}
              </span>
            )}
            {unit && (
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{unit}</span>
            )}
          </div>
        )}
        {isLoading ? (
          <div
            className="animate-pulse"
            style={{ width: 60, height: 22, background: "var(--border)", borderRadius: 4 }}
            aria-label="로딩 중"
          />
        ) : (
          sparkData && sparkColor && <Spark data={sparkData} color={sparkColor} />
        )}
      </div>
      {delta && (
        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{delta}</div>
      )}
    </div>
  );
}
