"use client";

// 네이버 지도 위에 17개 시·도 GeoJSON 폴리곤을 risk choropleth로 오버레이.
// SVG 버전(KoreaMap)과 prop 시그니처 동일 — Dashboard 에서 env 플래그로 토글.
//
// 키 발급: https://www.ncloud.com → AI·Application Service → Maps
//   → Application 등록 (도메인: localhost, 34.64.124.90, 발표용 도메인)
//   → Web Dynamic Map "ncpKeyId" 복사
//   → frontend/.env.local 에 NEXT_PUBLIC_NAVER_MAPS_KEY_ID=xxxx 추가 후 재시작.

import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { RegionCode } from "@/lib/korea-regions";
import type { DistrictData } from "@/lib/mock-data";
import type { Lang } from "@/lib/i18n";

// 네이버 지도 SDK 전역 타입 (필요한 부분만 최소 선언).
declare global {
  interface Window {
    naver?: NaverNS;
  }
}
type NaverNS = {
  maps: {
    Map: new (el: HTMLElement, opts: NaverMapOptions) => NaverMap;
    LatLng: new (lat: number, lng: number) => NaverLatLng;
    LatLngBounds: new () => NaverLatLngBounds;
    Polygon: new (opts: NaverPolygonOptions) => NaverPolygon;
    Event: {
      addListener: (target: unknown, ev: string, fn: (...args: unknown[]) => void) => unknown;
    };
    Position?: { TOP_RIGHT: number };
    MapTypeControlStyle?: { BUTTON: number };
    ZoomControlStyle?: { SMALL: number };
  };
};
type NaverLatLng = { _lat: number; _lng: number };
type NaverLatLngBounds = { extend: (ll: NaverLatLng) => void };
type NaverMapOptions = {
  center: NaverLatLng;
  zoom: number;
  minZoom?: number;
  maxZoom?: number;
  zoomControl?: boolean;
  mapTypeControl?: boolean;
  scaleControl?: boolean;
  logoControl?: boolean;
  mapDataControl?: boolean;
};
type NaverMap = {
  fitBounds: (b: NaverLatLngBounds) => void;
  setCenter: (ll: NaverLatLng) => void;
  setZoom: (z: number) => void;
};
type NaverPolygonOptions = {
  map?: NaverMap | null;
  paths: NaverLatLng[][];
  fillColor: string;
  fillOpacity: number;
  strokeColor: string;
  strokeOpacity?: number;
  strokeWeight: number;
  clickable?: boolean;
};
type NaverPolygon = {
  setMap: (m: NaverMap | null) => void;
  setOptions: (k: keyof NaverPolygonOptions | NaverPolygonOptions, v?: unknown) => void;
};

interface FeatureProps { code: string; name: string; nameEng: string }
interface Feature { type: "Feature"; properties: FeatureProps; geometry: { type: "Polygon" | "MultiPolygon"; coordinates: number[][][] | number[][][][] } }

interface KoreaMapNaverProps {
  data: Record<RegionCode, DistrictData>;
  lang: Lang;
  selected?: RegionCode;
  onSelect?: (code: RegionCode) => void;
  height?: number;
}

const RISK_HEX: Record<number, string> = {
  1: "#009E73", // safe
  2: "#E69F00", // caution
  3: "#D55E00", // warning
  4: "#CC0000", // alert
};

const SDK_LOADING: { promise: Promise<void> | null } = { promise: null };

function loadNaverSdk(keyId: string, useClientId: boolean): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("ssr"));
  if (window.naver?.maps) return Promise.resolve();
  if (SDK_LOADING.promise) return SDK_LOADING.promise;
  SDK_LOADING.promise = new Promise<void>((resolve, reject) => {
    const param = useClientId ? "ncpClientId" : "ncpKeyId";
    const s = document.createElement("script");
    s.src = `https://oapi.map.naver.com/openapi/v3/maps.js?${param}=${encodeURIComponent(keyId)}`;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("naver maps sdk failed to load"));
    document.head.appendChild(s);
  });
  return SDK_LOADING.promise;
}

