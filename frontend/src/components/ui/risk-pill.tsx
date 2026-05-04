import { RISK_META, type RiskLevel } from "@/lib/risk";
import type { Lang } from "@/lib/i18n";

interface RiskPillProps {
  level: RiskLevel;
  lang: Lang;
}

export function RiskPill({ level, lang }: RiskPillProps) {
  const meta = RISK_META[level];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 0.3,
        background: `var(--risk-${meta.token})`,
        color: "#fff",
      }}
    >
      L{level} {meta.label[lang].toUpperCase()}
    </span>
  );
}
