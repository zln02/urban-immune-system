"use client";

import { useState, useEffect, useMemo, type CSSProperties } from "react";
import type { RegionCode } from "@/lib/korea-regions";
import { regionName } from "@/lib/korea-regions";
import { RISK_META, type RiskLevel } from "@/lib/risk";
import type { DistrictData } from "@/lib/mock-data";
import type { Lang } from "@/lib/i18n";

// ─── GeoJSON 최소 타입 ────────────────────────────────────────────────
type Pos = [number, number];
type GeoPolygon = { type: "Polygon"; coordinates: Pos[][] };
type GeoMultiPolygon = { type: "MultiPolygon"; coordinates: Pos[][][] };
type Feature = {
  type: "Feature";
  properties: { code: string; name: string; nameEng: string };
  geometry: GeoPolygon | GeoMultiPolygon;
};

interface ProjectedRegion {
  code: RegionCode;
  name: string;
  nameEng: string;
  path: string;
  centroid: [number, number];
}

// ─── 투영 (equirectangular — 한국 범위에서 충분) ─────────────────────
const LON_MIN = 124.6, LON_MAX = 132.0;
const LAT_MIN = 33.0, LAT_MAX = 38.9;
const VW = 540, VH = 700;

function project(lon: number, lat: number): [number, number] {
  return [
    ((lon - LON_MIN) / (LON_MAX - LON_MIN)) * VW,
    ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * VH,
  ];
}

