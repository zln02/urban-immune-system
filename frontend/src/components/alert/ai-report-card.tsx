"use client";
import { useState, type ReactNode } from "react";
import { I } from "@/components/ui/icons";
import { useAlertStream } from "@/hooks/useAlertStream";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import type { Translations, Lang } from "@/lib/i18n";

interface AIReportCardProps {
  t: Translations;
  lang: Lang;
  region?: string;
}

// **bold** 인라인 처리
function renderInline(s: string): ReactNode[] {
  const parts = s.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={i} style={{ color: "var(--text)", fontWeight: 700 }}>
        {p.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}

// 마크다운 → React 노드 변환 (경량 — # / ## / ### / **bold** / - / 1. / --- 만 처리)
function renderMarkdown(md: string): ReactNode[] {
  const out: ReactNode[] = [];
  const lines = md.split("\n");
  let bulletBuffer: string[] = [];
  const flushBullets = (key: number) => {
    if (bulletBuffer.length === 0) return;
    out.push(
      <ul
        key={`ul-${key}`}
        style={{ margin: "4px 0 8px 0", paddingLeft: 18, lineHeight: 1.7 }}
      >
        {bulletBuffer.map((b, i) => (
          <li key={i} style={{ marginBottom: 2 }}>
            {renderInline(b)}
          </li>
        ))}
      </ul>,
    );
    bulletBuffer = [];
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushBullets(idx);
      out.push(<div key={`sp-${idx}`} style={{ height: 6 }} />);
      return;
    }
    if (line.startsWith("---")) {
      flushBullets(idx);
      out.push(
        <hr
          key={`hr-${idx}`}
          style={{
            border: "none",
            borderTop: "1px solid var(--border)",
            margin: "8px 0",
          }}
        />,
      );
      return;
    }
    if (line.startsWith("### ")) {
      flushBullets(idx);
      out.push(
        <div key={idx} style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", marginTop: 8 }}>
          {renderInline(line.slice(4))}
        </div>,
      );
      return;
    }
    if (line.startsWith("## ")) {
      flushBullets(idx);
      out.push(
        <div
          key={idx}
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: "var(--primary-70)",
            marginTop: 10,
            marginBottom: 4,
          }}
        >
          {renderInline(line.slice(3))}
        </div>,
      );
      return;
    }
    if (line.startsWith("# ")) {
      flushBullets(idx);
      out.push(
        <div
          key={idx}
          style={{ fontSize: 14, fontWeight: 700, color: "var(--primary-70)", marginBottom: 4 }}
        >
          {renderInline(line.slice(2))}
        </div>,
      );
      return;
    }
    if (/^[-*]\s+/.test(line)) {
      bulletBuffer.push(line.replace(/^[-*]\s+/, ""));
      return;
    }
    if (/^\d+\.\s+/.test(line)) {
      flushBullets(idx);
      out.push(
        <div key={idx} style={{ paddingLeft: 14, textIndent: -14 }}>
          {renderInline(line)}
        </div>,
      );
      return;
    }
    flushBullets(idx);
    out.push(<div key={idx}>{renderInline(line)}</div>);
  });
  flushBullets(9999);
  return out;
}

