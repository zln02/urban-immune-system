"use client";
import { I } from "@/components/ui/icons";
import { useAlertStream } from "@/hooks/useAlertStream";
import type { Translations, Lang } from "@/lib/i18n";

interface AIReportCardProps {
  t: Translations;
  lang: Lang;
  region?: string;
}

export function AIReportCard({ t, lang, region = "전북특별자치도" }: AIReportCardProps) {
  const { text, streaming, done, error, start, reset } = useAlertStream(region);

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
              lineHeight: 1.7,
              color: "var(--text)",
              whiteSpace: "pre-wrap",
              fontFamily: "var(--font-sans)",
            }}
          >
            {text}
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

      {done && (
        <div
          style={{
            padding: "8px 16px",
            borderTop: "1px solid var(--border)",
            fontSize: 10,
            color: "var(--text-tertiary)",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>{lang === "ko" ? "생성 완료" : "Generation complete"}</span>
          <button
            type="button"
            style={{
              fontSize: 10,
              background: "none",
              border: "none",
              color: "var(--primary-70)",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
            onClick={() => {
              const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `uis-alert-report-${region}.txt`;
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            <I.Download size={11} stroke="var(--primary-70)" /> {lang === "ko" ? "다운로드" : "Download"}
          </button>
        </div>
      )}
    </div>
  );
}
