"use client";
import { useState } from "react";
import DeckGL from "@deck.gl/react";
import { HexagonLayer } from "@deck.gl/aggregation-layers";
import { Map } from "react-map-gl";

// 서울 구별 더미 위험도 데이터 (실 데이터는 /api/v1/signals/latest 에서 조회)
const DUMMY_DATA = [
  { coordinates: [126.9784, 37.5665], weight: 75 }, // 중구
  { coordinates: [126.9388, 37.5172], weight: 45 }, // 관악구
  { coordinates: [127.0276, 37.5113], weight: 60 }, // 강남구
  { coordinates: [126.8897, 37.5491], weight: 30 }, // 양천구
  { coordinates: [127.0831, 37.5133], weight: 55 }, // 송파구
];

const INITIAL_VIEW = {
  longitude: 126.978,
  latitude: 37.566,
  zoom: 11,
  pitch: 50,
  bearing: 0,
};

export default function RiskMap() {
  const [viewState, setViewState] = useState(INITIAL_VIEW);

  const layer = new HexagonLayer({
    id: "risk-hexagon",
    data: DUMMY_DATA,
    getPosition: (d) => d.coordinates as [number, number],
    getElevationWeight: (d) => d.weight,
    elevationScale: 500,
    extruded: true,
    radius: 600,
    colorRange: [
      [0, 200, 120, 200],
      [100, 220, 100, 200],
      [240, 200, 0, 220],
      [240, 120, 0, 230],
      [220, 40, 40, 250],
    ],
    pickable: true,
  });

  return (
    <div className="relative w-full h-full">
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) => setViewState(vs as typeof INITIAL_VIEW)}
        controller
        layers={[layer]}
      >
        {/* Mapbox token 필요 — 없을 때는 빈 배경 */}
        {process.env.NEXT_PUBLIC_MAPBOX_TOKEN && (
          <Map
            mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
            mapStyle="mapbox://styles/mapbox/dark-v11"
          />
        )}
      </DeckGL>
      <div className="absolute top-3 left-3 bg-gray-900/80 rounded-lg px-3 py-2 text-xs text-gray-300">
        3D 위험도 맵 · 서울특별시 구별
      </div>
    </div>
  );
}
