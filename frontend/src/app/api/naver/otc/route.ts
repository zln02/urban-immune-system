/**
 * Naver Shopping Insight (L1 OTC) 프록시
 * - 키는 서버에서만 사용, 클라이언트에 절대 노출하지 않음
 * - NAVER_CLIENT_ID / NAVER_CLIENT_SECRET → .env 관리
 */
import { NextRequest, NextResponse } from "next/server";

const NAVER_DATALAB_SHOPPING = "https://openapi.naver.com/v1/datalab/shopping/categories";

const NAVER_HEADERS = {
  "X-Naver-Client-Id": process.env.NAVER_CLIENT_ID ?? "",
  "X-Naver-Client-Secret": process.env.NAVER_CLIENT_SECRET ?? "",
  "Content-Type": "application/json",
};

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
    category: [
      { name: "OTC감기", param: ["50000008"] }, // 네이버 쇼핑 카테고리: 건강/의약외품
    ],
    device: "",
    ages: [],
    gender: "",
  };

  try {
    const res = await fetch(NAVER_DATALAB_SHOPPING, {
      method: "POST",
      headers: NAVER_HEADERS,
      body: JSON.stringify(payload),
      next: { revalidate: 3600 }, // 1시간 캐시
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

    return NextResponse.json({ series, startDate, endDate, layer: "otc" });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "unknown";
    return NextResponse.json({ error: "Fetch failed", detail: msg }, { status: 502 });
  }
}