export function KoreaMapNaver({ data, lang, selected, onSelect, height = 480 }: KoreaMapNaverProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<NaverMap | null>(null);
  const polysRef = useRef<Map<RegionCode, NaverPolygon>>(new Map());
  const featuresRef = useRef<Feature[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [errMsg, setErrMsg] = useState<string>("");

  const keyId =
    process.env.NEXT_PUBLIC_NAVER_MAPS_KEY_ID ||
    process.env.NEXT_PUBLIC_NAVER_MAPS_CLIENT_ID ||
    "";
  const useClientId = !process.env.NEXT_PUBLIC_NAVER_MAPS_KEY_ID && !!process.env.NEXT_PUBLIC_NAVER_MAPS_CLIENT_ID;

  // 1) SDK + GeoJSON 로드 → 맵 초기화 + 폴리곤 생성 (1회)
  useEffect(() => {
    if (!keyId) {
      setStatus("error");
      setErrMsg("NEXT_PUBLIC_NAVER_MAPS_KEY_ID 미설정 — .env.local 확인");
      return;
    }
    if (!containerRef.current) return;
    setStatus("loading");

    let cancelled = false;
    Promise.all([
      loadNaverSdk(keyId, useClientId),
      fetch("/korea-sido.geojson").then((r) => r.json()),
    ])
      .then(([, gj]: [void, { features: Feature[] }]) => {
        if (cancelled || !containerRef.current || !window.naver) return;
        const N = window.naver.maps;

        const map = new N.Map(containerRef.current, {
          center: new N.LatLng(36.0, 127.7),
          zoom: 7,
          minZoom: 6,
          maxZoom: 12,
          zoomControl: true,
          mapTypeControl: false,
          scaleControl: false,
          logoControl: true,
          mapDataControl: false,
        });
        mapRef.current = map;
        featuresRef.current = gj.features;

        // 폴리곤 생성
        const bounds = new N.LatLngBounds();
        gj.features.forEach((f) => {
          const code = f.properties.code as RegionCode;
          const paths = polygonsFromGeometry(f.geometry, N);
          paths.forEach((ring) => ring.forEach((ll) => bounds.extend(ll)));
          const info = data[code];
          const risk = info?.risk ?? 1;
          const poly = new N.Polygon({
            map,
            paths,
            fillColor: RISK_HEX[risk],
            fillOpacity: 0.5,
            strokeColor: code === selected ? "#000" : "#FFF",
            strokeOpacity: 1,
            strokeWeight: code === selected ? 2.4 : 1,
            clickable: true,
          });
          N.Event.addListener(poly, "click", () => onSelect?.(code));
          N.Event.addListener(poly, "mouseover", () => {
            poly.setOptions({ fillOpacity: 0.75 } as Partial<NaverPolygonOptions> as NaverPolygonOptions);
          });
          N.Event.addListener(poly, "mouseout", () => {
            poly.setOptions({ fillOpacity: 0.5 } as Partial<NaverPolygonOptions> as NaverPolygonOptions);
          });
          polysRef.current.set(code, poly);
        });
        map.fitBounds(bounds);
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("error");
        setErrMsg(err?.message ?? "init failed");
      });

    return () => {
      cancelled = true;
      polysRef.current.forEach((p) => {
        try { p.setMap(null); } catch { /* SDK 내부 race — 무시 */ }
      });
      polysRef.current.clear();
      mapRef.current = null;
    };
    // 1회만 (key, useClientId 변할 일 없음)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyId]);

  // 2) data(risk) 변경 시 색상만 업데이트
  useEffect(() => {
    if (status !== "ready") return;
    polysRef.current.forEach((poly, code) => {
      const risk = data[code]?.risk ?? 1;
      poly.setOptions({ fillColor: RISK_HEX[risk] } as NaverPolygonOptions);
    });
  }, [data, status]);

  // 3) selected 변경 시 stroke 강조
  useEffect(() => {
    if (status !== "ready") return;
    polysRef.current.forEach((poly, code) => {
      const isSel = code === selected;
      poly.setOptions({
        strokeColor: isSel ? "#000" : "#FFF",
        strokeWeight: isSel ? 2.4 : 1,
      } as NaverPolygonOptions);
    });
  }, [selected, status]);

  const wrapStyle: CSSProperties = {
    position: "relative",
    width: "100%",
    height,
    borderRadius: 8,
    overflow: "hidden",
    background: "var(--bg-sub)",
  };

  return (
    <div style={wrapStyle} aria-label={lang === "en" ? "Korea risk map (Naver basemap)" : "전국 17개 시도 위험도 (네이버 지도)"}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      {status !== "ready" && (
        <div
          style={{
            position: "absolute", inset: 0, display: "grid", placeItems: "center",
            color: "var(--text-secondary, #888)", fontSize: 13, fontFamily: "var(--font-sans)",
            background: "rgba(255,255,255,0.7)",
            pointerEvents: "none",
          }}
        >
          {status === "error" ? `지도 로드 실패 — ${errMsg}` : "네이버 지도 로딩 중…"}
        </div>
      )}
    </div>
  );
}

// GeoJSON geometry → naver.maps.LatLng[][] 변환
function polygonsFromGeometry(
  g: Feature["geometry"],
  N: NaverNS["maps"],
): NaverLatLng[][] {
  if (g.type === "Polygon") {
    const poly = g.coordinates as number[][][];
    return poly.map((ring) => ring.map(([lng, lat]) => new N.LatLng(lat, lng)));
  }
  // MultiPolygon — 외곽 ring 들만 모아서 단일 폴리곤 옵션으로 (네이버 Polygon은 paths가 다중 ring 지원)
  const multi = g.coordinates as number[][][][];
  return multi.flatMap((poly) =>
    poly.map((ring) => ring.map(([lng, lat]) => new N.LatLng(lat, lng))),
  );
}
