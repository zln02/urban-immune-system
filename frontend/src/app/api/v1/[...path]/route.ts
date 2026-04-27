// 백엔드 FastAPI 프록시 — 외부 클라이언트가 8001 차단 환경에서도 동작.
// 클라이언트가 같은 origin (Next.js 3000) 으로 /api/v1/* 호출 → Next.js 가 받아
// 내부망 UIS_API_INTERNAL_URL (기본 http://localhost:8001) 로 중계한다.

import type { NextRequest } from "next/server";

const BACKEND = process.env.UIS_API_INTERNAL_URL || "http://localhost:8001";

async function proxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await params;
  const subPath = path.join("/");
  const search = req.nextUrl.search;
  const target = `${BACKEND}/api/v1/${subPath}${search}`;

  const headers: Record<string, string> = {};
  const ct = req.headers.get("content-type");
  if (ct) headers["content-type"] = ct;

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = Buffer.from(await req.arrayBuffer());
  }

  const upstream = await fetch(target, init);
  const upstreamCt = upstream.headers.get("content-type") || "application/json";
  const isStream = upstreamCt.includes("text/event-stream");

  const respHeaders: Record<string, string> = {
    "content-type": upstreamCt,
    "cache-control": "no-store",
  };
  if (isStream) {
    respHeaders["x-accel-buffering"] = "no";
    respHeaders["connection"] = "keep-alive";
  }

  // SSE / 청크 응답은 buffer 금지 — body 스트림 그대로 통과
  return new Response(upstream.body, {
    status: upstream.status,
    headers: respHeaders,
  });
}

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
};
