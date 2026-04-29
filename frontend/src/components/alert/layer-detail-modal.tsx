"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

export interface LayerSeriesPoint {
  date: string; // ISO 또는 YYYY-MM-DD
  value: number;
  raw?: number; // 원시값 (정규화 전, 있으면 표시)
}

interface LayerDetailModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  layer: "otc" | "wastewater" | "search";
  color: string;
  icon?: ReactNode;
  series: LayerSeriesPoint[];
  /** 데이터 출처 한 줄 설명 */
  source?: string;
  /** 단위 표기 (예: "정규화 (0~100)" 또는 "log10 copies/mL") */
  unit?: string;
  /** "전국 단일값" 등 caveat */
  caveat?: { title: string; body: string };
  lang: "ko" | "en";
}

const COPY: Record<"ko" | "en", Record<string, string>> = {
  ko: {
    summary: "요약 통계",
    latest: "최신",
    min: "최소",
    max: "최대",
    avg: "평균",
    count: "관측 수",
    period: "기간",
    chart: "시계열 차트",
    table: "날짜별 데이터",
    date: "날짜",
    value: "정규화값",
    raw: "원시값",
    noData: "표시할 데이터가 없습니다.",
    close: "닫기",
    copyCsv: "CSV 복사",
    csvCopied: "복사됨",
    sortAsc: "오래된순",
    sortDesc: "최신순",
  },
  en: {
    summary: "Summary",
    latest: "Latest",
    min: "Min",
    max: "Max",
    avg: "Avg",
    count: "Points",
    period: "Range",
    chart: "Time series",
    table: "Date table",
    date: "Date",
    value: "Normalized",
    raw: "Raw",
    noData: "No data to display.",
    close: "Close",
    copyCsv: "Copy CSV",
    csvCopied: "Copied",
    sortAsc: "Oldest first",
    sortDesc: "Latest first",
  },
};

function formatDate(iso: string): string {
  // YYYY-MM-DD 또는 ISO 모두 처리
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const yy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
}

