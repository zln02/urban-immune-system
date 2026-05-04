export type RiskLevel = 1 | 2 | 3 | 4;

interface RiskMeta {
  token: "safe" | "caution" | "warning" | "alert";
  icon: string;
  label: { ko: string; en: string };
  hatch: boolean;
}

export const RISK_META: Record<RiskLevel, RiskMeta> = {
  1: { token: "safe",    icon: "✓", label: { ko: "정상", en: "Normal"   }, hatch: false },
  2: { token: "caution", icon: "!",  label: { ko: "주의", en: "Caution"  }, hatch: false },
  3: { token: "warning", icon: "▲",  label: { ko: "경보", en: "Warning"  }, hatch: true  },
  4: { token: "alert",   icon: "⊗",  label: { ko: "위기", en: "Critical" }, hatch: true  },
};
