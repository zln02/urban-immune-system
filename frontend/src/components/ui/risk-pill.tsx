import { RISK_META, type RiskLevel } from "@/lib/risk";
import type { Lang } from "@/lib/i18n";

interface RiskPillProps {
  level: RiskLevel;
  lang: Lang;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

/**
 * 위험도 뱃지 — 3중 코딩 (색상 + 기호 + L숫자 + 한국어/영어 라벨).
 * WCAG AA 대비 유지를 위해 진한 색상 on 옅은 배경 + 좌측 2px 벽.
 */
export function RiskPill({ level, lang, size = "sm", showLabel = true }: RiskPillProps) {
  const meta = RISK_META[level];
  const fs = size === "sm" ? 11 : size === "md" ? 12 : 13;

  return (
    <span
      className="uis-risk"
      data-level={level}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: size === "sm" ? "2px 6px" : "3px 8px",
        fontSize: fs,
        fontWeight: 600,
        letterSpacing: 0.16,
        background: `var(--risk-${meta.token}-10)`,
        color: `var(--risk-${meta.token})`,
        borderLeft: `2px solid var(--risk-${meta.token})`,
        borderRadius: 2,
      }}
    >
      <span aria-hidden style={{ fontSize: fs + 1, lineHeight: 1 }}>
        {meta.icon}
      </span>
      <span style={{ fontVariantNumeric: "tabular-nums" }}>L{level}</span>
      {showLabel && <span>{meta.label[lang]}</span>}
    </span>
  );
}
