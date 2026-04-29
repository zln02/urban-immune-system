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
  /** 클릭 시 상세 모달 열기. 지정되면 hover/cursor 활성화. */
  onClick?: () => void;
  /** 상세 모달 열기 버튼의 접근성 라벨 (lang 별) */
  detailLabel?: string;
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

export function LayerCard({
  title,
  sub,
  data,
  value,
  change,
  color,
  icon,
  caveatLabel,
  caveatTooltip,
  onClick,
  detailLabel,
}: LayerCardProps) {
  const isUp = change >= 0;
  const clickable = typeof onClick === "function";

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (!clickable) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <div
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={clickable ? detailLabel ?? `${title} 상세 보기` : undefined}
      onClick={clickable ? onClick : undefined}
      onKeyDown={handleKeyDown}
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${color}`,
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        cursor: clickable ? "pointer" : "default",
        transition: "transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease",
        position: "relative",
      }}
      onMouseEnter={(e) => {
        if (!clickable) return;
        e.currentTarget.style.transform = "translateY(-1px)";
        e.currentTarget.style.boxShadow = "0 4px 14px rgba(15, 23, 42, 0.08)";
      }}
      onMouseLeave={(e) => {
        if (!clickable) return;
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "none";
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
              <span onClick={(e) => e.stopPropagation()}>
                <InfoTooltip title={caveatTooltip.title} body={caveatTooltip.body} size={12} />
              </span>
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
      {clickable && (
        <div
          aria-hidden
          style={{
            position: "absolute",
            right: 10,
            bottom: 8,
            fontSize: 10,
            color: "var(--text-tertiary)",
            display: "flex",
            alignItems: "center",
            gap: 3,
            pointerEvents: "none",
          }}
        >
          {detailLabel ?? "상세 보기"} →
        </div>
      )}
    </div>
  );
}
