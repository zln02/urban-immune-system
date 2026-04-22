import { I } from "@/components/ui/icons";
import type { Dict, Lang } from "@/lib/i18n";

interface AIReportCardProps {
  t: Dict;
  lang: Lang;
}

const FINDINGS_KO: [string, string][] = [
  ["전북 전주시 해열제 OTC 판매량이 14일 기준선 대비 28.4% 증가 (p=0.003)", "layer-pharmacy"],
  ["광주 송정 하수처리장 SARS-CoV-2 N유전자 카피수 3.1배 급증 (04-22 이후)", "layer-sewage"],
  ["검색어 \"기침 열 사흘\"이 전북·전남 지역에서 2.3배 피크 (04-26)", "layer-search"],
  ["Granger 인과분석 결과 OTC가 임상을 약 2주 선행 (lag 14)", "text-secondary"],
];

const FINDINGS_EN: [string, string][] = [
  ["Jeonju-si OTC antipyretic sales up 28.4% vs 14-day baseline (p=0.003)", "layer-pharmacy"],
  ["Gwangju WWTP SARS-CoV-2 N-gene copies surged 3.1× since 04-22", "layer-sewage"],
  ['Search query "기침 열 사흘" peaked 2.3× in Jeonbuk/Jeonnam (04-26)', "layer-search"],
  ["Granger causality (lag 14) confirms OTC leading clinical by ~2 weeks", "text-secondary"],
];

/**
 * RAG 기반 AI 경보 리포트 카드 — AI 생성 배지 + 인간 검토 주의 문구 + PDF 다운로드 CTA.
 */
export function AIReportCard({ t, lang }: AIReportCardProps) {
  const findings = lang === "en" ? FINDINGS_EN : FINDINGS_KO;
  return (
    <section
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        position: "relative",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 10,
          fontSize: 9,
          fontWeight: 600,
          padding: "2px 8px",
          background: "var(--primary-70)",
          color: "var(--gray-0)",
          letterSpacing: 0.5,
          textTransform: "uppercase",
        }}
      >
        ⚡ {t.ai_watermark}
      </div>
      <header style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
        <div className="t-h-02">{t.ai_title}</div>
        <div
          className="t-label-02"
          style={{ color: "var(--text-tertiary)", fontWeight: 400, marginTop: 2 }}
        >
          {t.ai_sub}
        </div>
      </header>
      <div
        style={{
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div
          className="t-label-02"
          style={{
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: 0.32,
          }}
        >
          {t.ai_finding}
        </div>
        <ul
          style={{
            margin: 0,
            padding: 0,
            listStyle: "none",
            fontSize: 13,
            lineHeight: 1.6,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          {findings.map(([text, color], i) => (
            <li key={i} style={{ display: "flex", gap: 10 }}>
              <span
                style={{
                  flexShrink: 0,
                  width: 18,
                  fontSize: 10,
                  fontWeight: 700,
                  color: `var(--${color})`,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span style={{ color: "var(--text)" }}>{text}</span>
            </li>
          ))}
        </ul>
        <div
          style={{
            padding: "10px 12px",
            background: "var(--bg-sub)",
            fontSize: 11,
            color: "var(--text-tertiary)",
            lineHeight: 1.5,
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
          }}
        >
          <I.Alert size={14} stroke="var(--risk-warning)" />
          <span>
            {lang === "en"
              ? "AI-generated summary. Human surveillance officer review required before field dispatch."
              : "AI가 생성한 요약입니다. 현장 파견 전 감시 공무원의 검토가 필수입니다."}
          </span>
        </div>
        <div
          style={{
            display: "flex",
            gap: 8,
            justifyContent: "flex-end",
            borderTop: "1px solid var(--border)",
            paddingTop: 12,
          }}
        >
          <button
            type="button"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "7px 12px",
              fontSize: 12,
              fontWeight: 500,
              background: "transparent",
              color: "var(--text)",
              border: "1px solid var(--border-strong)",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            {lang === "en" ? "View full report" : "전체 리포트"} →
          </button>
          <button
            type="button"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "7px 14px",
              fontSize: 12,
              fontWeight: 500,
              background: "var(--primary-70)",
              color: "var(--gray-0)",
              border: "none",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <I.Download size={14} /> {t.ai_action}
          </button>
        </div>
      </div>
    </section>
  );
}
