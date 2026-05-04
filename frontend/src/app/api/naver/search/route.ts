/**
 * Naver DataLab 검색어 트렌드 (L3 Search) 프록시
 * - 독감/감기 증상 키워드 5종 묶음
 */
import { NextRequest, NextResponse } from "next/server";

const NAVER_DATALAB_SEARCH = "https://openapi.naver.com/v1/datalab/search";

const NAVER_HEADERS = {
  "X-Naver-Client-Id": process.env.NAVER_CLIENT_ID ?? "",
  "X-Naver-Client-Secret": process.env.NAVER_CLIENT_SECRET ?? "",
  "Content-Type": "application/json",
};

const SYMPTOM_KEYWORDS = ["독감 증상", "인플루엔자", "고열 원인", "몸살 원인", "타미플루"];

function getDateRange(weeks = 12): { startDate: string; endDate: string } {
  const end = new Date();
  const start = new Date(end.getTime() - weeks * 7 * 24 * 60 * 60 * 1000);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { startDate: fmt(start), endDate: fmt(end) };
}

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const weeks = Math.min(52, Math.max(4, Number(searchParams.get("weeks") ?? 12)));

  if (!process.env.NAVER_CLIENT_ID || !process.env.NAVER_CLIENT_SECRET) {
    return NextResponse.json({ error: "Naver API credentials not configured" }, { status: 503 });
  }

  const { startDate, endDate } = getDateRange(weeks);

  const payload = {
    startDate,
    endDate,
    timeUnit: "week",
    keywordGroups: [
      { groupName: "독감증상", keywords: SYMPTOM_KEYWORDS },
    ],
  };

  try {
    const res = await fetch(NAVER_DATALAB_SEARCH, {
      method: "POST",
      headers: NAVER_HEADERS,
      body: JSON.stringify(payload),
      next: { revalidate: 3600 },
    });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json({ error: `Naver API error ${res.status}`, detail: text }, { status: res.status });
    }

    const data = await res.json();
    const results = (data.results ?? []) as Array<{ data: Array<{ period: string; ratio: number }> }>;

    if (!results.length) {
      return NextResponse.json({ series: [], startDate, endDate });
    }

    const raw = results[0].data;
    const values = raw.map((p) => p.ratio);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const normalized = max > min ? values.map((v) => (v - min) / (max - min)) : values.map(() => 0.5);

    const series = raw.map((p, i) => ({
      date: p.period,
      raw: p.ratio,
      value: normalized[i],
    }));

    return NextResponse.json({ series, startDate, endDate, layer: "search" });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "unknown";
    return NextResponse.json({ error: "Fetch failed", detail: msg }, { status: 502 });
  }
}
