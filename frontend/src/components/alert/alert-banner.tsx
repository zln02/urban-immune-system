import type { ReactNode } from "react";
import { I } from "@/components/ui/icons";
import { regionName, type RegionCode } from "@/lib/korea-regions";
import type { Dict, Lang } from "@/lib/i18n";
import type { AlertItem } from "@/lib/mock-data";

interface AlertBannerProps {
  alerts: AlertItem[];
  t: Dict;
  lang: Lang;
  alertId?: string;
  confidence?: number;
  onOpenReport?: () => void;
  onAcknowledge?: () => void;
}

/**
 * Hero 경보 배너 — Conservative 변형의 시그니처 스캐너빌리티.
 * 좌: 대형 숫자 / 중: 메시지 + 진앙 / 우: CTA 2종.
 */
export function AlertBanner({
  alerts,
  t,
  lang,
  alertId = alerts[0]?.id ?? "",
  confidence = 0.92,
  onOpenReport,
  onAcknowledge,
}: AlertBannerProps) {
  const l4 = alerts.filter((a) => a.level === 4);
  const epicenters = l4
    .map((a) => regionName(a.district as RegionCode, lang))
    .join(" · ");
  const tone = "alert";

  return (
    <div
      role="alert"
      style={{
        display: "grid",
        gridTemplateColumns: "280px 1fr auto",
        alignItems: "stretch",
        background: `var(--risk-${tone})`,
        color: "#fff",
        animation: "uis-slidein var(--dur) var(--ease) forwards",
        boxShadow: "var(--shadow-2)",
      }}
    >
      <Block title={lang === "en" ? "Level 4 · Alert" : "레벨 4 · 경보"}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <span
            style={{
              fontSize: 64,
              fontWeight: 700,
              letterSpacing: -2,
              lineHeight: 1,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {l4.length}
          </span>
          <span style={{ fontSize: 16, fontWeight: 500, opacity: 0.9 }}>
            {lang === "en" ? "regions" : "개 권역"}
          </span>
        </div>
        <div style={{ fontSize: 12, opacity: 0.88, marginTop: 6 }}>
          {lang === "en" ? "3-Layer cross-validated" : "3-Layer 교차검증 완료"}
        </div>
      </Block>

      <div
        style={{
          padding: "20px 24px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: 8,
        }}
      >
        <div
          style={{
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: -0.3,
            lineHeight: 1.2,
          }}
        >
          🚨 {t.alert_title} — {epicenters}
        </div>
        <div style={{ fontSize: 13.5, opacity: 0.92, lineHeight: 1.5 }}>
          {lang === "en"
            ? "OTC (L1) · Sewage (L2) · Search (L3) all exceeded 85th-percentile threshold at 09:14 KST. AI report generated."
            : "약국 OTC(L1) · 하수(L2) · 검색(L3) 모두 85퍼센타일 임계값을 09:14 KST에 초과. AI 리포트 생성 완료."}
        </div>
        <div style={{ display: "flex", gap: 20, fontSize: 11, opacity: 0.88, marginTop: 2 }}>
          <span className="t-mono">conf. {confidence.toFixed(2)}</span>
          <span className="t-mono">p &lt; 0.001</span>
          <span className="t-mono">ID {alertId}</span>
        </div>
      </div>

      <div
        style={{
          padding: 20,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: 8,
          borderLeft: "1px solid rgba(255,255,255,0.25)",
        }}
      >
        <button
          type="button"
          onClick={onOpenReport}
          style={{
            padding: "12px 22px",
            fontSize: 14,
            fontWeight: 600,
            fontFamily: "inherit",
            background: "#fff",
            color: `var(--risk-${tone})`,
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <I.Report size={16} stroke={`var(--risk-${tone})`} /> {t.alert_action_report} →
        </button>
        <button
          type="button"
          onClick={onAcknowledge}
          style={{
            padding: "10px 22px",
            fontSize: 12,
            fontWeight: 500,
            fontFamily: "inherit",
            background: "transparent",
            color: "#fff",
            border: "1px solid rgba(255,255,255,0.5)",
            cursor: "pointer",
          }}
        >
          {t.alert_action_ack}
        </button>
      </div>
    </div>
  );
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div
      style={{
        padding: "20px 24px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        borderRight: "1px solid rgba(255,255,255,0.25)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: 1.5,
          textTransform: "uppercase",
          marginBottom: 6,
        }}
      >
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: "#fff",
            animation: "uis-blink 1s infinite",
          }}
        />
        {title}
      </div>
      {children}
    </div>
  );
}
