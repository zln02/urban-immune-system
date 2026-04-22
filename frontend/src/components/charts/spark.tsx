interface SparkProps {
  data: readonly number[];
  color?: string;
  width?: number;
  height?: number;
}

/**
 * KPI 카드 보조 스파크라인. `aria-hidden` 처리 (장식용 데이터 반복).
 */
export function Spark({ data, color = "var(--accent)", width = 120, height = 28 }: SparkProps) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const path = data
    .map((v, i) =>
      `${i === 0 ? "M" : "L"} ${(i / (data.length - 1)) * width} ${
        height - ((v - min) / range) * (height - 4) - 2
      }`,
    )
    .join(" ");
  return (
    <svg width={width} height={height} style={{ display: "block" }} aria-hidden>
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}
