"use client";

import { useState, useEffect, useRef, useCallback, type CSSProperties } from "react";
import type { Lang } from "@/lib/i18n";
import { API_BASE } from "@/lib/api";

// ── 상수 ──────────────────────────────────────────────────────────────────
const STORAGE_KEY = "uis_chat_history";
const MAX_HISTORY = 10;
const CHAT_ENDPOINT = `${API_BASE}/api/v1/chat/ask`;

const GREETING: Record<Lang, string> = {
  ko: "안녕하세요! UIS의 동작 방식이 궁금하신가요? 파이프라인·경보·ML 모델 등 시스템 전반에 대해 안내드릴 수 있어요.",
  en: "Hello! Curious about how UIS works? I can explain the pipeline, alert logic, ML models, and more.",
};

const PLACEHOLDER: Record<Lang, string> = {
  ko: "💬 시스템 사용법 챗봇 — 질문을 입력하세요",
  en: "💬 System guide chatbot — ask a question",
};

const TITLE: Record<Lang, string> = {
  ko: "UIS 안내 챗봇",
  en: "UIS Guide Bot",
};

const SEND_LABEL: Record<Lang, string> = { ko: "전송", en: "Send" };

// ── 타입 ──────────────────────────────────────────────────────────────────
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatWidgetProps {
  lang: Lang;
}

// ── 로컬스토리지 헬퍼 ──────────────────────────────────────────────────────
function loadHistory(): ChatMessage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatMessage[];
    return parsed.slice(-MAX_HISTORY);
  } catch {
    return [];
  }
}

function saveHistory(msgs: ChatMessage[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-MAX_HISTORY)));
  } catch {
    // localStorage 쓰기 실패 시 silent fail
  }
}

// ── 컴포넌트 ──────────────────────────────────────────────────────────────
export function ChatWidget({ lang }: ChatWidgetProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 첫 마운트: 로컬스토리지에서 히스토리 복원 + 인삿말
  useEffect(() => {
    const stored = loadHistory();
    if (stored.length === 0) {
      setMessages([{ role: "assistant", content: GREETING[lang] }]);
    } else {
      setMessages(stored);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 언어 변경 시 히스토리가 없으면 인삿말 갱신
  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 1 && prev[0].role === "assistant" && Object.values(GREETING).includes(prev[0].content)) {
        return [{ role: "assistant", content: GREETING[lang] }];
      }
      return prev;
    });
  }, [lang]);

  // 메시지 변경 시 스크롤 하단 유지
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // 열릴 때 인풋 포커스
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [open]);

  const sendMessage = useCallback(async () => {
    const trimmed = input.trim().slice(0, 300);
    if (!trimmed || loading) return;

    const userMsg: ChatMessage = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setError(null);
    setLoading(true);

    // API로 넘길 히스토리: 직전 MAX_HISTORY-1건 (user/assistant 교대)
    const history = nextMessages.slice(-MAX_HISTORY - 1, -1);

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // SSE 스트리밍 누적용
    let accumulated = "";
    const assistantPlaceholder: ChatMessage = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantPlaceholder]);

    try {
      const res = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: trimmed, history }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") break;
          try {
            const parsed = JSON.parse(data) as { text?: string; error?: string };
            if (parsed.error) {
              setError(parsed.error);
              break;
            }
            if (parsed.text) {
              accumulated += parsed.text;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: "assistant", content: accumulated };
                return updated;
              });
            }
          } catch {
            // JSON 파싱 실패 라인 무시
          }
        }
      }

      // 최종 히스토리 저장
      const finalMessages: ChatMessage[] = [
        ...nextMessages,
        { role: "assistant", content: accumulated },
      ];
      saveHistory(finalMessages);
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(lang === "ko" ? "연결 오류가 발생했어요. 잠시 후 다시 시도해주세요." : "Connection error. Please try again.");
      // placeholder 제거
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, lang]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* ── Floating 버튼 ─────────────────────────────── */}
      <button
        type="button"
        aria-label={TITLE[lang]}
        onClick={() => setOpen((v) => !v)}
        style={fabStyle}
        title={TITLE[lang]}
      >
        {open ? "✕" : "💬"}
      </button>

      {/* ── 채팅 카드 ──────────────────────────────────── */}
      {open && (
        <div style={cardStyle} role="dialog" aria-label={TITLE[lang]}>
          {/* 헤더 */}
          <div style={headerStyle}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>{TITLE[lang]}</span>
            <button
              type="button"
              aria-label="닫기"
              onClick={() => setOpen(false)}
              style={closeBtn}
            >
              ✕
            </button>
          </div>

          {/* 메시지 리스트 */}
          <div style={msgListStyle}>
            {messages.map((msg, i) => (
              <div key={i} style={bubbleWrap(msg.role)}>
                <div style={bubble(msg.role)}>
                  {msg.content || (
                    <span style={{ opacity: 0.5 }}>…</span>
                  )}
                </div>
              </div>
            ))}
            {loading && messages[messages.length - 1]?.content === "" && (
              <div style={bubbleWrap("assistant")}>
                <div style={{ ...bubble("assistant"), display: "flex", gap: 4, alignItems: "center" }}>
                  <Spinner />
                </div>
              </div>
            )}
            {error && (
              <div style={errorBanner}>{error}</div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* 입력창 */}
          <div style={inputAreaStyle}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, 300))}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder={PLACEHOLDER[lang]}
              disabled={loading}
              style={textareaStyle}
              aria-label={PLACEHOLDER[lang]}
            />
            <button
              type="button"
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              style={sendBtnStyle(loading || !input.trim())}
              aria-label={SEND_LABEL[lang]}
            >
              {loading ? <Spinner small /> : SEND_LABEL[lang]}
            </button>
          </div>
        </div>
      )}
    </>
  );
}

