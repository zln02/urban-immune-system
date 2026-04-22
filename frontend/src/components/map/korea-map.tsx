"use client";

import { useState, type CSSProperties } from "react";
import { KOREA_REGIONS, type RegionCode, regionName } from "@/lib/korea-regions";
import { RISK_META, type RiskLevel } from "@/lib/risk";
import type { RiskInfo } from "@/lib/mock-data";
import type { Lang } from "@/lib/i18n";

interface KoreaMapProps {
  data: Record<RegionCode, RiskInfo>;
  lang: Lang;
  selected?: RegionCode;
  onSelect?: (code: RegionCode) => void;
  size?: number;
  showLabels?: boolean;
}

/**
 * 전국 17개 시도 choropleth — 추상화된 SVG geometry.
 * Jeolla 권역 (JB·JN·GJU) 은 대시보더 프레임으로 우선 감시 강조.
 *
 * 3중 코딩:
 *  - 색상: --risk-* 토큰
 *  - 패턴: L3/L4 에 hatch (색맹 구분 보조)
 *  - 글자: 각 지역명 표시
 */
export function KoreaMap({
  data,
  lang,
  selected,
  onSelect,
  size = 560,
  showLabels = true,
}: KoreaMapProps) {
  const [hover, setHover] = useState<RegionCode | null>(null);

  const mapTitle = lang === "en" ? "Nationwide · 17 provinces" : "전국 17개 시도 위험도";

  return (
    <svg
      viewBox="0 0 540 700"
      width="100%"
      style={{ maxWidth: size, display: "block" }}
      role="img"
      aria-label={mapTitle}
    >
      <defs>
        {/* L3 경계 hatch */}
        <pattern
          id="hatch-warn"
          width="6"
          height="6"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width="6" height="6" fill="var(--risk-warning)" />
          <line x1="0" y1="0" x2="0" y2="6" stroke="rgba(0,0,0,0.2)" strokeWidth="2" />
        </pattern>
        {/* L4 경보 hatch */}
        <pattern
          id="hatch-alert"
          width="6"
          height="6"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width="6" height="6" fill="var(--risk-alert)" />
          <line x1="0" y1="0" x2="0" y2="6" stroke="rgba(0,0,0,0.3)" strokeWidth="2.5" />
        </pattern>
        <filter id="alertPulse">
          <feGaussianBlur stdDeviation="2" />
        </filter>
      </defs>

      {/* Jeolla focus ring */}
      <rect
        x="108"
        y="360"
        width="190"
        height="260"
        fill="none"
        stroke="var(--risk-alert)"
        strokeWidth="1.5"
        strokeDasharray="4 3"
        opacity="0.6"
      />
      <text
        x="204"
        y="355"
        textAnchor="middle"
        fontSize="10"
        fontWeight="700"
        fill="var(--risk-alert)"
        letterSpacing="1"
      >
        {lang === "en" ? "JEOLLA · PRIORITY" : "전라 · 우선 감시"}
      </text>

      {/* Regions */}
      {KOREA_REGIONS.map((region) => {
        const info = data[region.code];
        const level = info.risk as RiskLevel;
        const isHover = hover === region.code;
        const isSelected = selected === region.code;
        const isAlert = level === 4;
        const meta = RISK_META[level];

        const fill =
          level === 3
            ? "url(#hatch-warn)"
            : level === 4
            ? "url(#hatch-alert)"
            : `var(--risk-${meta.token})`;

        const pathStyle: CSSProperties = {
          cursor: "pointer",
          opacity: hover !== null && !isHover ? 0.75 : 1,
          transition: "opacity 120ms, stroke-width 120ms",
        };

        return (
          <g key={region.code}>
            {isAlert && (
              <path
                d={region.d}
                fill="var(--risk-alert)"
                opacity="0.5"
                filter="url(#alertPulse)"
                style={{ animation: "uis-pulse 1.8s ease-in-out infinite" }}
              />
            )}
            <path
              d={region.d}
              fill={fill}
              stroke={isSelected ? "var(--text)" : "var(--bg)"}
              strokeWidth={isSelected ? 2 : 1}
              style={pathStyle}
              onMouseEnter={() => setHover(region.code)}
              onMouseLeave={() => setHover(null)}
              onClick={() => onSelect?.(region.code)}
              role="button"
              aria-label={`${regionName(region.code, lang)} · L${level} ${meta.label[lang]}`}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelect?.(region.code);
              }}
            />
          </g>
        );
      })}

      {/* Labels */}
      {showLabels &&
        KOREA_REGIONS.map((region) => {
          const info = data[region.code];
          const level = info.risk as RiskLevel;
          const textColor = level >= 3 ? "#fff" : "var(--text)";
          return (
            <text
              key={`label-${region.code}`}
              x={region.centroid.x}
              y={region.centroid.y}
              textAnchor="middle"
              fontSize="12"
              fontWeight={level >= 3 ? 700 : 600}
              fill={textColor}
              style={{ pointerEvents: "none", letterSpacing: 0 }}
            >
              {regionName(region.code, lang)}
            </text>
          );
        })}

      {/* Hover tooltip */}
      {hover &&
        (() => {
          const region = KOREA_REGIONS.find((r) => r.code === hover);
          if (!region) return null;
          const info = data[hover];
          const x = Math.min(region.centroid.x + 10, 420);
          const y = Math.max(region.centroid.y - 50, 10);
          return (
            <g transform={`translate(${x},${y})`} style={{ pointerEvents: "none" }}>
              <rect
                x="0"
                y="0"
                width="118"
                height="46"
                fill="var(--surface)"
                stroke="var(--border-strong)"
                strokeWidth="1"
              />
              <text x="8" y="14" fontSize="10" fontWeight="600" fill="var(--text)">
                {regionName(hover, lang)}
              </text>
              <text x="8" y="28" fontSize="9" fill="var(--text-secondary)">
                L{info.risk} · {info.cases} {lang === "en" ? "cases" : "건"}
              </text>
              <text
                x="8"
                y="40"
                fontSize="9"
                fill={info.change > 0 ? "var(--risk-warning)" : "var(--risk-safe)"}
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {info.change > 0 ? "▲" : "▼"} {info.change > 0 ? "+" : ""}
                {info.change.toFixed(1)}% / 7d
              </text>
            </g>
          );
        })()}
    </svg>
  );
}
