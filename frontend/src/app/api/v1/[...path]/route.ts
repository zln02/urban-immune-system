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
  const body = await upstream.arrayBuffer();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "content-type":
        upstream.headers.get("content-type") || "application/json",
      "cache-control": "no-store",
    },
  });
}

export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
};
