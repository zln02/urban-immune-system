"use client";

import { Panel } from "@/components/ui/panel";
import { useLeadTime, useBacktest17, useTftRegression } from "@/hooks/useAnalysisStats";
import type { Lang } from "@/lib/i18n";

interface Metric {
  label: string;
  value: string;
  unit?: string;
  ok: boolean | null;
  note?: string;
}

interface Axis {
  title: string;
  subtitle: string;
  color: string;
  metrics: Metric[];
}

function MetricRow({ m }: { m: Metric }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        padding: "6px 0",
        borderBottom: "1px dashed var(--border)",
        gap: 12,
      }}
    >
      <div style={{ flexShrink: 0 }}>
        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{m.label}</div>
        {m.note && (
          <div style={{ fontSize: 9, color: "var(--text-tertiary)", marginTop: 1 }}>
            {m.note}
          </div>
        )}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span
          style={{
            fontSize: 18,
            fontWeight: 600,
            fontFamily: "var(--font-mono)",
            color: m.ok === false ? "var(--risk-warning)" : "var(--text)",
          }}
        >
          {m.value}
        </span>
        {m.unit && (
          <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{m.unit}</span>
        )}
      </div>
    </div>
  );
}

function AxisCard({ axis }: { axis: Axis }) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderTop: `3px solid ${axis.color}`,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div className="t-label-01" style={{ color: "var(--text)", fontWeight: 600 }}>
        {axis.title}
      </div>
      <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginBottom: 6 }}>
        {axis.subtitle}
      </div>
      {axis.metrics.map((m) => (
        <MetricRow key={m.label} m={m} />
      ))}
    </div>
  );
}

