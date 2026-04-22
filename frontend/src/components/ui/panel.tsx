import type { ReactNode } from "react";

interface PanelProps {
  title: ReactNode;
  sub?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

/**
 * Carbon-style bordered panel — 대시보드 카드 표준 래퍼.
 */
export function Panel({ title, sub, actions, children }: PanelProps) {
  return (
    <section
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
          gap: 12,
        }}
      >
        <div>
          <div className="t-h-02">{title}</div>
          {sub && (
            <div
              className="t-label-02"
              style={{ color: "var(--text-tertiary)", fontWeight: 400, marginTop: 2 }}
            >
              {sub}
            </div>
          )}
        </div>
        {actions}
      </header>
      <div style={{ padding: 16 }}>{children}</div>
    </section>
  );
}
