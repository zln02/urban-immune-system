"use client";

import { useOtcTrend, useSearchTrend } from "@/hooks/useNaverTrend";
import { useWastewaterSeries } from "@/hooks/useSignalTimeseries";
import { useRegionAlerts } from "@/hooks/useRegionAlerts";
import type { Lang } from "@/lib/i18n";

interface LayerHealth {
  name: string;
  color: string;
  lastDate?: string;
  daysAgo?: number;
  state: "ok" | "warn" | "fail";
  errorMsg?: string;
}

function daysBetween(isoDate: string): number {
  const d = new Date(isoDate).getTime();
  if (!isFinite(d)) return NaN;
  const now = Date.now();
  return Math.floor((now - d) / (1000 * 60 * 60 * 24));
}

/**
 * 운영 알림 배너 — 데이터 수집 상태 모니터링.
 *
 * 검사 대상:
 *   L1 OTC (네이버 쇼핑인사이트) · L2 KOWAS 하수 · L3 검색 트렌드 · regionAlerts
 *
 * 임계:
 *   ok   < 8일
 *   warn 8 ~ 14일
 *   fail ≥ 15일 또는 fetch 실패
 *
 * GREEN(모두 정상) → 배너 자동 숨김. 1개 이상 warn/fail → 노랑/빨강 배너.
 */
export function SystemHealthBanner({ lang }: { lang: Lang }) {
  const otc = useOtcTrend(4);
  const search = useSearchTrend(4);
  // 하수 데이터: 서울 기준 freshness 체크 (어차피 KOWAS는 전국 동일 업데이트 사이클)
  const sewage = useWastewaterSeries("서울특별시", 60);
  const alerts = useRegionAlerts(8);

  const STALE_WARN = 8;
  const STALE_FAIL = 15;

  function classify(lastDate: string | undefined, fetchError?: unknown): LayerHealth["state"] {
    if (fetchError) return "fail";
    if (!lastDate) return "fail";
    const d = daysBetween(lastDate);
    if (!isFinite(d)) return "fail";
    if (d >= STALE_FAIL) return "fail";
    if (d >= STALE_WARN) return "warn";
    return "ok";
  }

  const otcSeries = otc.data?.series ?? [];
  const searchSeries = search.data?.series ?? [];
  const sewageSeries = sewage.data?.data ?? [];
  const otcLast = otcSeries.length > 0 ? otcSeries[otcSeries.length - 1].date : undefined;
  const searchLast = searchSeries.length > 0 ? searchSeries[searchSeries.length - 1].date : undefined;
  const sewageLast = sewageSeries.length > 0 ? sewageSeries[sewageSeries.length - 1].time : undefined;

  const layers: LayerHealth[] = [
    {
      name: "L1 OTC",
      color: "var(--layer-pharmacy)",
      lastDate: otcLast,
      daysAgo: otcLast ? daysBetween(otcLast) : undefined,
      state: classify(otcLast, otc.error),
      errorMsg: otc.error?.message,
    },
    {
      name: "L2 KOWAS",
      color: "var(--layer-sewage)",
      lastDate: sewageLast,
      daysAgo: sewageLast ? daysBetween(sewageLast) : undefined,
      state: classify(sewageLast, sewage.error),
      errorMsg: sewage.error?.message,
    },
    {
      name: "L3 Search",
      color: "var(--layer-search)",
      lastDate: searchLast,
      daysAgo: searchLast ? daysBetween(searchLast) : undefined,
      state: classify(searchLast, search.error),
      errorMsg: search.error?.message,
    },
    {
      name: lang === "ko" ? "경보 API" : "Alerts API",
      color: "var(--text-secondary)",
      lastDate: alerts.dataUpdatedAt ? new Date(alerts.dataUpdatedAt).toISOString() : undefined,
      daysAgo: 0,
      state: alerts.error ? "fail" : "ok",
      errorMsg: alerts.error?.message,
    },
  ];

  const failCount = layers.filter((l) => l.state === "fail").length;
  const warnCount = layers.filter((l) => l.state === "warn").length;

  // 모든 ok면 배너 숨김
  if (failCount === 0 && warnCount === 0) return null;

  const isFail = failCount > 0;
  const bg = isFail ? "rgba(220, 38, 38, 0.08)" : "rgba(234, 179, 8, 0.08)";
  const border = isFail ? "var(--risk-alert)" : "var(--risk-warning)";

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        background: bg,
        border: `1px solid ${border}`,
        borderLeft: `4px solid ${border}`,
        padding: "10px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>{isFail ? "🔴" : "🟡"}</span>
          <strong style={{ fontSize: 13, color: "var(--text)" }}>
            {lang === "ko"
              ? (isFail
                  ? `데이터 수집 이상 — ${failCount}개 계층 실패${warnCount > 0 ? `, ${warnCount}개 경고` : ""}`
                  : `데이터 수집 주의 — ${warnCount}개 계층 늦음`)
              : (isFail
                  ? `Data collection issue — ${failCount} layer(s) failed${warnCount > 0 ? `, ${warnCount} warn` : ""}`
                  : `Collection warning — ${warnCount} layer(s) stale`)}
          </strong>
        </div>
        <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>
          {lang === "ko" ? "임계 8일 경고 · 15일 실패" : "threshold 8d warn / 15d fail"}
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
        {layers.map((l) => {
          const dot = l.state === "ok" ? "#10b981" : l.state === "warn" ? "#eab308" : "#dc2626";
          const ageText = l.state === "fail"
            ? (l.errorMsg ? "ERR" : (lang === "ko" ? "데이터 없음" : "no data"))
            : l.daysAgo !== undefined && isFinite(l.daysAgo)
              ? (lang === "ko" ? `${l.daysAgo}일 전` : `${l.daysAgo}d ago`)
              : "—";
          return (
            <div
              key={l.name}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                padding: "6px 10px",
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 11,
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: dot, flexShrink: 0 }} />
              <span style={{ fontWeight: 600, color: "var(--text)" }}>{l.name}</span>
              <span style={{ marginLeft: "auto", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                {ageText}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