export function ValidationMatrixPanel({ lang }: { lang: Lang }) {
  const lt = useLeadTime();
  const bt = useBacktest17();
  const tft = useTftRegression();

  const bs = bt.data?.summary;
  // 17지역 walk-forward 평균 lead (6.76주) 우선, lead_time_summary(서울 단독)는 폴백
  const leadFromBacktest = bs?.mean_lead_weeks;
  const leadFromLT = lt.data?.signal_lead_weeks?.composite;
  const lead = leadFromBacktest ?? leadFromLT;
  const leadSource = leadFromBacktest !== undefined ? "17regions" : "seoul";
  const prodEval = tft.data?.evaluations?.prod_20260504;
  const h1 = prodEval?.by_horizon?.horizon_1week;
  const h2 = prodEval?.by_horizon?.horizon_2week;

  const fmt = (v: number | null | undefined, digits = 3) =>
    v === undefined || v === null ? "—" : v.toFixed(digits);

  const axes: Axis[] = [
    {
      title: lang === "ko" ? "① 분류 검증 (경보 Y/N)" : "① Classification (alert Y/N)",
      subtitle: lang === "ko" ? "17지역 walk-forward · gate 4주" : "17 regions · gap 4w",
      color: "var(--risk-safe)",
      metrics: [
        {
          label: "F1",
          value: fmt(bs?.mean_f1, 3),
          ok: bs ? bs.mean_f1 >= 0.8 : null,
          note: lang === "ko" ? "목표 ≥0.80" : "target ≥0.80",
        },
        {
          label: "Recall",
          value: fmt(bs?.mean_recall, 3),
          ok: bs ? bs.mean_recall >= 0.85 : null,
          note: lang === "ko" ? "목표 ≥0.85" : "target ≥0.85",
        },
        {
          label: "Precision",
          value: fmt(bs?.mean_precision, 3),
          ok: bs ? bs.mean_precision >= 0.9 : null,
          note: lang === "ko" ? "목표 ≥0.90" : "target ≥0.90",
        },
        {
          label: "FAR (gate ON)",
          value: fmt(bs?.mean_far_with_gate, 3),
          ok: bs ? bs.mean_far_with_gate < 0.3 : null,
          note: lang === "ko" ? "목표 <0.30" : "target <0.30",
        },
      ],
    },
    {
      title: lang === "ko" ? "② 시점 검증 (lead time)" : "② Timing (lead time)",
      subtitle: lang === "ko"
        ? (leadSource === "17regions"
            ? `17지역 walk-forward 평균 · n=${bs?.n_regions_with_lead ?? 17}`
            : "서울 단독 분석 (Granger/CCF)")
        : leadSource === "17regions"
            ? `17 regions walk-forward avg · n=${bs?.n_regions_with_lead ?? 17}`
            : "Seoul-only (Granger/CCF)",
      color: "var(--layer-search)",
      metrics: [
        {
          label: lang === "ko" ? "Composite lead" : "Composite lead",
          value: fmt(lead, 2),
          unit: lang === "ko" ? "주" : "wks",
          ok: lead !== undefined ? lead >= 6.0 : null,
          note: lang === "ko" ? "목표 ≥6주 (KCDC peak 대비)" : "target ≥6 weeks",
        },
        {
          label: "L1 (OTC)",
          value: fmt(lt.data?.signal_lead_weeks?.l1_otc, 2),
          unit: lang === "ko" ? "주" : "wks",
          ok: null,
          note: lang === "ko" ? "서울 단독 (CCF)" : "Seoul (CCF)",
        },
        {
          label: "L2 (KOWAS)",
          value: fmt(lt.data?.signal_lead_weeks?.l2_wastewater, 2),
          unit: lang === "ko" ? "주" : "wks",
          ok: null,
          note: lang === "ko" ? "서울 단독" : "Seoul",
        },
        {
          label: "L3 (Search)",
          value: fmt(lt.data?.signal_lead_weeks?.l3_search, 2),
          unit: lang === "ko" ? "주" : "wks",
          ok: null,
          note: lang === "ko" ? "단독 경보 금지" : "no solo trigger",
        },
      ],
    },
    {
      title: lang === "ko" ? "③ 회귀 검증 (위험점수)" : "③ Regression (risk score)",
      subtitle: lang === "ko"
        ? "TFT prod (2026-05-04) · composite 0-100 회귀"
        : "TFT prod (2026-05-04) · composite 0-100",
      color: "var(--layer-pharmacy)",
      metrics: [
        {
          label: lang === "ko" ? "MAE @1주 후" : "MAE @1w",
          value: fmt(h1?.mae, 2),
          ok: h1?.mae !== undefined && h1.mae !== null ? h1.mae <= 7.5 : null,
          note: lang === "ko" ? "0-100 절대오차" : "abs error 0-100",
        },
        {
          label: lang === "ko" ? "MAPE @1주 후" : "MAPE @1w",
          value: fmt(h1?.mape_percent, 2),
          unit: "%",
          ok: h1?.mape_percent !== undefined && h1.mape_percent !== null ? h1.mape_percent <= 25 : null,
          note: lang === "ko" ? "목표 <25%" : "target <25%",
        },
        {
          label: lang === "ko" ? "RMSE @1주 후" : "RMSE @1w",
          value: fmt(h1?.rmse, 2),
          ok: null,
          note: `n=${h1?.n ?? "—"}`,
        },
        {
          label: lang === "ko" ? "MAPE @2주 후" : "MAPE @2w",
          value: fmt(h2?.mape_percent, 2),
          unit: "%",
          ok: h2?.mape_percent !== undefined && h2.mape_percent !== null ? h2.mape_percent <= 25 : null,
          note: lang === "ko" ? "horizon 길수록 ↑" : "longer horizon ↑",
        },
      ],
    },
  ];

  const allLoaded = bs && lead !== undefined && prodEval;
  const totalPass = axes.flatMap((a) => a.metrics).filter((m) => m.ok === true).length;
  const totalCheckable = axes.flatMap((a) => a.metrics).filter((m) => m.ok !== null).length;

  return (
    <Panel
      title={lang === "ko" ? "🎯 3축 검증 매트릭스 (분류·시점·회귀)" : "🎯 3-Axis Validation Matrix"}
      sub={
        allLoaded
          ? lang === "ko"
            ? `목표 충족 ${totalPass}/${totalCheckable} · 17지역 walk-forward 실측 (gap 4주)`
            : `${totalPass}/${totalCheckable} targets met · 17 regions walk-forward`
          : lang === "ko"
          ? "데이터 로딩 중…"
          : "loading…"
      }
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "var(--sp-4)",
        }}
      >
        {axes.map((ax) => (
          <AxisCard key={ax.title} axis={ax} />
        ))}
      </div>
      <div
        style={{
          marginTop: 12,
          padding: "8px 12px",
          background: "var(--surface-elevated, rgba(0,0,0,0.02))",
          border: "1px solid var(--border)",
          fontSize: 10,
          color: "var(--text-tertiary)",
          lineHeight: 1.5,
        }}
      >
        {lang === "ko" ? (
          <>
            <strong>정직성 명시 (V11):</strong> ① 분류는 outbreak Y/N, ② 시점은 lead weeks, ③ 회귀는
            composite 위험점수 0-100. <u>환자 수 절대값 예측은 별도 모델 필요 (현 단계 미수행)</u>.
            원본 산출물: <code>analysis/outputs/{`{backtest_17regions,lead_time_summary,tft_regression_backtest_17regions}`}.json</code>
          </>
        ) : (
          <>
            <strong>Honesty note:</strong> ① classification = outbreak Y/N, ② timing = lead weeks, ③ regression =
            composite risk score 0-100. <u>Absolute case-count prediction is out of scope (separate model needed)</u>.
            Source: <code>analysis/outputs/*.json</code>
          </>
        )}
      </div>
    </Panel>
  );
}