function fmt(n: number, digits = 2): string {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

export function LayerDetailModal({
  open,
  onClose,
  title,
  color,
  icon,
  series,
  source,
  unit,
  caveat,
  lang,
}: LayerDetailModalProps) {
  const t = COPY[lang];
  const [sortDesc, setSortDesc] = useState(true);
  const [copied, setCopied] = useState(false);

  // ESC 닫기
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const stats = useMemo(() => {
    if (series.length === 0) return null;
    const vals = series.map((p) => p.value);
    return {
      count: series.length,
      latest: vals[vals.length - 1],
      min: Math.min(...vals),
      max: Math.max(...vals),
      avg: vals.reduce((a, b) => a + b, 0) / vals.length,
      first: formatDate(series[0].date),
      last: formatDate(series[series.length - 1].date),
    };
  }, [series]);

  const sortedRows = useMemo(() => {
    const rows = [...series];
    rows.sort((a, b) =>
      sortDesc ? b.date.localeCompare(a.date) : a.date.localeCompare(b.date)
    );
    return rows;
  }, [series, sortDesc]);

  if (!open) return null;

  const handleCopyCsv = async () => {
    const header = "date,value" + (series.some((p) => p.raw !== undefined) ? ",raw" : "");
    const rows = series
      .map((p) => `${formatDate(p.date)},${p.value}${p.raw !== undefined ? `,${p.raw}` : ""}`)
      .join("\n");
    try {
      await navigator.clipboard.writeText(`${header}\n${rows}`);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard 실패 무시 */
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
      style={overlayStyle}
    >
      <div onClick={(e) => e.stopPropagation()} style={panelStyle}>
        {/* 헤더 */}
        <div style={{ ...headerStyle, borderTop: `4px solid ${color}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
            <span style={{ color, display: "grid", placeItems: "center", flexShrink: 0 }}>{icon}</span>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 16, color: "var(--text)" }}>{title}</div>
              {source && (
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                  {source}
                </div>
              )}
            </div>
          </div>
          <button
            type="button"
            aria-label={t.close}
            onClick={onClose}
            style={closeBtn}
          >
            ✕
          </button>
        </div>

        {/* caveat */}
        {caveat && (
          <div style={caveatBox}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 2 }}>
              ⓘ {caveat.title}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>
              {caveat.body}
            </div>
          </div>
        )}

        {/* 본문 */}
        <div style={bodyStyle}>
          {!stats ? (
            <div style={emptyStyle}>{t.noData}</div>
          ) : (
            <>
              {/* 요약 통계 */}
              <section>
                <div style={sectionTitleStyle}>{t.summary}</div>
                <div style={statsGrid}>
                  <Stat label={t.latest} value={fmt(stats.latest)} accent={color} />
                  <Stat label={t.min} value={fmt(stats.min)} />
                  <Stat label={t.max} value={fmt(stats.max)} />
                  <Stat label={t.avg} value={fmt(stats.avg)} />
                  <Stat label={t.count} value={String(stats.count)} />
                  <Stat label={t.period} value={`${stats.first} ~ ${stats.last}`} small />
                </div>
              </section>

              {/* 차트 */}
              <section style={{ marginTop: 16 }}>
                <div style={sectionTitleStyle}>{t.chart}</div>
                <DetailChart series={series} color={color} unit={unit} lang={lang} />
              </section>

              {/* 데이터 테이블 */}
              <section style={{ marginTop: 16 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <div style={sectionTitleStyle}>{t.table}</div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      type="button"
                      onClick={() => setSortDesc((v) => !v)}
                      style={miniBtn}
                      aria-label={sortDesc ? t.sortAsc : t.sortDesc}
                      title={sortDesc ? t.sortAsc : t.sortDesc}
                    >
                      ⇅ {sortDesc ? t.sortDesc : t.sortAsc}
                    </button>
                    <button
                      type="button"
                      onClick={handleCopyCsv}
                      style={miniBtn}
                      aria-label={t.copyCsv}
                    >
                      {copied ? `✓ ${t.csvCopied}` : `⧉ ${t.copyCsv}`}
                    </button>
                  </div>
                </div>
                <div style={tableWrap}>
                  <table style={tableStyle}>
                    <thead>
                      <tr>
                        <th style={thStyle}>{t.date}</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>{t.value}</th>
                        {series.some((p) => p.raw !== undefined) && (
                          <th style={{ ...thStyle, textAlign: "right" }}>{t.raw}</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {sortedRows.map((p) => (
                        <tr key={p.date}>
                          <td style={tdStyle}>{formatDate(p.date)}</td>
                          <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                            {fmt(p.value)}
                          </td>
                          {series.some((s) => s.raw !== undefined) && (
                            <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                              {p.raw !== undefined ? fmt(p.raw, 4) : "—"}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── 통계 칩 ────────────────────────────────────────────────────────────────
function Stat({ label, value, accent, small }: { label: string; value: string; accent?: string; small?: boolean }) {
  return (
    <div style={statCardStyle}>
      <div style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </div>
      <div
        style={{
          fontSize: small ? 12 : 18,
          fontWeight: 700,
          fontFamily: "var(--font-mono)",
          color: accent ?? "var(--text)",
          marginTop: 2,
        }}
      >
        {value}
      </div>
    </div>
  );
}

// ── 상세 차트 (SVG) ────────────────────────────────────────────────────────
function DetailChart({
  series,
  color,
  unit,
  lang,
}: {
  series: LayerSeriesPoint[];
  color: string;
  unit?: string;
  lang: "ko" | "en";
}) {
  const [hover, setHover] = useState<{ x: number; y: number; idx: number } | null>(null);
  if (series.length < 2) {
    return (
      <div style={emptyStyle}>{lang === "ko" ? "차트를 그리려면 2개 이상 필요" : "need ≥2 points"}</div>
    );
  }

  const W = 520;
  const H = 180;
  const padL = 36;
  const padR = 12;
  const padT = 12;
  const padB = 28;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const vals = series.map((p) => p.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;

  const x = (i: number) => padL + (i / (series.length - 1)) * innerW;
  const y = (v: number) => padT + (1 - (v - min) / range) * innerH;

  const linePath =
    `M ${x(0)} ${y(vals[0])} ` +
    vals.slice(1).map((v, i) => `L ${x(i + 1)} ${y(v)}`).join(" ");
  const areaPath = `${linePath} L ${x(series.length - 1)} ${padT + innerH} L ${x(0)} ${padT + innerH} Z`;

  // Y축 눈금 4개
  const ticks = [0, 0.33, 0.66, 1].map((t) => min + range * t);

  // X축 라벨: 시작·중간·끝
  const xLabels = [0, Math.floor(series.length / 2), series.length - 1];

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    if (px < padL || px > W - padR) {
      setHover(null);
      return;
    }
    const ratio = (px - padL) / innerW;
    const idx = Math.round(ratio * (series.length - 1));
    if (idx < 0 || idx >= series.length) {
      setHover(null);
      return;
    }
    setHover({ x: x(idx), y: y(series[idx].value), idx });
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        style={{ display: "block", background: "var(--bg-sub)", borderRadius: 8 }}
      >
        {/* Y 그리드 + 라벨 */}
        {ticks.map((tv, i) => (
          <g key={i}>
            <line
              x1={padL}
              x2={W - padR}
              y1={y(tv)}
              y2={y(tv)}
              stroke="var(--border)"
              strokeDasharray="2 3"
              strokeWidth={0.7}
            />
            <text
              x={padL - 6}
              y={y(tv) + 3}
              fontSize={9}
              fill="var(--text-tertiary)"
              textAnchor="end"
              fontFamily="var(--font-mono)"
            >
              {tv.toFixed(1)}
            </text>
          </g>
        ))}

        {/* 영역 + 라인 */}
        <path d={areaPath} fill={color} fillOpacity={0.14} />
        <path d={linePath} fill="none" stroke={color} strokeWidth={1.8} strokeLinejoin="round" />

        {/* X축 라벨 */}
        {xLabels.map((i, k) => (
          <text
            key={k}
            x={x(i)}
            y={H - 8}
            fontSize={9}
            fill="var(--text-tertiary)"
            textAnchor={k === 0 ? "start" : k === xLabels.length - 1 ? "end" : "middle"}
            fontFamily="var(--font-mono)"
          >
            {formatDate(series[i].date)}
          </text>
        ))}

        {/* 호버 마커 */}
        {hover && (
          <>
            <line
              x1={hover.x}
              x2={hover.x}
              y1={padT}
              y2={padT + innerH}
              stroke={color}
              strokeOpacity={0.4}
              strokeWidth={1}
            />
            <circle cx={hover.x} cy={hover.y} r={4} fill={color} stroke="#fff" strokeWidth={1.5} />
          </>
        )}
      </svg>

      {hover && (
        <div
          style={{
            position: "absolute",
            top: 4,
            right: 8,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "5px 9px",
            fontSize: 11,
            boxShadow: "0 2px 8px rgba(15, 23, 42, 0.1)",
            pointerEvents: "none",
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--text)" }}>
            {formatDate(series[hover.idx].date)}
          </div>
          <div style={{ color, fontFamily: "var(--font-mono)", fontWeight: 700 }}>
            {fmt(series[hover.idx].value)}
            {unit ? <span style={{ fontSize: 9, color: "var(--text-tertiary)", marginLeft: 4 }}>{unit}</span> : null}
          </div>
        </div>
      )}
    </div>
  );
}

// ── 스타일 ────────────────────────────────────────────────────────────────
const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.55)",
  backdropFilter: "blur(2px)",
  display: "grid",
  placeItems: "center",
  zIndex: 10000,
  padding: 20,
  animation: "uis-chat-pop 0.18s ease-out",
};

const panelStyle: React.CSSProperties = {
  width: "min(720px, 100%)",
  maxHeight: "min(80vh, 720px)",
  background: "var(--surface)",
  borderRadius: 14,
  boxShadow: "0 24px 60px rgba(15, 23, 42, 0.32)",
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
  fontFamily: "var(--font-sans)",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  padding: "14px 18px 12px",
  borderBottom: "1px solid var(--border)",
  flexShrink: 0,
};

const closeBtn: React.CSSProperties = {
  width: 28,
  height: 28,
  border: "none",
  background: "var(--bg-sub)",
  borderRadius: 6,
  cursor: "pointer",
  fontSize: 14,
  color: "var(--text-secondary)",
  flexShrink: 0,
};

const caveatBox: React.CSSProperties = {
  margin: "0 18px",
  marginTop: 12,
  padding: "8px 10px",
  background: "var(--bg-sub)",
  border: "1px solid var(--border)",
  borderRadius: 6,
};

const bodyStyle: React.CSSProperties = {
  padding: "16px 18px 20px",
  overflowY: "auto",
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 0.6,
  textTransform: "uppercase",
  color: "var(--text-secondary)",
  marginBottom: 8,
};

const statsGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
  gap: 8,
};

const statCardStyle: React.CSSProperties = {
  background: "var(--bg-sub)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "8px 10px",
};

const tableWrap: React.CSSProperties = {
  maxHeight: 240,
  overflowY: "auto",
  border: "1px solid var(--border)",
  borderRadius: 8,
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 12,
};

const thStyle: React.CSSProperties = {
  position: "sticky",
  top: 0,
  background: "var(--bg-sub)",
  padding: "7px 10px",
  textAlign: "left",
  fontWeight: 600,
  color: "var(--text-secondary)",
  borderBottom: "1px solid var(--border)",
  fontSize: 11,
};

const tdStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderBottom: "1px solid var(--border)",
  color: "var(--text)",
};

const miniBtn: React.CSSProperties = {
  padding: "4px 9px",
  fontSize: 11,
  border: "1px solid var(--border)",
  background: "var(--surface)",
  borderRadius: 6,
  cursor: "pointer",
  color: "var(--text-secondary)",
  fontFamily: "inherit",
};

const emptyStyle: React.CSSProperties = {
  padding: 24,
  textAlign: "center",
  color: "var(--text-tertiary)",
  fontSize: 12,
};
