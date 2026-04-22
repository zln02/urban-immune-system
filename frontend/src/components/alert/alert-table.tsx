import type { AlertRecord } from "@/lib/mock-data";
import type { Translations, Lang } from "@/lib/i18n";
import { RISK_META, type RiskLevel } from "@/lib/risk";

interface AlertTableProps {
  alerts: AlertRecord[];
  t: Translations;
  lang: Lang;
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
              const meta = RISK_META[alert.level as RiskLevel];
              return (
                <tr
                  key={alert.id}
                  style={{
                    borderTop: "1px solid var(--border)",
                    background: idx % 2 === 0 ? "transparent" : "var(--bg-sub)",
                  }}
                >
                  <td
                    style={{
                      padding: "8px 12px",
                      color: "var(--text-tertiary)",
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                    }}
                  >
                    {alert.id.slice(-6)}
                  </td>
                  <td style={{ padding: "8px 12px" }}>
                    <div style={{ fontWeight: 500 }}>{alert.region}</div>
                    <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 1 }}>
                      {alert.summary.slice(0, 30)}…
                    </div>
                  </td>
                  <td style={{ padding: "8px 12px" }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 3,
                        padding: "2px 6px",
                        fontSize: 10,
                        fontWeight: 700,
                        background: `var(--risk-${meta.token})`,
                        color: "#fff",
                      }}
                    >
                      L{alert.level}
                    </span>
                  </td>
                  <td
                    style={{
                      padding: "8px 12px",
                      color: "var(--text-secondary)",
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {alert.time}
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
