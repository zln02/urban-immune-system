import type { AlertRecord } from "@/lib/mock-data";
import type { Translations, Lang } from "@/lib/i18n";
import { RISK_META, type RiskLevel } from "@/lib/risk";

interface AlertBannerProps {
  alerts: AlertRecord[];
  t: Translations;
  lang: Lang;
  confidence?: number;
}

export function AlertBanner({ alerts, t: _t, lang, confidence = 0.87 }: AlertBannerProps) {
  // ORANGE+(level≥3) 부터 표시 — 보건당국 사전 대응 시간 확보 목적
  const critical = alerts.filter((a) => a.level >= 3);
  if (critical.length === 0) return null;

  // RED 우선, 없으면 ORANGE 최상위
  critical.sort((a, b) => b.level - a.level);
  const top = critical[0];
  const meta = RISK_META[top.level as RiskLevel];
  const isRed = top.level >= 4;
  const redCount = critical.filter((a) => a.level >= 4).length;
  const orangeCount = critical.filter((a) => a.level === 3).length;

  const breakdown =
    redCount > 0 && orangeCount > 0
      ? `RED ${redCount} · ORANGE ${orangeCount}`
      : redCount > 0
      ? `RED ${redCount}`
      : `ORANGE ${orangeCount}`;

  return (
    <div
      role="alert"
      aria-live={isRed ? "assertive" : "polite"}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 16px",
        background: `var(--risk-${meta.token})`,
        color: "#fff",
        animation: isRed ? "uis-pulse 1.5s ease-in-out infinite" : undefined,
        boxShadow: isRed ? "0 0 0 0 var(--risk-alert)" : undefined,
        borderLeft: `4px solid #fff`,
      }}
    >
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: "#fff",
          animation: isRed ? "uis-blink 0.6s infinite" : "uis-blink 1.5s infinite",
          flexShrink: 0,
        }}
      />
      <span style={{ fontWeight: 700, fontSize: 13 }}>
        {isRed ? "🚨 " : "⚠️ "}
        L{top.level} {lang === "ko" ? "경보 발령" : "ALERT"} · {top.region}
      </span>
      <span style={{ fontSize: 12, opacity: 0.9 }}>{top.summary}</span>
      <span
        style={{
          marginLeft: "auto",
          fontSize: 11,
          opacity: 0.9,
          fontFamily: "var(--font-mono)",
        }}
      >
        {breakdown} · {lang === "ko" ? "신뢰도" : "Conf"} {(confidence * 100).toFixed(0)}%
      </span>
    </div>
  );
}
