/**
 * SSE 실시간 경보 구독 훅.
 *
 * Backend `/api/v1/alerts/stream` 에서 heartbeat + alert event 수신.
 * 수신 시 TanStack Query 의 ['alerts', 'current'] 캐시 invalidate.
 */

"use client";

import { useEffect } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useQueryClient } from "@tanstack/react-query";
import { AlertEventSchema } from "@/types/alert";

const SSE_URL = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/alerts/stream`;

export function useAlertStream() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const controller = new AbortController();

    fetchEventSource(SSE_URL, {
      signal: controller.signal,
      onmessage(ev) {
        if (ev.event === "heartbeat") return;
        if (ev.event === "alert") {
          const parsed = AlertEventSchema.safeParse(JSON.parse(ev.data));
          if (parsed.success) {
            queryClient.invalidateQueries({ queryKey: ["alerts", "current"] });
          }
        }
      },
      onerror(err) {
        console.error("[useAlertStream]", err);
        return 5_000;
      },
    });

    return () => controller.abort();
  }, [queryClient]);
}
