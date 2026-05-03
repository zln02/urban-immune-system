"use client";
import { useState } from "react";
import useSWR from "swr";
import type { Lang } from "@/lib/i18n";

interface AnomalyPanelProps {
  lang: Lang;
}

interface AnomalyRegion {
  code: string;
  name: string;
  score: number;
  status: "anomaly" | "warning" | "normal";
}

interface AnomalyMeta {
  generated_at?: string;        // ISO UTC
  threshold?: number;
  threshold_percentile?: number;
  fallback_temperature_count?: number;
}

/** 이상탐지 점수 — Autoencoder 재구성 오차 기반 (ml/anomaly/autoencoder.py)
 *  /api/v1/predictions/anomaly 에서 60초 폴링.
 *  score 50 = 임계값(threshold), status = API 반환값 그대로 사용.
 */
function useAnomalyScores(): { regions: AnomalyRegion[]; meta: AnomalyMeta } {
  const { data } = useSWR<{
    generated_at?: string;
    threshold?: number;
    threshold_percentile?: number;
    anomaly_scores: Array<{
      region: string;
      score: number;
      reconstruction_error: number;
      status: "anomaly" | "warning" | "normal";
      features: { l1: number; l2: number; l3: number; temperature: number };
      fallback_temperature: boolean;
    }>;
  }>(
    `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/predictions/anomaly`,
    (url: string) => fetch(url).then((r) => r.json()),
    { refreshInterval: 60_000, revalidateOnFocus: false },
  );
  if (!data?.anomaly_scores) return { regions: [], meta: {} };
  const regions = data.anomaly_scores.map((a) => ({
    code: a.region.slice(0, 2),
    name: a.region,
    score: Math.round(a.score),
    status: a.status,
  }));
  const meta: AnomalyMeta = {
    generated_at: data.generated_at,
    threshold: data.threshold,
    threshold_percentile: data.threshold_percentile,
    fallback_temperature_count: data.anomaly_scores.filter((a) => a.fallback_temperature).length,
  };
  return { regions, meta };
}

function formatKstTimestamp(iso?: string, lang: Lang = "ko"): string {
  if (!iso) return lang === "ko" ? "데이터 없음" : "no data";
  try {
    const d = new Date(iso);
    const fmt = new Intl.DateTimeFormat(lang === "ko" ? "ko-KR" : "en-US", {
      timeZone: "Asia/Seoul",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
    });
    return fmt.format(d) + " KST";
  } catch {
    return iso;
  }
}

const STATUS_META = {
  anomaly: { label: { ko: "이상 감지", en: "Anomaly"  }, color: "var(--risk-alert)",   bg: "#fef2f2" },
  warning: { label: { ko: "주의 관찰", en: "Watch"    }, color: "var(--risk-warning)",  bg: "#fff7ed" },
  normal:  { label: { ko: "정상",      en: "Normal"   }, color: "var(--risk-safe)",     bg: "var(--bg-sub)" },
};

function ScoreBar({ score, status }: { score: number; status: AnomalyRegion["status"] }) {
  return (
    <div style={{ position: "relative", height: 6, background: "var(--border)", flex: 1 }}>
      <div
        style={{
          position: "absolute",
          left: 0, top: 0, bottom: 0,
          width: `${score}%`,
          background: STATUS_META[status].color,
          transition: "width 0.6s ease",
        }}
      />
      {/* 임계값 마커 (75%) */}
      <div
        style={{
          position: "absolute",
          left: "75%",
          top: -3,
          bottom: -3,
          width: 1,
          background: "var(--border-strong)",
        }}
      />
    </div>
  );
}

