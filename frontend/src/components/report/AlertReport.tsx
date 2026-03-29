"use client";
import useSWR from "swr";
import { fetchCurrentAlert } from "@/lib/api";

const LEVEL_STYLES: Record<string, string> = {
  GREEN:  "bg-green-900/50 border-green-700 text-green-300",
  YELLOW: "bg-yellow-900/50 border-yellow-600 text-yellow-300",
  RED:    "bg-red-900/50 border-red-600 text-red-300",
};

export default function AlertReport() {
  const { data, isLoading } = useSWR("/api/v1/alerts/current", fetchCurrentAlert, { refreshInterval: 60_000 });

  const level = data?.alert_level ?? "GREEN";
  const style = LEVEL_STYLES[level] ?? LEVEL_STYLES.GREEN;

  return (
    <div className="flex flex-col gap-4 h-full">
      <h2 className="text-sm font-semibold text-gray-300">경보 현황</h2>

      {/* 경보 레벨 */}
      <div className={`rounded-lg border px-4 py-3 text-center font-bold text-lg ${style}`}>
        {isLoading ? "로딩 중..." : `● ${level}`}
      </div>

      {/* 신호별 점수 */}
      <div className="space-y-2">
        {[
          { label: "Layer 1 · OTC 구매", key: "l1_score", color: "bg-blue-500" },
          { label: "Layer 2 · 하수 바이오마커", key: "l2_score", color: "bg-emerald-500" },
          { label: "Layer 3 · 검색어 트렌드", key: "l3_score", color: "bg-purple-500" },
        ].map(({ label, key, color }) => {
          const score = data?.[key] ?? 0;
          return (
            <div key={key}>
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>{label}</span>
                <span>{score.toFixed(1)}</span>
              </div>
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${score}%` }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* LLM 요약 */}
      <div className="flex-1 overflow-y-auto">
        <p className="text-xs font-medium text-gray-400 mb-1.5">AI 리포트 요약</p>
        <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
          {isLoading ? "분석 중..." : (data?.summary ?? "데이터 수집 대기 중입니다.")}
        </p>
      </div>

      {data?.generated_at && (
        <p className="text-xs text-gray-600 text-right">
          생성: {new Date(data.generated_at).toLocaleString("ko-KR")}
        </p>
      )}
    </div>
  );
}
