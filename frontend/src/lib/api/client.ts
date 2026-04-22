/**
 * Backend API 클라이언트 (FastAPI 연동).
 *
 * - 환경변수: NEXT_PUBLIC_API_BASE_URL (기본: http://localhost:8000)
 * - 에러 처리: HTTP 4xx/5xx → ApiError throw
 * - 타임아웃: 10초
 */

import { z } from "zod";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public endpoint: string,
    message: string,
  ) {
    super(`[${status}] ${endpoint}: ${message}`);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);

  try {
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });

    if (!res.ok) {
      throw new ApiError(res.status, path, await res.text());
    }

    return schema.parse(await res.json());
  } finally {
    clearTimeout(timeout);
  }
}
