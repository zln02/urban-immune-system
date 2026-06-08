"use client";

import { Panel } from "@/components/ui/panel";
import {
  useLeadTime,
  useBacktest17,
  useTftRegression,
  useCovidBacktest,
  useNoroBacktest,
} from "@/hooks/useAnalysisStats";
import type { Lang } from "@/lib/i18n";
import type { Pathogen } from "@/hooks/useSignalTimeseries";

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

export function ValidationMatrixPanel({
  lang,
  pathogen = "influenza",
}: {
  lang: Lang;
  pathogen?: Pathogen;
}) {
  const lt = useLeadTime();
  const bt = useBacktest17();
  const tft = useTftRegression();
  const covid = useCovidBacktest();
  const noro = useNoroBacktest();

  const isCovid = pathogen === "covid";
  const isNoro = pathogen === "norovirus";

  const bs = bt.data?.summary;
  const cs = covid.data?.summary;
  const ns = noro.data?.summary;
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

  // 분류 카드 — pathogen별 다른 source
  // 정직성: proxy 라벨 한계 — trivial baseline이 ML보다 좋을 수 있음 (v11.5)
  const buildProxyMetrics = (s: typeof cs): Metric[] => {
    const gain = s?.model_gain_vs_trivial_f1 ?? null;
    const gainSign = gain === null ? "" : gain >= 0 ? "+" : "";
    const gainLabel =
      gain === null
        ? ""
        : lang === "ko"
        ? ` · ML gain ${gainSign}${gain.toFixed(3)}`
        : ` · ML gain ${gainSign}${gain.toFixed(3)}`;
    return [
      {
        label: "F1 (ML)",
        value: fmt(s?.pool_f1, 3),
        ok: gain !== null ? gain >= 0 : null,
        note: (lang === "ko"
          ? `vs trivial ${fmt(s?.best_trivial_f1, 3)} (${s?.best_trivial_name ?? "—"})`
          : `vs trivial ${fmt(s?.best_trivial_f1, 3)} (${s?.best_trivial_name ?? "—"})`) + gainLabel,
      },
      {
        label: "Recall (ML)",
        value: fmt(s?.pool_recall, 3),
        ok: s ? s.pool_recall >= 0.7 : null,
        note: lang === "ko"
          ? `n=${s?.pool_n ?? "—"} 양성 ${s?.pool_n_pos ?? "—"} · weekly group CV`
          : `n=${s?.pool_n ?? "—"} pos=${s?.pool_n_pos ?? "—"} · weekly group CV`,
      },
      {
        label: "Precision (ML)",
        value: fmt(s?.pool_precision, 3),
        ok: s ? s.pool_precision >= 0.6 : null,
        note: lang === "ko" ? "L1 미적재 (L2+L3 only)" : "L1 missing (L2+L3 only)",
      },
      {
        label: "FAR (ML)",
        value: fmt(s?.pool_far, 3),
        ok: s ? s.pool_far < 0.3 : null,
        note: lang === "ko"
          ? `trivial FAR ${fmt(s?.best_trivial_far, 3)} · MCC ${fmt(s?.pool_mcc, 3)}`
          : `trivial FAR ${fmt(s?.best_trivial_far, 3)} · MCC ${fmt(s?.pool_mcc, 3)}`,
      },
    ];
  };

  const classificationMetrics: Metric[] = isCovid
    ? buildProxyMetrics(cs)
    : isNoro
    ? buildProxyMetrics(ns)
    : [
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
      ];

  const axes: Axis[] = [
    {
      title: isCovid
        ? lang === "ko" ? "① 분류 (COVID-19 β · proxy)" : "① Classification (COVID-19 β · proxy)"
        : isNoro
        ? lang === "ko" ? "① 분류 (노로 β · proxy)" : "① Classification (Norovirus β · proxy)"
        : lang === "ko" ? "① 분류 검증 (경보 Y/N)" : "① Classification (alert Y/N)",
      subtitle: isCovid || isNoro
        ? lang === "ko"
          ? "self-target proxy: L2(t+2주) ≥ thr · weekly group CV (leakage-free)"
          : "self-target proxy: L2(t+2w) ≥ thr · weekly group CV"
        : lang === "ko" ? "17지역 walk-forward · gate 4주" : "17 regions · gap 4w",
      color: "var(--risk-safe)",
      metrics: classificationMetrics,
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
      title: pathogen === "influenza"
        ? lang === "ko" ? "③ 회귀 검증 (위험점수)" : "③ Regression (risk score)"
        : lang === "ko" ? "③ 회귀 (인플루엔자 전용)" : "③ Regression (influenza only)",
      subtitle: pathogen === "influenza"
        ? lang === "ko" ? "TFT prod (2026-05-04) · composite 0-100 회귀" : "TFT prod (2026-05-04) · composite 0-100"
        : lang === "ko" ? "다질병 회귀 미수행 — TFT 인플루엔자 학습" : "no multi-pathogen regression yet",
      color: "var(--layer-pharmacy)",
      metrics: pathogen !== "influenza" ? [
        { label: "MAE @1w", value: "—", ok: null, note: lang === "ko" ? "인플루엔자 전용" : "influenza only" },
        { label: "MAPE @1w", value: "—", ok: null, note: lang === "ko" ? "P0 PatchTST 도입" : "P0 PatchTST" },
        { label: "RMSE @1w", value: "—", ok: null, note: lang === "ko" ? "데이터 누적 필요" : "data accrual" },
        { label: "MAPE @2w", value: "—", ok: null, note: lang === "ko" ? "발표 후 R&D" : "post-presentation R&D" },
      ] : [
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
            <strong>정직성 명시 (V11.5):</strong> ① 인플루엔자 분류는 KDCA peak 외부 라벨로 학습/검증.
            ② COVID·노로는 <u>self-target proxy (L2 자체 t+2주 값 라벨)</u> — L2(t)와 강한 자기상관 때문에
            단순 임계 비교(trivial)가 ML 모델보다 좋을 수 있음. ML 우위는 KDCA 확진자 연동 후 회복 예상.
            ③ 시점 = lead weeks, 회귀 = composite 위험점수 (인플루엔자 전용). 환자 수 절대값 예측은 별도 모델.
            원본: <code>analysis/outputs/backtest_xgboost_{`{covid,norovirus}`}_17regions.json</code> (baselines 포함)
          </>
        ) : (
          <>
            <strong>Honesty note (V11.5):</strong> ① Influenza classification uses KDCA peak external labels.
            ② COVID·Norovirus use <u>self-target proxy (L2 self t+2w value as label)</u> — strong autocorrelation
            means trivial threshold may beat ML. ML edge expected post-KDCA confirmed integration.
            ③ Timing = lead weeks; regression = influenza-only.
            Source: <code>analysis/outputs/backtest_xgboost_*.json</code> (baselines included)
          </>
        )}
      </div>
    </Panel>
  );
}