export function AIReportCard({ t, lang, region = "전북특별자치도" }: AIReportCardProps) {
  const { text, citations, streaming, done, error, start, reset } = useAlertStream(region);
  const [pdfDownloading, setPdfDownloading] = useState(false);

  const downloadPdf = async () => {
    if (pdfDownloading) return;
    try {
      setPdfDownloading(true);
      const url = `/api/v1/alerts/report-pdf?region=${encodeURIComponent(region)}`;
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`PDF ${res.status}`);
      const blob = await res.blob();
      const link = document.createElement("a");
      const objUrl = URL.createObjectURL(blob);
      link.href = objUrl;
      link.download = `UIS_alert_${region}_${new Date().toISOString().slice(0, 10)}.pdf`;
      link.click();
      URL.revokeObjectURL(objUrl);
    } catch (e) {
      console.error(e);
      alert(lang === "ko" ? "PDF 생성 실패 — 백엔드 로그 확인 필요" : "PDF generation failed");
    } finally {
      setPdfDownloading(false);
    }
  };

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <I.Sparkle size={14} stroke="var(--primary-70)" />
          <span style={{ fontSize: 13, fontWeight: 600 }}>{t.ai_report_title}</span>
          <InfoTooltip term="rag" />
          <InfoTooltip term="sse" />
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {done && (
            <button
              type="button"
              onClick={reset}
              style={{
                padding: "4px 10px",
                fontSize: 11,
                background: "transparent",
                border: "1px solid var(--border-strong)",
                color: "var(--text-secondary)",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              {lang === "ko" ? "초기화" : "Reset"}
            </button>
          )}
          <button
            type="button"
            onClick={start}
            disabled={streaming}
            style={{
              padding: "4px 12px",
              fontSize: 11,
              fontWeight: 600,
              background: streaming ? "var(--border)" : "var(--primary-70)",
              color: streaming ? "var(--text-secondary)" : "#fff",
              border: "none",
              cursor: streaming ? "not-allowed" : "pointer",
              fontFamily: "inherit",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
          >
            {streaming ? (
              <>
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: "var(--primary-70)",
                    animation: "uis-blink 1s infinite",
                  }}
                />
                {t.ai_report_generating}
              </>
            ) : (
              <>
                <I.Sparkle size={12} stroke="#fff" />
                {t.ai_report_generate}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Watermark strip */}
      {(streaming || done || error) && (
        <div
          style={{
            padding: "4px 16px",
            background: "var(--bg-sub)",
            borderBottom: "1px solid var(--border)",
            fontSize: 10,
            color: "var(--text-tertiary)",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              background: "var(--risk-caution)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 7,
              color: "#fff",
              fontWeight: 700,
            }}
          >
            !
          </span>
          {t.ai_report_watermark} · Claude claude-sonnet-4-6 · {region}
        </div>
      )}

      {/* Body */}
      <div
        style={{
          flex: 1,
          padding: 16,
          minHeight: 200,
          overflowY: "auto",
        }}
      >
        {!text && !streaming && !error && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: 160,
              gap: 8,
              color: "var(--text-tertiary)",
              fontSize: 12,
              textAlign: "center",
            }}
          >
            <I.Sparkle size={28} stroke="var(--border-strong)" />
            <div>
              {lang === "ko"
                ? "버튼을 누르면 Claude가 실시간으로 경보 리포트를 작성합니다"
                : "Click the button to generate a real-time alert report with Claude"}
            </div>
            <div style={{ fontSize: 10, opacity: 0.7 }}>
              {lang === "ko"
                ? "SSE 스트리밍 · 3계층 신호 분석"
                : "SSE streaming · 3-layer signal analysis"}
            </div>
          </div>
        )}

        {error && (
          <div
            style={{
              padding: 12,
              background: "#fef2f2",
              border: "1px solid var(--risk-alert)",
              color: "var(--risk-alert)",
              fontSize: 12,
            }}
          >
            ⊗ {error}
          </div>
        )}

        {text && (
          <div
            style={{
              fontSize: 12,
              lineHeight: 1.6,
              color: "var(--text-secondary)",
              fontFamily: "var(--font-sans)",
            }}
          >
            {renderMarkdown(text)}
            {streaming && (
              <span
                style={{
                  display: "inline-block",
                  width: 2,
                  height: "1em",
                  background: "var(--primary-70)",
                  marginLeft: 2,
                  verticalAlign: "middle",
                  animation: "uis-cursor 0.8s infinite",
                }}
              />
            )}
          </div>
        )}
      </div>

      {/* RAG 인용 출처 패널 — citations 메타이벤트 수신 시 표시 */}
      {citations.length > 0 && (
        <div
          style={{
            padding: "8px 16px",
            borderTop: "1px solid var(--border)",
            background: "var(--bg-sub)",
            fontSize: 11,
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              color: "var(--text-secondary)",
              marginBottom: 6,
              textTransform: "uppercase",
              letterSpacing: 0.4,
            }}
          >
            {lang === "ko" ? "참고 가이드 (RAG 검색 결과)" : "Reference guidelines (RAG hits)"}
          </div>
          <ol style={{ margin: 0, paddingLeft: 18, color: "var(--text-secondary)", lineHeight: 1.45 }}>
            {citations.map((c) => (
              <li key={c.rank} style={{ marginBottom: 3 }}>
                {c.url ? (
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--primary-70)", textDecoration: "none" }}
                  >
                    {c.source}
                  </a>
                ) : (
                  <span>{c.source}</span>
                )}
                <span
                  style={{
                    fontSize: 9,
                    color: "var(--text-tertiary)",
                    marginLeft: 6,
                  }}
                >
                  · {c.topic} · {c.score.toFixed(2)}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {done && (
        <div
          style={{
            padding: "8px 16px",
            borderTop: "1px solid var(--border)",
            fontSize: 10,
            color: "var(--text-tertiary)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{lang === "ko" ? "생성 완료 · PDF로 내려받기" : "Generation complete"}</span>
          <button
            type="button"
            onClick={downloadPdf}
            disabled={pdfDownloading}
            style={{
              fontSize: 10,
              fontWeight: 600,
              padding: "4px 10px",
              background: pdfDownloading ? "var(--border)" : "var(--primary-70)",
              border: "none",
              color: "#fff",
              cursor: pdfDownloading ? "wait" : "pointer",
              fontFamily: "inherit",
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
            }}
          >
            <I.Download size={11} stroke="#fff" />
            {pdfDownloading
              ? lang === "ko" ? "PDF 생성 중…" : "Generating…"
              : lang === "ko" ? "PDF 다운로드" : "Download PDF"}
          </button>
        </div>
      )}
    </div>
  );
}