function ringToD(ring: Pos[]): string {
  return ring
    .map(([lon, lat], i) => {
      const [x, y] = project(lon, lat);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ") + " Z";
}

function geomToPath(geom: GeoPolygon | GeoMultiPolygon): string {
  if (geom.type === "Polygon") return geom.coordinates.map(ringToD).join(" ");
  return geom.coordinates.flatMap((poly) => poly.map(ringToD)).join(" ");
}

function geomCentroid(geom: GeoPolygon | GeoMultiPolygon): [number, number] {
  const rings = geom.type === "Polygon" ? [geom.coordinates[0]] : geom.coordinates.map((p) => p[0]);
  const main = rings.reduce((a, b) => (a.length >= b.length ? a : b));
  const lon = main.reduce((s, p) => s + p[0], 0) / main.length;
  const lat = main.reduce((s, p) => s + p[1], 0) / main.length;
  return project(lon, lat);
}

// ─── 컴포넌트 ─────────────────────────────────────────────────────────
interface KoreaMapProps {
  data: Record<RegionCode, DistrictData>;
  lang: Lang;
  selected?: RegionCode;
  onSelect?: (code: RegionCode) => void;
  size?: number;
  showLabels?: boolean;
}

export function KoreaMap({ data, lang, selected, onSelect, size = 560, showLabels = true }: KoreaMapProps) {
  const [regions, setRegions] = useState<ProjectedRegion[]>([]);
  const [hover, setHover] = useState<RegionCode | null>(null);

  // 공개 GeoJSON 로드 (public/korea-sido.geojson)
  useEffect(() => {
    fetch("/korea-sido.geojson")
      .then((r) => r.json())
      .then((gj: { features: Feature[] }) => {
        const projected: ProjectedRegion[] = gj.features.map((f) => ({
          code: f.properties.code as RegionCode,
          name: f.properties.name,
          nameEng: f.properties.nameEng,
          path: geomToPath(f.geometry),
          centroid: geomCentroid(f.geometry),
        }));
        setRegions(projected);
      })
      .catch(() => {/* GeoJSON 로드 실패 시 빈 지도 */});
  }, []);

  const mapTitle = lang === "en" ? "Nationwide · 17 provinces" : "전국 17개 시도 위험도";

  // Jeolla focus bounding box (투영 좌표)
  const [jFocusX, jFocusY] = project(126.0, 35.9); // 전라 북서 모서리 approx
  const [jFocusX2, jFocusY2] = project(127.9, 34.0); // 전라 남동 모서리 approx
  const jW = jFocusX2 - jFocusX;
  const jH = jFocusY2 - jFocusY;

  if (regions.length === 0) {
    return (
      <svg viewBox={`0 0 ${VW} ${VH}`} width="100%" style={{ maxWidth: size, display: "block" }} aria-busy="true">
        <rect x="0" y="0" width={VW} height={VH} fill="var(--bg-sub)" rx="8" />
        <text x={VW / 2} y={VH / 2} textAnchor="middle" fontSize="14" fill="var(--text-secondary)">
          지도 로딩 중…
        </text>
      </svg>
    );
  }

  return (
    <svg
      viewBox={`0 0 ${VW} ${VH}`}
      width="100%"
      style={{ maxWidth: size, display: "block" }}
      role="img"
      aria-label={mapTitle}
    >
      <defs>
        <pattern id="hatch-warn" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="6" height="6" fill="var(--risk-warning)" />
          <line x1="0" y1="0" x2="0" y2="6" stroke="rgba(0,0,0,0.2)" strokeWidth="2" />
        </pattern>
        <pattern id="hatch-alert" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="6" height="6" fill="var(--risk-alert)" />
          <line x1="0" y1="0" x2="0" y2="6" stroke="rgba(0,0,0,0.3)" strokeWidth="2.5" />
        </pattern>
        <filter id="alertPulse">
          <feGaussianBlur stdDeviation="3" />
        </filter>
      </defs>

      {/* 전라 우선 감시 focus ring */}
      <rect
        x={jFocusX - 8}
        y={jFocusY - 8}
        width={jW + 16}
        height={jH + 16}
        fill="none"
        stroke="var(--risk-alert)"
        strokeWidth="1.5"
        strokeDasharray="4 3"
        opacity="0.65"
      />
      <text
        x={jFocusX + jW / 2}
        y={jFocusY - 12}
        textAnchor="middle"
        fontSize="9"
        fontWeight="700"
        fill="var(--risk-alert)"
        letterSpacing="1"
      >
        {lang === "en" ? "JEOLLA · PRIORITY" : "전라 · 우선 감시"}
      </text>

      {/* 지역 choropleth */}
      {regions.map((region) => {
        const info = data[region.code];
        if (!info) return null;
        const level = info.risk as RiskLevel;
        const isHover = hover === region.code;
        const isSelected = selected === region.code;
        const isAlert = level === 4;
        const meta = RISK_META[level];
        const fill =
          level === 3 ? "url(#hatch-warn)" : level === 4 ? "url(#hatch-alert)" : `var(--risk-${meta.token})`;

        return (
          <g key={region.code}>
            {isAlert && (
              <path
                d={region.path}
                fill="var(--risk-alert)"
                opacity="0.45"
                filter="url(#alertPulse)"
                style={{ animation: "uis-pulse 1.8s ease-in-out infinite" }}
              />
            )}
            <path
              d={region.path}
              fill={fill}
              stroke={isSelected ? "var(--text)" : "var(--bg)"}
              strokeWidth={isSelected ? 2 : 0.8}
              style={{
                cursor: "pointer",
                opacity: hover !== null && !isHover ? 0.75 : 1,
                transition: "opacity 120ms, stroke-width 120ms",
              } as CSSProperties}
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

      {/* 지역명 레이블 */}
      {showLabels &&
        regions.map((region) => {
          const info = data[region.code];
          if (!info) return null;
          const level = info.risk as RiskLevel;
          const [cx, cy] = region.centroid;
          return (
            <text
              key={`lbl-${region.code}`}
              x={cx}
              y={cy}
              textAnchor="middle"
              fontSize="10"
              fontWeight={level >= 3 ? 700 : 500}
              fill={level >= 3 ? "#fff" : "var(--text)"}
              style={{ pointerEvents: "none" }}
            >
              {regionName(region.code, lang)}
            </text>
          );
        })}

      {/* 호버 툴팁 */}
      {hover &&
        (() => {
          const region = regions.find((r) => r.code === hover);
          if (!region) return null;
          const info = data[hover];
          const [cx, cy] = region.centroid;
          const tx = Math.min(cx + 10, VW - 130);
          const ty = Math.max(cy - 55, 10);
          return (
            <g transform={`translate(${tx},${ty})`} style={{ pointerEvents: "none" }}>
              <rect x="0" y="0" width="118" height="46" fill="var(--bg)" stroke="var(--border)" strokeWidth="1" rx="3" />
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
                style={{ fontVariantNumeric: "tabular-nums" } as CSSProperties}
              >
                {info.change > 0 ? "▲ +" : "▼ "}{info.change.toFixed(1)}% / 7d
              </text>
            </g>
          );
        })()}
    </svg>
  );
}
