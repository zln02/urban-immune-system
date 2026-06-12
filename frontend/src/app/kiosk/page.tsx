"use client";

import { useState, useEffect } from "react";
import { useRegionAlerts, type RegionAlert, type AlertLevel } from "@/hooks/useRegionAlerts";
import { useSignalSeries, useWastewaterSeries } from "@/hooks/useSignalTimeseries";
import { KoreaMap } from "@/components/map/korea-map";
import { AIReportCard } from "@/components/alert/ai-report-card";
import { TrendChart } from "@/components/charts/trend-chart";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { RiskPill } from "@/components/ui/risk-pill";
import { regionCodeFromName, type RegionCode } from "@/lib/korea-regions";
import { mockDistricts, type DistrictData, type SeriesData } from "@/lib/mock-data";
import { type RiskLevel } from "@/lib/risk";
import { DICT } from "@/lib/i18n";

const t = DICT.ko;
const LEVEL_TO_RISK: Record<AlertLevel, RiskLevel> = { GREEN: 1, YELLOW: 2, ORANGE: 3, RED: 4 };
const TOKENS = ["", "safe", "caution", "warning", "alert"] as const;
const L1_COLOR = "#be185d";
const L2_COLOR = "#047857";
const L3_COLOR = "#1d4ed8";

function buildDistricts(alerts: RegionAlert[]): Record<RegionCode, DistrictData> {
  const out: Record<RegionCode, DistrictData> = { ...mockDistricts };
  for (const a of alerts) {
    const code = regionCodeFromName(a.region);
    if (!code) continue;
    out[code] = {
      risk: LEVEL_TO_RISK[a.alert_level] ?? 1,
      cases: Math.round(a.composite * 10),
      change: Math.round((a.l1 + a.l2 + a.l3) / 3 - 30),
    };
  }
  return out;
}

function calcChange(arr: number[]): number {
  if (arr.length < 2) return 0;
  const last = arr[arr.length - 1];
  const prev = arr[arr.length - 2];
  if (prev === 0) return 0;
  return Math.round(((last - prev) / prev) * 100);
}

function SectionTitle({ accent, children }: { accent: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 700, marginBottom: 12, letterSpacing: "-0.01em" }}>
      <span style={{ width: 3, height: 16, borderRadius: 2, background: accent }} />
      {children}
    </div>
  );
}

