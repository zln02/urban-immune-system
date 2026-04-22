/**
 * 위험도 4단계 메타 — 3중 코딩 (색·아이콘·라벨) 강제.
 */

export type RiskLevel = 1 | 2 | 3 | 4;
export type RiskToken = "safe" | "caution" | "warning" | "alert";

export interface RiskMeta {
  token: RiskToken;
  icon: string;      // 표식 (색맹 구분 보조)
  symbol: string;    // 보조 기호
  hatch: boolean;    // L3+ 패턴 사용
  label: { ko: string; en: string };
}

export const RISK_META: Record<RiskLevel, RiskMeta> = {
  1: { token: "safe",    icon: "●", symbol: "✓", hatch: false, label: { ko: "안전", en: "Safe" } },
  2: { token: "caution", icon: "◆", symbol: "!", hatch: false, label: { ko: "주의", en: "Caution" } },
  3: { token: "warning", icon: "▲", symbol: "⚠", hatch: true,  label: { ko: "경계", en: "Warning" } },
  4: { token: "alert",   icon: "■", symbol: "✕", hatch: true,  label: { ko: "경보", en: "Alert" } },
};

export function riskColor(level: RiskLevel): string {
  return `var(--risk-${RISK_META[level].token})`;
}

export function riskLabel(level: RiskLevel, lang: "ko" | "en"): string {
  return RISK_META[level].label[lang];
}
