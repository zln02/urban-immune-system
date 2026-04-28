import type { AlertRecord } from "@/lib/mock-data";
import type { Translations, Lang } from "@/lib/i18n";
import { RISK_META, type RiskLevel } from "@/lib/risk";
import type { RegionAlert } from "@/hooks/useRegionAlerts";

interface AlertTableProps {
  alerts: AlertRecord[] | RegionAlert[];
  t: Translations;
  lang: Lang;
}

const LEVEL_TO_NUM: Record<string, RiskLevel> = {
  GREEN: 1, YELLOW: 2, ORANGE: 3, RED: 4,
};

function isRegionAlert(a: AlertRecord | RegionAlert): a is RegionAlert {
  return "alert_level" in a && "composite" in a;
}

export function AlertTable({ alerts, t, lang }: AlertTableProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
          fontSize: 13,
          fontWeight: 600,
        }}
      >
        {t.alert_table_title}
      </div>
      <div style={{ overflow: "auto", flex: 1 }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 11,
          }}
        >
          <thead>
            <tr
              style={{
                background: "var(--bg-sub)",
                color: "var(--text-tertiary)",
                textAlign: "left",
              }}
            >
              {[
                lang === "ko" ? "ID" : "ID",
                lang === "ko" ? "지역" : "Region",
                lang === "ko" ? "단계" : "Level",
                lang === "ko" ? "시간" : "Time",
              ].map((h) => (
                <th
                  key={h}
                  className="t-label-01"
                  style={{ padding: "6px 12px", fontWeight: 600, whiteSpace: "nowrap" }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert, idx) => {
              const isReal = isRegionAlert(alert);
              const level = isReal ? LEVEL_TO_NUM[alert.alert_level] ?? 1 : alert.level;
              const meta = RISK_META[level as RiskLevel];
              const id = isReal ? alert.region.slice(0, 6) : alert.id.slice(-6);
              const region = alert.region;
              const summary = isReal
                ? `composite=${alert.composite} (L1=${alert.l1.toFixed(0)}/L2=${alert.l2.toFixed(0)}/L3=${alert.l3.toFixed(0)})`
                : alert.summary;
              const time = isReal
                ? (alert.latest_time ? alert.latest_time.slice(0, 10) : "—")
                : alert.time;
              const labelText = isReal ? alert.alert_level : `L${alert.level}`;
              return (
                <tr
                  key={isReal ? alert.region : alert.id}
                  style={{
                    borderTop: "1px solid var(--border)",
                    background: idx % 2 === 0 ? "transparent" : "var(--bg-sub)",
                  }}
                >
                  <td style={{ padding: "8px 12px", color: "var(--text-tertiary)", fontFamily: "var(--font-mono)", fontSize: 10 }}>
                    {id}
                  </td>
                  <td style={{ padding: "8px 12px" }}>
                    <div style={{ fontWeight: 500 }}>{region}</div>
                    <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 1 }}>
                      {summary.slice(0, 50)}{summary.length > 50 ? "…" : ""}
                    </div>
                  </td>
                  <td style={{ padding: "8px 12px" }}>
                    <span
                      style={{
                        display: "inline-flex", alignItems: "center", gap: 3,
                        padding: "2px 6px", fontSize: 10, fontWeight: 700,
                        background: `var(--risk-${meta.token})`, color: "#fff",
                      }}
                    >
                      {labelText}
                    </span>
                  </td>
                  <td style={{ padding: "8px 12px", color: "var(--text-secondary)", fontFamily: "var(--font-mono)", fontSize: 10, whiteSpace: "nowrap" }}>
                    {time}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
