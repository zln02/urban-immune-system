import type { CSSProperties, ReactNode } from "react";

interface PanelProps {
  title?: string;
  sub?: string;
  actions?: ReactNode;
  children: ReactNode;
  style?: CSSProperties;
}

export function Panel({ title, sub, actions, children, style }: PanelProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        ...style,
      }}
    >
      {(title || actions) && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "12px 16px",
            borderBottom: "1px solid var(--border)",
            gap: 12,
            flexShrink: 0,
          }}
        >
          <div>
            {title && (
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
                {title}
              </div>
            )}
            {sub && (
              <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 1 }}>
                {sub}
              </div>
            )}
          </div>
          {actions && <div style={{ flexShrink: 0 }}>{actions}</div>}
        </div>
      )}
      <div style={{ padding: 16, flex: 1 }}>{children}</div>
    </div>
  );
}
