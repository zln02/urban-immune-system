"use client";
import useSWR from "swr";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { fetchSignalTimeseries } from "@/lib/api";

const COLORS = {
  L1: "#60a5fa", // blue — OTC
  L2: "#34d399", // green — 하수
  L3: "#a78bfa", // purple — 검색
  GT: "#f87171", // red — 실제 확진
};

export default function TrendChart() {
  const { data, isLoading } = useSWR("/api/v1/signals/timeseries?weeks=24", fetchSignalTimeseries);

  if (isLoading) return <div className="h-56 flex items-center justify-center text-gray-500 text-sm">로딩 중...</div>;

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 mb-4">3-Layer 신호 시계열 (최근 24주)</h2>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data?.series ?? []}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="week" stroke="#6b7280" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} stroke="#6b7280" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            labelStyle={{ color: "#e5e7eb" }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
          <Line type="monotone" dataKey="L1" name="Layer 1 (OTC)" stroke={COLORS.L1} dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="L2" name="Layer 2 (하수)" stroke={COLORS.L2} dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="L3" name="Layer 3 (검색)" stroke={COLORS.L3} dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="GT" name="실제 확진" stroke={COLORS.GT} dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
