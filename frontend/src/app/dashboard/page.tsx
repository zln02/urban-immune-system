"use client";

import { useState, type CSSProperties } from "react";
import { I } from "@/components/ui/icons";
import { Panel } from "@/components/ui/panel";
import { RiskPill } from "@/components/ui/risk-pill";
import { KoreaMap } from "@/components/map/korea-map";
import { TrendChart } from "@/components/charts/trend-chart";
import { AlertBanner } from "@/components/alert/alert-banner";
import { KpiCard } from "@/components/alert/kpi-card";
import { LayerCard } from "@/components/alert/layer-card";
import { AIReportCard } from "@/components/alert/ai-report-card";
import { AlertTable } from "@/components/alert/alert-table";
import { AnomalyPanel } from "@/components/anomaly/anomaly-panel";

import { KOREA_REGIONS, regionName, regionCodeFromName, type RegionCode } from "@/lib/korea-regions";
import { RISK_META } from "@/lib/risk";
import { DICT, type Lang } from "@/lib/i18n";
import { mockAlerts, mockDistricts, mockSeries, type DistrictData } from "@/lib/mock-data";
import { useOtcTrend, useSearchTrend } from "@/hooks/useNaverTrend";
import { useWastewaterSeries } from "@/hooks/useSignalTimeseries";
import { useRegionAlerts, type RegionAlert } from "@/hooks/useRegionAlerts";
import { useLeadTime, useBacktest17 } from "@/hooks/useAnalysisStats";

// alert_level → 1~4 매핑 (legend·map 색칠 통일)
const LEVEL_TO_RISK: Record<string, 1 | 2 | 3 | 4> = {
  GREEN: 1,
  YELLOW: 2,
  ORANGE: 3,
  RED: 4,
};

function buildDistrictsFromAlerts(alerts: RegionAlert[]): Record<RegionCode, DistrictData> {
  // 기본값: mockDistricts 구조를 시작점으로 (모든 17지역 키 보장)
  const out: Record<RegionCode, DistrictData> = { ...mockDistricts };
  for (const a of alerts) {
    const code = regionCodeFromName(a.region);
    if (!code) continue;
    const risk = LEVEL_TO_RISK[a.alert_level] ?? 1;
    // composite (0~100) 를 cases 칸에 정수로 표시 — 실 confirmed_cases 미연결 (Phase 3)
    out[code] = {
      risk,
      cases: Math.round(a.composite * 10),
      change: Math.round((a.l1 + a.l2 + a.l3) / 3 - 30),
    };
  }
  return out;
}

type DashTab = "surveillance" | "anomaly";

/**
 * Urban Immune System — Conservative Dashboard Home
 *
 * Claude Design handoff (2026-04-22, k6f2hag...) Conservative 변형.
 * 전국 17개 시도 · 전라 권역 L4 경보 시나리오.
 * 캡스톤 중간발표 Golden Path: Alert Banner → AI Report → PDF.
 *
 * Layout:
 *   ┌─────────── top bar (navy) ───────────┐
 *   │rail│sidebar│  hero alert banner      │
 *   │    │       │  KPI × 4                │
 *   │    │       │  Map | 3-Layer cards    │
 *   │    │       │  Trend chart (hero)     │
 *   │    │       │  AI report | Alerts     │
 *   └────┴───────┴─────────────────────────┘
 */
