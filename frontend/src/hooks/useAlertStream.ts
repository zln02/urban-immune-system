"use client";
import { useState, useCallback, useRef } from "react";

const BACKEND = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

interface AlertStreamResult {
  text: string;
  streaming: boolean;
  done: boolean;
  error: string | null;
  start: () => void;
  reset: () => void;
}

export function useAlertStream(region: string): AlertStreamResult {
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sseRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => {
    sseRef.current?.close();
    setText("");
    setDone(false);
    setError(null);
    setStreaming(false);
  }, []);

  const start = useCallback(() => {
    sseRef.current?.close();
    setText("");
    setDone(false);
    setError(null);
    setStreaming(true);

    const url = `${BACKEND}/api/v1/alerts/stream?region=${encodeURIComponent(region)}`;
    const sse = new EventSource(url);
    sseRef.current = sse;

    sse.onmessage = (e: MessageEvent<string>) => {
      if (e.data === "[DONE]") {
        setStreaming(false);
        setDone(true);
        sse.close();
        return;
      }
      try {
        const parsed = JSON.parse(e.data) as { text?: string; error?: string };
        if (parsed.error) {
          setError(parsed.error);
          setStreaming(false);
          sse.close();
          return;
        }
        if (parsed.text) {
          setText((prev) => prev + parsed.text);
        }
      } catch {
        // ignore malformed chunks
      }
    };

    sse.onerror = () => {
      setError("SSE 연결 오류가 발생했습니다.");
      setStreaming(false);
      sse.close();
    };
  }, [region]);

  return { text, streaming, done, error, start, reset };
}