// ── 스피너 ────────────────────────────────────────────────────────────────
function Spinner({ small }: { small?: boolean }) {
  const size = small ? 14 : 16;
  return (
    <span
      aria-label="로딩 중"
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: `2px solid rgba(255,255,255,0.3)`,
        borderTopColor: "#fff",
        borderRadius: "50%",
        animation: "uis-spin 0.7s linear infinite",
      }}
    />
  );
}

// ── 스타일 ────────────────────────────────────────────────────────────────
const fabStyle: CSSProperties = {
  position: "fixed",
  bottom: 28,
  right: 28,
  width: 60,
  height: 60,
  borderRadius: "50%",
  background: "var(--primary-70)",
  color: "#fff",
  border: "none",
  fontSize: 24,
  cursor: "pointer",
  display: "grid",
  placeItems: "center",
  boxShadow: "0 4px 16px rgba(0,0,0,0.25)",
  zIndex: 9999,
  transition: "transform 0.15s",
};

const cardStyle: CSSProperties = {
  position: "fixed",
  bottom: 100,
  right: 28,
  width: 320,
  height: 480,
  background: "var(--surface, #fff)",
  border: "1px solid var(--border, #e0e0e0)",
  borderRadius: 12,
  boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
  zIndex: 9998,
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
  fontFamily: "var(--font-sans, system-ui)",
};

const headerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "10px 14px",
  background: "var(--primary-70)",
  color: "#fff",
  fontSize: 13,
  flexShrink: 0,
};

const closeBtn: CSSProperties = {
  background: "transparent",
  border: "none",
  color: "#fff",
  cursor: "pointer",
  fontSize: 16,
  lineHeight: 1,
  padding: 2,
};

const msgListStyle: CSSProperties = {
  flex: 1,
  overflowY: "auto",
  padding: "12px 10px",
  display: "flex",
  flexDirection: "column",
  gap: 8,
};

function bubbleWrap(role: "user" | "assistant"): CSSProperties {
  return {
    display: "flex",
    justifyContent: role === "user" ? "flex-end" : "flex-start",
  };
}

function bubble(role: "user" | "assistant"): CSSProperties {
  return {
    maxWidth: "80%",
    padding: "8px 11px",
    borderRadius: role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
    background: role === "user" ? "var(--primary-70)" : "var(--bg-sub, #f5f5f5)",
    color: role === "user" ? "#fff" : "var(--text, #111)",
    fontSize: 13,
    lineHeight: 1.5,
    wordBreak: "break-word",
    whiteSpace: "pre-wrap",
  };
}

const errorBanner: CSSProperties = {
  padding: "8px 12px",
  background: "#fee2e2",
  color: "#b91c1c",
  borderRadius: 6,
  fontSize: 12,
};

const inputAreaStyle: CSSProperties = {
  borderTop: "1px solid var(--border, #e0e0e0)",
  padding: "8px 10px",
  display: "flex",
  gap: 8,
  alignItems: "flex-end",
  flexShrink: 0,
  background: "var(--surface, #fff)",
};

const textareaStyle: CSSProperties = {
  flex: 1,
  resize: "none",
  border: "1px solid var(--border, #e0e0e0)",
  borderRadius: 6,
  padding: "6px 8px",
  fontSize: 12,
  fontFamily: "inherit",
  background: "var(--bg-sub, #f5f5f5)",
  color: "var(--text, #111)",
  lineHeight: 1.4,
  outline: "none",
};

function sendBtnStyle(disabled: boolean): CSSProperties {
  return {
    padding: "7px 12px",
    background: disabled ? "var(--border, #e0e0e0)" : "var(--primary-70)",
    color: disabled ? "var(--text-tertiary, #999)" : "#fff",
    border: "none",
    borderRadius: 6,
    cursor: disabled ? "not-allowed" : "pointer",
    fontSize: 12,
    fontWeight: 600,
    fontFamily: "inherit",
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    gap: 4,
    transition: "background 0.15s",
  };
}