export default function DashboardPage() {
  const [lang, setLang] = useState<Lang>("ko");
  const [selected, setSelected] = useState<RegionCode>("JB");
  const [activeTab, setActiveTab] = useState<DashTab>("surveillance");

  const t = DICT[lang];
  const regionAlertsQuery = useRegionAlerts(28);
  const realAlerts = regionAlertsQuery.data?.alerts ?? [];
  const districts = realAlerts.length > 0 ? buildDistrictsFromAlerts(realAlerts) : mockDistricts;
  const atRiskCount = Object.values(districts).filter((d) => d.risk >= 3).length;
  // AlertBanner / KpiCard 는 기존 mockAlerts 유지 (AlertRecord 타입)
  const activeAlerts = mockAlerts;
  // AlertTable 만 실데이터 (RegionAlert 타입) 분리
  const tableAlerts: typeof mockAlerts | NonNullable<typeof regionAlertsQuery.data>["alerts"] =
    realAlerts.length > 0 ? realAlerts : mockAlerts;

  const layerColor = {
    pharmacy: "var(--layer-pharmacy)",
    sewage: "var(--layer-sewage)",
    search: "var(--layer-search)",
  };

  const selectedInfo = districts[selected];

  // ── Naver 실데이터 (L1 OTC / L3 검색어) ──────────────────────────
  const otcQuery = useOtcTrend(12);
  const searchQuery = useSearchTrend(12);
  // ── L2 KOWAS 하수 실데이터 (TimescaleDB 952건 → /signals/timeseries) ─
  const sewageQuery = useWastewaterSeries("서울특별시", 365);
  // ── 분석 산출물 (lead time / backtest 17지역) ───────────────────
  const leadTimeQuery = useLeadTime();
  const backtestQuery = useBacktest17();

  const toSparkValues = (values: number[], scale = 100) =>
    values.map((v) => v * scale);

  const calcChange = (values: number[]) => {
    if (values.length < 2) return 0;
    const prev = values[values.length - 2];
    const curr = values[values.length - 1];
    return prev === 0 ? 0 : ((curr - prev) / prev) * 100;
  };

  const otcSeries = otcQuery.data?.series ?? [];
  const searchSeries = searchQuery.data?.series ?? [];
  const sewageSeries = sewageQuery.data?.data ?? [];
  const hasOtc = otcSeries.length > 0;
  const hasSearch = searchSeries.length > 0;
  const hasSewage = sewageSeries.length > 0;

  const otcValues = hasOtc ? toSparkValues(otcSeries.map((p) => p.value)) : mockSeries.pharmacy;
  const otcLatest = hasOtc ? otcValues[otcValues.length - 1] : mockSeries.pharmacy[mockSeries.pharmacy.length - 1];
  const otcChange = hasOtc ? calcChange(otcValues) : 0;

  const searchValues = hasSearch ? toSparkValues(searchSeries.map((p) => p.value)) : mockSeries.search;
  const searchLatest = hasSearch ? searchValues[searchValues.length - 1] : mockSeries.search[mockSeries.search.length - 1];
  const searchChange = hasSearch ? calcChange(searchValues) : 0;

  // KOWAS는 이미 0-100 정규화 완료, scale 1.0
  const sewageValues = hasSewage ? sewageSeries.map((p) => p.value) : mockSeries.sewage;
  const sewageLatest = hasSewage ? sewageValues[sewageValues.length - 1] : mockSeries.sewage[mockSeries.sewage.length - 1];

  const dataSourceLabel = hasOtc || hasSearch || hasSewage ? "실시간 · Naver + KOWAS 연결" : "시뮬레이션 데이터";

  // ── KPI 실값 (lead_time_summary / backtest_17regions) ─────────────
  const leadWeeksComposite = leadTimeQuery.data?.signal_lead_weeks.composite;
  const leadDaysDisplay = leadWeeksComposite !== undefined ? (leadWeeksComposite * 7).toFixed(1) : null;
  const ccfComposite = leadTimeQuery.data?.ccf_max.composite;
  const grangerP = leadTimeQuery.data?.granger_p;
  const backtestRecall = backtestQuery.data?.summary.mean_recall;
  const backtestF1 = backtestQuery.data?.summary.mean_f1;

  return (
    <div
      style={{
        width: "100%",
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "var(--rail-w) var(--sidebar-w) 1fr",
        gridTemplateRows: "var(--header-h) 1fr",
        background: "var(--bg-sub)",
        color: "var(--text)",
        fontFamily: "var(--font-sans)",
      }}
    >
      {/* ── Top bar ────────────────────────────────────────── */}
      <header
        style={{
          gridColumn: "1 / -1",
          display: "grid",
          gridTemplateColumns: "var(--rail-w) var(--sidebar-w) 1fr auto",
          background: "var(--primary-70)",
          color: "var(--gray-0)",
          borderBottom: "1px solid var(--primary-90)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <I.Grid size={20} stroke="var(--gray-0)" />
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "0 16px",
            borderRight: "1px solid var(--primary-90)",
          }}
        >
          <div
            style={{
              width: 24,
              height: 24,
              background: "var(--gray-0)",
              color: "var(--primary-70)",
              display: "grid",
              placeItems: "center",
              fontWeight: 700,
              fontSize: 11,
              letterSpacing: 0.5,
            }}
          >
            UIS
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: 0.1 }}>
              {t.brand}
            </div>
            <div style={{ fontSize: 10, opacity: 0.7 }}>
              KDCA · {t.nav_dashboard}
            </div>
          </div>
        </div>
        <nav
          style={{
            display: "flex",
            alignItems: "center",
            paddingLeft: 16,
            gap: 4,
            fontSize: 13,
          }}
        >
          {[
            { label: t.nav_dashboard, tab: "surveillance" as DashTab },
            { label: lang === "ko" ? "🧬 팬데믹 조기탐지" : "🧬 Pandemic Detection", tab: "anomaly" as DashTab },
          ].map(({ label, tab }) => {
            const isActive = tab ? activeTab === tab : false;
            return (
              <button
                key={label}
                type="button"
                onClick={() => tab && setActiveTab(tab)}
                style={{
                  height: "100%",
                  padding: "0 14px",
                  background: isActive ? "var(--primary-90)" : "transparent",
                  color: "var(--gray-0)",
                  border: "none",
                  cursor: "pointer",
                  borderBottom: isActive ? "2px solid var(--gray-0)" : "2px solid transparent",
                  fontWeight: isActive ? 600 : 400,
                }}
              >
                {label}
              </button>
            );
          })}
        </nav>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            paddingRight: 12,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 11,
              opacity: 0.85,
              marginRight: 12,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: hasOtc || hasSearch ? "var(--risk-safe)" : "var(--risk-caution)",
                animation: "uis-blink 2s infinite",
              }}
            />
            <span>{dataSourceLabel} · {hasOtc || hasSearch ? "실시간" : t.header_sync}</span>
          </div>
          <button
            type="button"
            aria-label={lang === "en" ? "Toggle language" : "언어 전환"}
            onClick={() => setLang(lang === "ko" ? "en" : "ko")}
            style={iconBtnDark}
          >
            <span style={{ fontSize: 11, fontWeight: 700 }}>{lang.toUpperCase()}</span>
          </button>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              paddingLeft: 12,
              borderLeft: "1px solid var(--primary-90)",
              height: 24,
            }}
          >
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: "50%",
                background: "var(--primary-30)",
                display: "grid",
                placeItems: "center",
                fontSize: 10,
                fontWeight: 600,
              }}
            >
              JP
            </div>
            <div style={{ fontSize: 11 }}>
              <div style={{ fontWeight: 600 }}>{t.user}</div>
              <div style={{ opacity: 0.7, fontSize: 10 }}>
                {t.role.split("·")[1]?.trim()}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ── Rail ─────────────────────────────────────────── */}
      <aside
        style={{
          background: "var(--surface)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "12px 0",
          gap: 4,
        }}
      >
        <button
          type="button"
          aria-current="page"
          style={{
            width: 36,
            height: 36,
            background: "var(--primary-70)",
            color: "var(--gray-0)",
            border: "none",
            display: "grid",
            placeItems: "center",
            cursor: "default",
          }}
        >
          <I.Home size={18} stroke="currentColor" />
        </button>
      </aside>

      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside
        style={{
          background: "var(--surface)",
          borderRight: "1px solid var(--border)",
          padding: "var(--sp-4)",
          display: "flex",
          flexDirection: "column",
          gap: "var(--sp-5)",
          overflow: "hidden",
        }}
      >
        <div>
          <div className="t-label-01" style={sidebarLabel}>
            {lang === "en" ? "Filter" : "필터"}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <FieldRow label={lang === "en" ? "Time window" : "기간 (Phase 2)"}>
              <select
                style={{ ...selectStyle, opacity: 0.5, cursor: "not-allowed" }}
                disabled
                defaultValue="60d"
              >
                <option value="60d">{lang === "en" ? "Last 60 days" : "최근 60일"}</option>
              </select>
            </FieldRow>
            <FieldRow label={lang === "en" ? "Region" : "권역"}>
              <select
                style={selectStyle}
                value={selected}
                onChange={(e) => setSelected(e.target.value as RegionCode)}
              >
                {KOREA_REGIONS.map((d) => (
                  <option key={d.code} value={d.code}>
                    {regionName(d.code, lang)}
                  </option>
                ))}
              </select>
            </FieldRow>
            <FieldRow label={lang === "en" ? "Disease (Phase 2)" : "질병 (Phase 2)"}>
              <select
                style={{ ...selectStyle, opacity: 0.5, cursor: "not-allowed" }}
                disabled
                defaultValue="flu"
              >
                <option value="flu">
                  {lang === "en" ? "Influenza" : "인플루엔자"}
                </option>
              </select>
            </FieldRow>
          </div>
        </div>

        <div>
          <div className="t-label-01" style={sidebarLabel}>
            {lang === "en" ? "Active signal layers" : "활성 신호 레이어"}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {[
              { key: "pharmacy", label: t.layer_pharmacy, sub: t.layer_pharmacy_sub, c: layerColor.pharmacy },
              { key: "sewage", label: t.layer_sewage, sub: t.layer_sewage_sub, c: layerColor.sewage },
              { key: "search", label: t.layer_search, sub: t.layer_search_sub, c: layerColor.search },
            ].map((l) => (
              <div
                key={l.key}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: 8,
                  background: "var(--bg-sub)",
                }}
              >
                <span style={{ width: 3, height: 18, background: l.c }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 500 }}>{l.label}</div>
                  <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{l.sub}</div>
                </div>
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 600,
                    color: "var(--risk-safe)",
                    letterSpacing: 0.4,
                  }}
                >
                  ON
                </span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="t-label-01" style={sidebarLabel}>
            {lang === "en" ? "Alert thresholds (fixed)" : "경보 임계값 (고정)"}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.6 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>YELLOW</span>
              <span style={{ fontWeight: 600, color: "var(--text)" }}>composite ≥ 30</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>ORANGE</span>
              <span style={{ fontWeight: 600, color: "var(--text)" }}>≥ 55</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>RED</span>
              <span style={{ fontWeight: 600, color: "var(--text)" }}>≥ 75</span>
            </div>
          </div>
          <div
            style={{
              marginTop: 8,
              fontSize: 10,
              color: "var(--text-tertiary)",
              lineHeight: 1.4,
            }}
          >
            {t.trigger}
          </div>
        </div>

        <div
          style={{
            marginTop: "auto",
            padding: 12,
            background: "var(--bg-sub)",
            fontSize: 10,
            color: "var(--text-tertiary)",
            lineHeight: 1.5,
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
            {lang === "en" ? "Compliance" : "준법"}
          </div>
          WCAG 2.2 AA · KWCAG 2.2
          <br />
          ISMS-P · KRDS 2024
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────── */}
      <main
        style={{
          padding: "var(--sp-5) var(--sp-6)",
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "var(--sp-5)",
        }}
      >
        {/* ── 팬데믹 조기탐지 탭 ───────────────────────── */}
        {activeTab === "anomaly" && (
          <AnomalyPanel lang={lang} />
        )}

        {/* ── 감시 현황 탭 ─────────────────────────────── */}
        {activeTab === "surveillance" && (<>
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 11,
              color: "var(--text-tertiary)",
              marginBottom: 6,
            }}
          >
            <span>KDCA</span>
            <span>/</span>
            <span>{t.nav_dashboard}</span>
            <span>/</span>
            <span style={{ color: "var(--text-secondary)" }}>
              {lang === "en" ? "Nationwide overview" : "전국 현황"}
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "space-between",
              gap: 16,
            }}
          >
            <div>
              <h1 className="t-h-04" style={{ margin: 0, fontWeight: 400 }}>
                {lang === "en" ? "Surveillance overview" : "감시 현황 개요"}
              </h1>
              <div
                style={{
                  fontSize: 13,
                  color: "var(--text-secondary)",
                  marginTop: 4,
                }}
              >
                {t.header_status} · 2026-04-28 09:28 KST · Δ 7d vs baseline
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                onClick={async () => {
                  const url = `/api/v1/alerts/report-pdf?region=${encodeURIComponent(regionName(selected, "ko"))}`;
                  const res = await fetch(url, { cache: "no-store" });
                  if (!res.ok) {
                    alert(lang === "ko" ? "PDF 생성 실패" : "PDF failed");
                    return;
                  }
                  const blob = await res.blob();
                  const a = document.createElement("a");
                  const obj = URL.createObjectURL(blob);
                  a.href = obj;
                  a.download = `UIS_alert_${regionName(selected, "ko")}_${new Date().toISOString().slice(0,10)}.pdf`;
                  a.click();
                  URL.revokeObjectURL(obj);
                }}
                title={lang === "en" ? "Download PDF report" : "PDF 리포트 다운로드"}
                style={btnPrimary}
              >
                <I.Print size={14} /> {lang === "en" ? "Download PDF" : "PDF 리포트"}
              </button>
            </div>
          </div>
        </div>

        <AlertBanner alerts={activeAlerts} t={t} lang={lang} confidence={0.93} />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "var(--sp-4)",
          }}
        >
          <KpiCard
            label={t.kpi_alerts}
            value={activeAlerts.length}
            delta={`+${activeAlerts.filter((a) => a.level === 4).length} L4`}
            tone="alert"
          />
          <KpiCard
            label={t.kpi_at_risk}
            value={atRiskCount}
            total={17}
            delta={lang === "en" ? "of 17" : "/17"}
            tone={atRiskCount > 3 ? "warning" : "caution"}
          />
          <KpiCard
            label={t.kpi_lead}
            value={leadDaysDisplay ?? "—"}
            unit={lang === "en" ? "days" : "일"}
            delta={leadWeeksComposite !== undefined
              ? `composite ${leadWeeksComposite}주 (KCDC peak 대비)`
              : (lang === "en" ? "loading…" : "로딩 중")}
            tone="safe"
            sparkData={otcValues.slice(-20)}
            sparkColor="var(--layer-pharmacy)"
          />
          <KpiCard
            label={lang === "en" ? "Backtest F1" : "백테스트 F1"}
            value={backtestF1 !== undefined ? backtestF1.toFixed(3) : "—"}
            delta={backtestRecall !== undefined
              ? `Recall ${backtestRecall.toFixed(3)} · 17지역`
              : (lang === "en" ? "loading…" : "로딩 중")}
            tone={backtestF1 !== undefined && backtestF1 >= 0.65 ? "safe" : "caution"}
            sparkData={sewageValues.slice(-20)}
            sparkColor="var(--layer-sewage)"
          />
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.45fr 1fr",
            gap: "var(--sp-4)",
          }}
        >
          <Panel
            title={t.map_title}
            sub={t.map_sub}
            actions={
              <div style={{ display: "flex", gap: 4 }}>
                <button type="button" style={tabBtn(true)}>
                  L4-L1
                </button>
                <button
                  type="button"
                  disabled
                  title={lang === "en" ? "Phase 2" : "Phase 2 예정"}
                  style={{ ...tabBtn(false), opacity: 0.4, cursor: "not-allowed" }}
                >
                  {lang === "en" ? "Cases" : "건수"}
                </button>
                <button
                  type="button"
                  disabled
                  title={lang === "en" ? "Phase 2" : "Phase 2 예정"}
                  style={{ ...tabBtn(false), opacity: 0.4, cursor: "not-allowed" }}
                >
                  Δ 7d
                </button>
              </div>
            }
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 200px",
                gap: 16,
                alignItems: "stretch",
              }}
            >
              <KoreaMap
                data={districts}
                lang={lang}
                selected={selected}
                onSelect={setSelected}
                size={520}
              />
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  borderLeft: "1px solid var(--border)",
                  paddingLeft: 16,
                }}
              >
                <div className="t-label-01" style={sidebarLabel}>
                  {lang === "en" ? "Legend" : "범례"}
                </div>
                {([4, 3, 2, 1] as const).map((level) => {
                  const meta = RISK_META[level];
                  const count = Object.values(districts).filter(
                    (x) => x.risk === level,
                  ).length;
                  return (
                    <div
                      key={level}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        fontSize: 12,
                        padding: "4px 0",
                      }}
                    >
                      <span
                        style={{
                          width: 14,
                          height: 14,
                          background: `var(--risk-${meta.token})`,
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#fff",
                          fontSize: 9,
                          fontWeight: 700,
                          backgroundImage: meta.hatch
                            ? "repeating-linear-gradient(45deg, transparent 0 3px, rgba(0,0,0,0.25) 3px 4px)"
                            : "none",
                        }}
                      >
                        {meta.icon}
                      </span>
                      <span style={{ flex: 1, fontWeight: 500 }}>
                        L{level} · {meta.label[lang]}
                      </span>
                      <span className="t-num-sm" style={{ color: "var(--text-tertiary)" }}>
                        {count}
                      </span>
                    </div>
                  );
                })}
                <div
                  style={{
                    marginTop: 12,
                    padding: 10,
                    background: "var(--bg-sub)",
                    fontSize: 11,
                    color: "var(--text-secondary)",
                    lineHeight: 1.5,
                  }}
                >
                  <div
                    style={{
                      fontWeight: 600,
                      color: "var(--text)",
                      marginBottom: 4,
                    }}
                  >
                    {regionName(selected, lang)}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>{lang === "en" ? "Level" : "단계"}</span>
                    <RiskPill level={selectedInfo.risk} lang={lang} />
                  </div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginTop: 4,
                    }}
                  >
                    <span>{lang === "en" ? "Cases" : "건수"}</span>
                    <span className="t-num-sm">{selectedInfo.cases}</span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginTop: 4,
                    }}
                  >
                    <span>Δ 7d</span>
                    <span
                      className="t-num-sm"
                      style={{ color: "var(--risk-warning)" }}
                    >
                      +{selectedInfo.change}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </Panel>

          <div
            style={{ display: "flex", flexDirection: "column", gap: "var(--sp-4)" }}
          >
            <LayerCard
              title={t.layer_pharmacy}
              sub={hasOtc ? "Naver 쇼핑인사이트 실시간" : t.layer_pharmacy_sub}
              data={otcValues.slice(-30)}
              value={otcLatest}
              change={otcChange}
              color="var(--layer-pharmacy)"
              icon={<I.Pharmacy size={14} />}
            />
            <LayerCard
              title={t.layer_sewage}
              sub={hasSewage ? "질병관리청 KOWAS 자동 수집 (952건)" : t.layer_sewage_sub}
              data={sewageValues.slice(-30)}
              value={sewageLatest}
              change={hasSewage ? calcChange(sewageValues) : 22.8}
              color="var(--layer-sewage)"
              icon={<I.Water size={14} />}
            />
            <LayerCard
              title={t.layer_search}
              sub={hasSearch ? "Naver 데이터랩 실시간" : t.layer_search_sub}
              data={searchValues.slice(-30)}
              value={searchLatest}
              change={searchChange}
              color="var(--layer-search)"
              icon={<I.Search size={14} />}
            />
          </div>
        </div>

        <Panel
          title={t.trend_title}
          sub={t.trend_sub}
          actions={
            <div style={{ display: "flex", gap: 4 }}>
              {["7d", "30d", "60d", lang === "en" ? "All" : "전체"].map((lbl, i) => {
                const active = i === 2;
                return (
                  <button
                    key={lbl}
                    type="button"
                    disabled={!active}
                    title={active ? "" : (lang === "en" ? "Phase 2" : "Phase 2 예정")}
                    style={{
                      ...tabBtn(active),
                      opacity: active ? 1 : 0.4,
                      cursor: active ? "default" : "not-allowed",
                    }}
                  >
                    {lbl}
                  </button>
                );
              })}
            </div>
          }
        >
          <TrendChart
            series={{
              pharmacy: hasOtc ? otcValues.slice(-60) : mockSeries.pharmacy,
              sewage: hasSewage ? sewageValues.slice(-60) : mockSeries.sewage,
              search: hasSearch ? searchValues.slice(-60) : mockSeries.search,
            }}
            t={t}
            height={280}
          />
          <div
            style={{
              marginTop: 12,
              padding: "10px 12px",
              background: "var(--bg-sub)",
              fontSize: 12,
              color: "var(--text-secondary)",
              display: "flex",
              gap: 16,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <span style={{ fontWeight: 600, color: "var(--text)" }}>{t.granger}</span>
            {grangerP ? (
              <>
                <span>
                  OTC → {lang === "en" ? "Clinical" : "임상"}: p = {grangerP.l1_otc.toFixed(3)} (lead {leadTimeQuery.data?.signal_lead_weeks.l1_otc}주)
                </span>
                <span style={{ color: "var(--border-strong)" }}>|</span>
                <span>
                  {lang === "en" ? "Sewage" : "하수"} → p = {grangerP.l2_wastewater.toFixed(3)} (lead {leadTimeQuery.data?.signal_lead_weeks.l2_wastewater}주)
                </span>
                <span style={{ color: "var(--border-strong)" }}>|</span>
                <span>
                  {lang === "en" ? "Search" : "검색"} → p = {grangerP.l3_search.toFixed(3)} (lead {leadTimeQuery.data?.signal_lead_weeks.l3_search}주)
                </span>
                {ccfComposite !== undefined && (
                  <>
                    <span style={{ color: "var(--border-strong)" }}>|</span>
                    <span>CCF (composite) = {ccfComposite.toFixed(3)}</span>
                  </>
                )}
              </>
            ) : (
              <span>{lang === "en" ? "loading…" : "분석 산출물 로딩 중"}</span>
            )}
          </div>
        </Panel>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.3fr 1fr",
            gap: "var(--sp-4)",
          }}
        >
          <AIReportCard t={t} lang={lang} region={regionName(selected, "ko")} />
          <AlertTable alerts={tableAlerts} t={t} lang={lang} />
        </div>

        <footer
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "var(--text-tertiary)",
            padding: "8px 0",
            borderTop: "1px solid var(--border)",
            marginTop: 8,
          }}
        >
          {t.footer} · WCAG 2.2 AA · ISMS-P
        </footer>
        </>)}
      </main>
    </div>
  );
}