function MiniAreaChart({ values, color, height = 64 }: { values: number[]; color: string; height?: number }) {
  if (values.length < 2) {
    return <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, opacity: 0.4 }}>수집 대기</div>;
  }
  const w = 100;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => [(i / (values.length - 1)) * w, height - ((v - min) / range) * (height - 8) - 4]);
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${w},${height} L0,${height} Z`;
  const gid = "grad" + color.replace(/[^a-zA-Z0-9]/g, "");
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" style={{ width: "100%", height, display: "block" }}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.45" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function LayerGraphCard({ title, source, dbDate, values, latest, change, color, icon, caveat }: { title: string; source: string; dbDate: string; values: number[]; latest: number; change: number; color: string; icon: string; caveat?: boolean }) {
  const up = change > 0;
  return (
    <div style={{ background: "linear-gradient(160deg, #101d33, #0a1322)", border: "1px solid #1a2740", borderRadius: 13, padding: 13 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 17 }}>{icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", gap: 5 }}>
            {title}
            {caveat && <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 4, background: "rgba(148,163,184,0.15)", color: "#94a3b8", fontWeight: 600 }}>전국</span>}
          </div>
          <div style={{ fontSize: 12, opacity: 0.6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{source}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 19, fontWeight: 800, color, lineHeight: 1 }}>{latest.toFixed(0)}</div>
          <div style={{ fontSize: 10, color: up ? "#f87171" : "#4ade80", marginTop: 2 }}>{change === 0 ? "─" : up ? "▲" : "▼"} {Math.abs(change)}%</div>
        </div>
      </div>
      <MiniAreaChart values={values} color={color} />
      <div style={{ fontSize: 11, opacity: 0.55, fontFamily: "var(--font-mono)", marginTop: 4 }}>DB 최신 {dbDate}</div>
    </div>
  );
}

function RegionDrilldown({ alert, onClose }: { alert: RegionAlert; onClose: () => void }) {
  // 3계층 전부 TimescaleDB(layer_signals) 직접 조회 — 실제 수집 데이터
  const otc = useSignalSeries("otc", alert.region, 90, "influenza");
  const search = useSignalSeries("search", alert.region, 90, "influenza");
  const sewage = useWastewaterSeries(alert.region, 365, "influenza");

  const l1 = (otc.data?.data ?? []).map((p) => Math.round(p.value));
  const l3 = (search.data?.data ?? []).map((p) => Math.round(p.value));
  const l2 = (sewage.data?.data ?? []).map((p) => Math.round(p.value));

  // 각 계층 최신 수집 시각 (DB 마지막 레코드 time)
  const lastDate = (d?: { data: { time: string }[] }): string =>
    d?.data?.length ? d.data[d.data.length - 1].time.slice(0, 10) : "수집 대기";
  const l1date = lastDate(otc.data);
  const l2date = lastDate(sewage.data);
  const l3date = lastDate(search.data);
  const series: SeriesData = { pharmacy: l1, sewage: l2, search: l3 };
  const token = TOKENS[LEVEL_TO_RISK[alert.alert_level]];

  const meta = [
    { label: "약국 OTC (L1)", w: 35, v: alert.l1, color: L1_COLOR },
    { label: "하수 바이오마커 (L2)", w: 40, v: alert.l2, color: L2_COLOR },
    { label: "검색 트렌드 (L3)", w: 25, v: alert.l3, color: L3_COLOR },
  ];
  const gateOk = alert.layers_above_30 >= 2;

  return (
    <div className="drill" style={{ display: "flex", flexDirection: "column", gap: 16, overflowY: "auto", height: "100%", paddingRight: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h2 style={{ fontSize: 28, fontWeight: 800, margin: 0, letterSpacing: "-0.02em" }}>{alert.region}</h2>
        <RiskPill level={LEVEL_TO_RISK[alert.alert_level]} lang="ko" />
        <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 12, opacity: 0.6 }}>
          최신 {alert.latest_time?.slice(0, 10) ?? "—"}
        </span>
        <button className="close-btn" onClick={onClose}>← 전국</button>
      </div>

      <div className="calc-box" style={{ borderColor: `var(--risk-${token})` }}>
        <SectionTitle accent={`var(--risk-${token})`}>
          위험도 계산 <InfoTooltip term="composite" />
        </SectionTitle>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 14 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 38, fontWeight: 800, lineHeight: 1, color: `var(--risk-${token})` }}>{alert.composite.toFixed(1)}</span>
          <span style={{ fontSize: 13, opacity: 0.55 }}>/ 100 종합점수</span>
        </div>
        {meta.map((m) => (
          <div key={m.label} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 4 }}>
              <span>{m.label} <span style={{ opacity: 0.5, fontFamily: "var(--font-mono)" }}>×{m.w}%</span></span>
              <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>{m.v.toFixed(1)}</span>
            </div>
            <div style={{ height: 8, background: "#0b1322", borderRadius: 5, overflow: "hidden" }}>
              <div style={{ width: `${Math.min(100, m.v)}%`, height: "100%", background: `linear-gradient(90deg, ${m.color}aa, ${m.color})`, borderRadius: 5, transition: "width .5s ease" }} />
            </div>
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, padding: "8px 12px", borderRadius: 9, background: gateOk ? "rgba(204,0,0,0.12)" : "rgba(148,163,184,0.08)", fontSize: 12.5 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 5 }}>교차검증 게이트 <InfoTooltip term="layers_above_30" /></span>
          <span style={{ marginLeft: "auto", fontWeight: 700, color: gateOk ? "var(--risk-alert)" : "#94a3b8" }}>
            {alert.layers_above_30}/3 계층 ≥30 · {gateOk ? "발령 조건 충족" : "단독 차단"}
          </span>
        </div>
      </div>

      <div>
        <SectionTitle accent="#38bdf8">데이터 수집 현황 <span style={{ fontSize: 11, fontWeight: 600, color: "#34d399", opacity: 0.9 }}>● TimescaleDB 실시간</span></SectionTitle>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 }}>
          <LayerGraphCard title="약국 OTC" source="네이버 쇼핑인사이트 · 주1" dbDate={l1date} values={l1} latest={alert.l1} change={calcChange(l1)} color={L1_COLOR} icon="💊" caveat />
          <LayerGraphCard title="하수 바이오마커" source="KOWAS 하수감시 · 주1" dbDate={l2date} values={l2} latest={alert.l2} change={calcChange(l2)} color={L2_COLOR} icon="💧" />
          <LayerGraphCard title="검색 트렌드" source="네이버 DataLab · 주1" dbDate={l3date} values={l3} latest={alert.l3} change={calcChange(l3)} color={L3_COLOR} icon="🔍" caveat />
        </div>
      </div>

      <div className="panel-card">
        <SectionTitle accent="#6366f1">3계층 신호 추이</SectionTitle>
        <TrendChart series={series} t={t} height={180} />
      </div>

      <div>
        <SectionTitle accent="#a855f7">AI 분석 리포트</SectionTitle>
        <AIReportCard t={t} lang="ko" region={alert.region} />
      </div>

      <style jsx>{`
        .close-btn { background: rgba(148,163,184,0.08); border: 1px solid #2a3a55; color: #cbd5e1; border-radius: 9px; padding: 7px 14px; cursor: pointer; font-size: 13px; transition: all .15s ease; }
        .close-btn:hover { background: rgba(148,163,184,0.18); border-color: #3b4d6b; }
        .calc-box { background: linear-gradient(150deg, #0f1b30, #0a1322); border: 1px solid; border-radius: 16px; padding: 18px; box-shadow: 0 8px 30px rgba(0,0,0,0.35); }
        .panel-card { background: linear-gradient(150deg, #0e1729, #0a1120); border: 1px solid #1a2740; border-radius: 16px; padding: 18px; }
      `}</style>
    </div>
  );
}

export default function KioskPage() {
  const { data, isLoading, isError } = useRegionAlerts();
  const alerts = data?.alerts ?? [];
  const [selectedCode, setSelectedCode] = useState<RegionCode | null>(null);
  const [clock, setClock] = useState("");

  useEffect(() => {
    // 키오스크 다크 테마: 콘텐츠가 viewport보다 길 때 body 흰 배경이 비치는 것 방지
    const prevBody = document.body.style.background;
    const prevHtml = document.documentElement.style.background;
    document.body.style.background = "#030712";
    document.documentElement.style.background = "#030712";
    return () => {
      document.body.style.background = prevBody;
      document.documentElement.style.background = prevHtml;
    };
  }, []);

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString("ko-KR"));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const districts = buildDistricts(alerts);
  const selectedAlert = selectedCode
    ? alerts.find((a) => regionCodeFromName(a.region) === selectedCode) ?? null
    : null;

  const sorted = [...alerts].sort((a, b) => b.composite - a.composite);
  const activeCount = alerts.filter((a) => a.alert_level !== "GREEN").length;
  const atRiskCount = alerts.filter((a) => a.composite >= 55).length;
  const top = sorted[0];
  const latest = alerts.map((a) => a.latest_time).filter(Boolean).sort().pop();
  const maxComposite = top?.composite ?? 100;

  const summary: Array<[string, string | number, string]> = [
    ["활성 경보", activeCount, "#f59e0b"],
    ["위험 지역", atRiskCount, "#ef4444"],
    ["최고 위험도", top?.composite?.toFixed(1) ?? "—", "#38bdf8"],
  ];

  return (
    <div className="kiosk-root">
      <header className="kiosk-header">
        <span className="header-bar" />
        <div style={{ display: "flex", flexDirection: "column" }}>
          <h1 style={{ fontSize: 25, fontWeight: 800, margin: 0, letterSpacing: "-0.02em" }}>도시 면역 시스템</h1>
          <span style={{ fontSize: 13, opacity: 0.6, marginTop: 2 }}>전국 감염병 조기경보 · 3계층 비의료 신호 융합</span>
        </div>
        <span className="live-badge" style={isError ? { color: "#f87171", borderColor: "rgba(248,113,113,0.35)", background: "rgba(248,113,113,0.08)" } : undefined}><span className="live-dot" style={isError ? { background: "#f87171" } : undefined} /> {isError ? "연결 실패" : isLoading ? "연결 중" : "LIVE"}</span>
        <span style={{ marginLeft: "auto", textAlign: "right", fontFamily: "var(--font-mono)" }}>
          <span style={{ display: "block", fontSize: 22, fontWeight: 700, letterSpacing: "0.02em" }}>{clock}</span>
          <span style={{ display: "block", fontSize: 12, opacity: 0.55 }}>데이터 {latest?.slice(0, 10) ?? "—"} · 60초 자동 갱신</span>
        </span>
      </header>

      <div className="kiosk-body">
        <div className="map-panel">
          <KoreaMap data={districts} lang="ko" selected={selectedCode ?? undefined} onSelect={(c) => setSelectedCode(c)} size={640} showLabels />
          <div className="legend">
            {([["정상", "safe"], ["주의", "caution"], ["경보", "warning"], ["위기", "alert"]] as const).map(([lbl, tok]) => (
              <span key={tok} className="legend-chip">
                <span style={{ width: 12, height: 12, borderRadius: 3, background: `var(--risk-${tok})` }} /> {lbl}
              </span>
            ))}
          </div>
        </div>

        <div className="side-panel">
          {selectedAlert ? (
            <RegionDrilldown alert={selectedAlert} onClose={() => setSelectedCode(null)} />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 18, height: "100%" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
                {summary.map(([lbl, val, c]) => (
                  <div key={lbl} className="kpi-card" style={{ borderTopColor: c }}>
                    <div style={{ fontSize: 44, fontWeight: 800, color: c, lineHeight: 1, fontFamily: "var(--font-mono)" }}>{val}</div>
                    <div style={{ fontSize: 12.5, opacity: 0.65, marginTop: 8 }}>{lbl}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 13, opacity: 0.55, display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 15 }}>👆</span> 지역을 클릭하면 수집 데이터 · 위험도 계산 · AI 리포트를 볼 수 있습니다
              </div>
              <div style={{ flex: 1, overflowY: "auto" }}>
                <SectionTitle accent="#38bdf8">위험도 순위 (17개 시·도)</SectionTitle>
                {sorted.length === 0 && (
                  <div style={{ padding: 24, textAlign: "center", opacity: 0.7, fontSize: 14 }}>
                    {isError ? "⚠ 데이터 연결 실패 — 백엔드 점검 필요" : "데이터 로딩 중…"}
                  </div>
                )}
                {sorted.map((a, i) => {
                  const tok = TOKENS[LEVEL_TO_RISK[a.alert_level]];
                  const pct = Math.max(4, Math.round((a.composite / maxComposite) * 100));
                  return (
                    <button key={a.region} className="rank-row" onClick={() => { const code = regionCodeFromName(a.region); if (code) setSelectedCode(code); }}>
                      <span className="rank-fill" style={{ width: `${pct}%`, background: `var(--risk-${tok})` }} />
                      <span style={{ position: "relative", width: 22, fontFamily: "var(--font-mono)", fontSize: 12, opacity: 0.5 }}>{i + 1}</span>
                      <span style={{ position: "relative", width: 11, height: 11, borderRadius: "50%", background: `var(--risk-${tok})`, flexShrink: 0 }} />
                      <span style={{ position: "relative", flex: 1, fontWeight: 600 }}>{a.region}</span>
                      <span style={{ position: "relative", fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 15 }}>{a.composite.toFixed(1)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .kiosk-root { min-height: 100vh; background: radial-gradient(ellipse at top, #0c1733 0%, #030712 55%); color: #e2e8f0; padding: 22px 30px; font-family: var(--font-sans); }
        .kiosk-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #16243f; }
        .header-bar { width: 5px; height: 44px; border-radius: 3px; background: linear-gradient(180deg, #38bdf8, #6366f1); box-shadow: 0 0 16px rgba(56,189,248,0.5); }
        .live-badge { display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700; letter-spacing: 0.05em; color: #34d399; padding: 4px 10px; border: 1px solid rgba(52,211,153,0.3); border-radius: 999px; background: rgba(52,211,153,0.08); }
        .live-dot { width: 8px; height: 8px; border-radius: 50%; background: #34d399; animation: uis-pulse 1.6s ease-in-out infinite; }
        .kiosk-body { display: grid; grid-template-columns: 1.4fr 1fr; gap: 22px; height: calc(100vh - 108px); }
        .map-panel { display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(ellipse at center, #0b1426 0%, #070d1c 100%); border: 1px solid #16243f; border-radius: 20px; padding: 18px; box-shadow: inset 0 0 60px rgba(0,0,0,0.4); }
        .legend { display: flex; gap: 18px; margin-top: 16px; font-size: 13px; }
        .legend-chip { display: flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; background: rgba(148,163,184,0.07); border: 1px solid #1a2740; }
        .side-panel { background: linear-gradient(160deg, #0c1628, #080f1e); border: 1px solid #16243f; border-radius: 20px; padding: 22px; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.4); }
        .kpi-card { background: linear-gradient(160deg, #101d33, #0a1322); border: 1px solid #1a2740; border-top: 3px solid; border-radius: 14px; padding: 18px 16px; text-align: center; transition: transform .15s ease, box-shadow .15s ease; }
        .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
        .rank-row { position: relative; display: flex; align-items: center; gap: 11px; width: 100%; background: transparent; border: none; border-bottom: 1px solid #14223c; padding: 11px 6px; cursor: pointer; color: #e2e8f0; text-align: left; overflow: hidden; transition: background .15s ease; }
        .rank-row:hover { background: rgba(56,189,248,0.06); }
        .rank-fill { position: absolute; left: 0; top: 0; bottom: 0; opacity: 0.1; border-radius: 0 6px 6px 0; transition: width .5s ease; }
      `}</style>
    </div>
  );
}
