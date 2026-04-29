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
  const critical = alerts.filter((a) => a.level >= 4);
  if (critical.length === 0) return null;

  const top = critical[0];
  const meta = RISK_META[top.level as RiskLevel];

  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 16px",
        background: `var(--risk-${meta.token})`,
        color: "#fff",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "#fff",
          animation: "uis-blink 1s infinite",
          flexShrink: 0,
        }}
      />
      <span style={{ fontWeight: 700, fontSize: 12 }}>
        <span aria-label={lang === "ko" ? `L${top.level} ${meta.token.toUpperCase()} 경보` : `L${top.level} ${meta.token.toUpperCase()} ALERT`} style={{ display: "inline" }}>
          ⚠
        </span>
        {" "}L{top.level} {lang === "ko" ? "경보" : "ALERT"} · {top.region}
      </span>
      <span style={{ fontSize: 12, opacity: 0.9 }}>{top.summary}</span>
      <span
        style={{
          marginLeft: "auto",
          fontSize: 11,
          opacity: 0.85,
        }}
      >
        {lang === "ko" ? "신뢰도" : "Confidence"} {(confidence * 100).toFixed(0)}%
        &nbsp;·&nbsp;
        {alerts.length} {lang === "ko" ? "개 지역" : "regions"}
      </span>
    </div>
  );
}
