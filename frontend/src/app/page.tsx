import RiskMap from "@/components/map/RiskMap";
import TrendChart from "@/components/charts/TrendChart";
import AlertReport from "@/components/report/AlertReport";

export default function DashboardPage() {
  return (
    <main className="flex flex-col gap-6 p-6">
      {/* 헤더 */}
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">🦠 Urban Immune System</h1>
          <p className="text-sm text-gray-400 mt-0.5">AI 기반 감염병 조기경보 시스템 · 서울특별시</p>
        </div>
        <AlertLevelBadge />
      </header>

      {/* 메인 그리드 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 3D 위험도 맵 */}
        <div className="lg:col-span-2 rounded-xl bg-gray-900 border border-gray-800 overflow-hidden" style={{ height: 480 }}>
          <RiskMap />
        </div>

        {/* 경보 리포트 */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <AlertReport />
        </div>
      </div>

      {/* 시계열 차트 */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
        <TrendChart />
      </div>
    </main>
  );
}

function AlertLevelBadge() {
  // TODO: SWR로 /api/v1/alerts/current 폴링
  return (
    <span className="px-3 py-1.5 rounded-full text-sm font-semibold bg-green-900 text-green-300 border border-green-700">
      ● GREEN — 정상
    </span>
  );
}