export function AnomalyPanel({ lang }: AnomalyPanelProps) {
  const { regions, meta } = useAnomalyScores();
  const [expanded, setExpanded] = useState<string | null>(null);
  const anomalyCount = regions.filter((r) => r.status === "anomaly").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-4)" }}>

      {/* 설명 배너 + 업데이트 시각·임계값 메타 */}
      <div
        style={{
          padding: "12px 16px",
          background: "#eff6ff",
          border: "1px solid #bfdbfe",
          fontSize: 12,
          lineHeight: 1.6,
          color: "#1e40af",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <strong>
            {lang === "ko" ? "🧬 신규 감염병 조기탐지 모드" : "🧬 Novel Pathogen Early Detection"}
          </strong>
          <span style={{ fontSize: 11, color: "#1e3a8a", fontVariantNumeric: "tabular-nums" }}>
            {lang === "ko" ? "마지막 업데이트: " : "Last update: "}
            <strong>{formatKstTimestamp(meta.generated_at, lang)}</strong>
            {meta.threshold !== undefined && (
              <>
                {" · "}
                {lang === "ko" ? "임계값" : "threshold"}{" "}
                <strong>{meta.threshold.toFixed(4)}</strong>
                {meta.threshold_percentile !== undefined && (
                  <span> ({meta.threshold_percentile}p)</span>
                )}
              </>
            )}
          </span>
        </div>
        <div style={{ marginTop: 4 }}>
          {lang === "ko"
            ? "Autoencoder가 학습한 정상 패턴 대비 재구성 오차를 실시간 측정합니다. 질병명을 모르더라도 \"뭔가 평소와 다르다\"는 신호를 포착합니다."
            : "Measures reconstruction error vs. learned normal patterns in real-time. Detects \"something unusual\" even before a pathogen is identified."}
        </div>
        {meta.fallback_temperature_count !== undefined && meta.fallback_temperature_count > 0 && (
          <div style={{ marginTop: 6, fontSize: 11, color: "#92400e", background: "#fffbeb", padding: "4px 8px", border: "1px solid #fde68a" }}>
            {lang === "ko"
              ? `⚠️ 기상 데이터 fallback ${meta.fallback_temperature_count}/${regions.length}개 지역 — KMA API 활성화 시 자동 정상화`
              : `⚠️ Weather fallback ${meta.fallback_temperature_count}/${regions.length} regions — auto-resolves when KMA API activates`}
          </div>
        )}
      </div>

      {/* 전국 이상지수 요약 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "var(--sp-4)",
        }}
      >
        {[
          {
            label: lang === "ko" ? "이상 감지 지역" : "Anomaly regions",
            value: anomalyCount,
            color: "var(--risk-alert)",
          },
          {
            label: lang === "ko" ? "주의 관찰 지역" : "Watch regions",
            value: regions.filter((r) => r.status === "warning").length,
            color: "var(--risk-warning)",
          },
          {
            label: lang === "ko" ? "평균 이상 지수" : "Avg anomaly score",
            value: Math.round(
              regions.filter((r) => r.status !== "normal")
                .reduce((s, r) => s + r.score, 0) /
                Math.max(regions.filter((r) => r.status !== "normal").length, 1)
            ),
            color: "var(--primary-70)",
          },
        ].map((kpi) => (
          <div
            key={kpi.label}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderTop: `3px solid ${kpi.color}`,
              padding: "12px 14px",
            }}
          >
            <div className="t-label-01" style={{ color: "var(--text-tertiary)", marginBottom: 6 }}>
              {kpi.label}
            </div>
            <div
              style={{
                fontSize: 28,
                fontWeight: 700,
                color: kpi.color,
                fontFamily: "var(--font-mono)",
                lineHeight: 1,
              }}
            >
              {kpi.value}
            </div>
          </div>
        ))}
      </div>

      {/* 지역별 이상지수 리스트 */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            padding: "12px 16px",
            borderBottom: "1px solid var(--border)",
            fontSize: 13,
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span>
            {lang === "ko" ? "지역별 이상 지수" : "Regional anomaly scores"}
          </span>
          <span style={{ fontSize: 10, color: "var(--text-tertiary)", fontWeight: 400 }}>
            {lang === "ko" ? "임계값 75 이상 = 이상 감지" : "Threshold ≥75 = anomaly"}
          </span>
        </div>

        {regions.map((r, idx) => {
          const meta = STATUS_META[r.status];
          const isOpen = expanded === r.name;
          return (
            <div
              key={r.name}
              style={{
                borderTop: idx > 0 ? "1px solid var(--border)" : "none",
                background: isOpen ? meta.bg : "transparent",
              }}
            >
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? null : r.name)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 16px",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left",
                  fontFamily: "inherit",
                }}
              >
                <span style={{ width: 80, fontSize: 12, fontWeight: 500 }}>{r.name}</span>
                <ScoreBar score={r.score} status={r.status} />
                <span
                  style={{
                    width: 36,
                    textAlign: "right",
                    fontFamily: "var(--font-mono)",
                    fontSize: 13,
                    fontWeight: 700,
                    color: meta.color,
                  }}
                >
                  {r.score}
                </span>
                <span
                  style={{
                    width: 64,
                    padding: "2px 6px",
                    fontSize: 10,
                    fontWeight: 700,
                    background: meta.color,
                    color: "#fff",
                    textAlign: "center",
                  }}
                >
                  {meta.label[lang]}
                </span>
              </button>

              {isOpen && (
                <div
                  style={{
                    padding: "0 16px 12px 16px",
                    fontSize: 11,
                    color: "var(--text-secondary)",
                    lineHeight: 1.6,
                  }}
                >
                  <strong style={{ color: "var(--text)" }}>
                    {lang === "ko" ? "이상 신호 해석" : "Signal interpretation"}
                  </strong>
                  <br />
                  {r.status === "anomaly" && (
                    lang === "ko"
                      ? `${r.name} 지역의 3계층 신호 패턴이 학습된 정상 범위(재구성 오차 기준)를 크게 벗어났습니다. OTC 구매량과 검색 트렌드가 동시에 비정상 증가 중입니다. 역학조사관의 현장 확인을 권장합니다.`
                      : `Signal patterns in ${r.name} deviate significantly from learned normal baseline. Simultaneous anomaly in OTC and search trends. Field verification by epidemiologists recommended.`
                  )}
                  {r.status === "warning" && (
                    lang === "ko"
                      ? `${r.name} 지역의 신호 패턴이 정상 범위 상단에 근접하고 있습니다. 단독 이상이 아닌 교차 확인이 필요합니다.`
                      : `Signal patterns approaching upper bound of normal range. Cross-layer confirmation needed.`
                  )}
                  <div style={{ marginTop: 6, color: "var(--text-tertiary)", fontSize: 10 }}>
                    {lang === "ko"
                      ? "⚠️ AI 분석 결과 · 역학조사관 최종 판단 필요"
                      : "⚠️ AI analysis · Requires epidemiologist confirmation"}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 알고리즘 설명 */}
      <div
        style={{
          padding: "12px 16px",
          background: "var(--bg-sub)",
          border: "1px solid var(--border)",
          fontSize: 11,
          color: "var(--text-secondary)",
          lineHeight: 1.6,
        }}
      >
        <div style={{ fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>
          {lang === "ko" ? "작동 원리" : "How it works"}
        </div>
        {lang === "ko"
          ? "Autoencoder가 52주 정상 시즌 데이터로 3계층 신호 패턴을 학습합니다. 입력 신호를 압축 후 복원할 때 발생하는 재구성 오차(Reconstruction Error)가 임계값(95th percentile)을 초과하면 이상으로 판정합니다. 인플루엔자, COVID-19 등 특정 질병명을 모르더라도 \"비정상 패턴\"을 탐지할 수 있습니다."
          : "An Autoencoder learns normal 3-layer signal patterns from 52 weeks of baseline data. When reconstruction error from compressing and restoring input exceeds the 95th-percentile threshold, an anomaly is flagged — even without knowing the specific pathogen."}
      </div>
    </div>
  );
}