/* ── 공통 style tokens (페이지 전용) ─────────────────────── */

const sidebarLabel: CSSProperties = {
  color: "var(--text-tertiary)",
  textTransform: "uppercase",
  letterSpacing: 0.48,
  marginBottom: 8,
};

const selectStyle: CSSProperties = {
  width: "100%",
  padding: "6px 10px",
  fontSize: 12,
  fontFamily: "inherit",
  background: "var(--bg-sub)",
  border: "none",
  borderBottom: "1px solid var(--text-tertiary)",
  color: "var(--text)",
  cursor: "pointer",
};

const iconBtnDark: CSSProperties = {
  width: 40,
  height: 40,
  background: "transparent",
  border: "none",
  color: "var(--gray-0)",
  cursor: "pointer",
  display: "grid",
  placeItems: "center",
  position: "relative",
};

const btnGhost: CSSProperties = {
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
};

const btnPrimary: CSSProperties = {
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
};

function tabBtn(active: boolean): CSSProperties {
  return {
    padding: "4px 10px",
    fontSize: 11,
    fontWeight: 500,
    fontFamily: "inherit",
    background: active ? "var(--primary-70)" : "transparent",
    color: active ? "var(--gray-0)" : "var(--text-secondary)",
    border: `1px solid ${active ? "var(--primary-70)" : "var(--border-strong)"}`,
    cursor: "pointer",
  };
}

function FieldRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span className="t-label-02" style={{ color: "var(--text-secondary)" }}>
        {label}
      </span>
      {children}
    </label>
  );
}
