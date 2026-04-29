/**
 * 시계열 시간축 정렬 유틸 — ISO 주차(월요일 KST) 단위로 여러 시리즈를 공통 축에 매핑한다.
 *
 * 사용 이유:
 *   L1(otc 12주) · L2(wastewater 1년) · L3(search 12주) 시리즈는 길이가 달라
 *   같은 X 픽셀에 다른 날짜가 그려지는 시각적 거짓 정렬을 만든다.
 *   공통 주간 축에 align 한 뒤 missing 은 null 로 두면 차트가 정직해진다.
 */

export interface DatedPoint {
  date: string; // ISO 또는 YYYY-MM-DD
  value: number;
}

export interface AlignedSeries<K extends string> {
  /** 정렬된 공통 주간 키 (월요일 YYYY-MM-DD) */
  dates: string[];
  /** 각 시리즈를 dates 와 동일 길이로 매핑. 해당 주에 데이터 없으면 null. */
  series: Record<K, (number | null)[]>;
}

/** YYYY-MM-DD 또는 ISO 문자열을 그 주차의 월요일(KST 기준 단순화) 로 정규화 */
export function toWeekStart(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const day = d.getDay(); // 일=0, 월=1, ..., 토=6
  const offset = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + offset);
  d.setHours(0, 0, 0, 0);
  const yy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
}

/**
 * 여러 시리즈를 주간 키 union 위에 정렬. 같은 주에 여러 관측이 있으면 평균.
 *
 * @param inputs key → 그 시리즈의 (date, value) 포인트 배열
 * @returns dates(공통 주간 축, 오름차순) + series(각 키별 number|null 배열)
 */
export function alignByWeek<K extends string>(
  inputs: Record<K, DatedPoint[]>
): AlignedSeries<K> {
  const keySet = new Set<string>();
  const buckets = {} as Record<K, Map<string, { sum: number; n: number }>>;

  (Object.keys(inputs) as K[]).forEach((name) => {
    const m = new Map<string, { sum: number; n: number }>();
    for (const p of inputs[name]) {
      if (!Number.isFinite(p.value)) continue;
      const wk = toWeekStart(p.date);
      const cur = m.get(wk);
      if (cur) {
        cur.sum += p.value;
        cur.n += 1;
      } else {
        m.set(wk, { sum: p.value, n: 1 });
      }
      keySet.add(wk);
    }
    buckets[name] = m;
  });

  const dates = Array.from(keySet).sort();

  const series = {} as Record<K, (number | null)[]>;
  (Object.keys(inputs) as K[]).forEach((name) => {
    const m = buckets[name];
    series[name] = dates.map((wk) => {
      const cell = m.get(wk);
      return cell ? cell.sum / cell.n : null;
    });
  });

  return { dates, series };
}

/** 끝에서 N개 주 만큼 자른다. weeks 가 null/undefined 면 전체 반환 */
export function tailWeeks<K extends string>(
  aligned: AlignedSeries<K>,
  weeks: number | null | undefined
): AlignedSeries<K> {
  if (weeks == null || weeks <= 0 || weeks >= aligned.dates.length) return aligned;
  const start = aligned.dates.length - weeks;
  const dates = aligned.dates.slice(start);
  const series = {} as Record<K, (number | null)[]>;
  (Object.keys(aligned.series) as K[]).forEach((k) => {
    series[k] = aligned.series[k].slice(start);
  });
  return { dates, series };
}
