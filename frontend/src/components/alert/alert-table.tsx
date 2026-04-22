import { Panel } from "@/components/ui/panel";
import { RiskPill } from "@/components/ui/risk-pill";
import { regionName, type RegionCode } from "@/lib/korea-regions";
import type { AlertItem } from "@/lib/mock-data";
import type { Dict, Lang } from "@/lib/i18n";

interface AlertTableProps {
  alerts: AlertItem[];
  t: Dict;
  lang: Lang;
}

/**
 * 최근 48h 경보 목록 — 발령 시각 순, 신뢰도·신호수·ID 포함.
 */
export function AlertTable({ alerts, t, lang }: AlertTableProps) {
  return (
    <Panel
      title={lang === "en" ? "Recent alerts" : "최근 경보"}
      sub={lang === "en" ? "Last 48h · sorted by issue time" : "최근 48시간 · 발령 순"}
    >
      <div style={{ display: "flex", flexDirection: "column" }}>
        {alerts.length === 0 && (
          <div
            style={{
              padding: 24,
              textAlign: "center",
              color: "var(--text-tertiary)",
              fontSize: 12,
            }}
          >
            {lang === "en" ? "No active alerts" : "활성 경보 없음"}
          </div>
        )}
        {alerts.map((a, i) => (
          <div
            key={a.id}
            style={{
              display: "grid",
              gridTemplateColumns: "auto 1fr auto auto",
              gap: 12,
              alignItems: "center",
              padding: "10px 0",
              borderTop: i === 0 ? "none" : "1px solid var(--border)",
            }}
          >
            <RiskPill level={a.level} lang={lang} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>
                {regionName(a.district as RegionCode, lang)} · {a.signals}/3{" "}
                {lang === "en" ? "layers" : "신호"}
              </div>
              <div className="t-mono" style={{ color: "var(--text-tertiary)" }}>
                {a.id}
              </div>
            </div>
            <div
              style={{
                textAlign: "right",
                fontSize: 11,
                color: "var(--text-tertiary)",
              }}
            >
              <div style={{ fontVariantNumeric: "tabular-nums" }}>
                {a.issued.split(" ")[1]}
              </div>
              <div>
                {lang === "en" ? "conf." : "신뢰도"} {a.confidence.toFixed(2)}
              </div>
            </div>
            <button
              type="button"
              aria-label={lang === "en" ? "Open alert" : "경보 열기"}
              style={{
                padding: "4px 8px",
                fontSize: 12,
                background: "transparent",
                color: "var(--text)",
                border: "1px solid var(--border-strong)",
                cursor: "pointer",
              }}
            >
              →
            </button>
          </div>
        ))}
        {t.trigger && (
          <div
            style={{
              marginTop: 16,
              padding: "8px 12px",
              background: "var(--bg-sub)",
              fontSize: 11,
              color: "var(--text-tertiary)",
              lineHeight: 1.5,
            }}
          >
            {t.trigger}
          </div>
        )}
      </div>
    </Panel>
  );
}
