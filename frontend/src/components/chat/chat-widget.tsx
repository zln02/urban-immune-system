"use client";

import { useState, useEffect, useRef, useCallback, type CSSProperties } from "react";
import type { Lang } from "@/lib/i18n";
import { API_BASE } from "@/lib/api";

// ── 상수 ──────────────────────────────────────────────────────────────────
const STORAGE_KEY = "uis_chat_history";
const MAX_HISTORY = 10;
const MAX_INPUT_LEN = 300;
const CHAT_ENDPOINT = `${API_BASE}/api/v1/chat/ask`;

const GREETING: Record<Lang, string> = {
  ko: "안녕하세요! UIS의 동작 방식이 궁금하신가요?\n파이프라인·경보·ML 모델 등 시스템 전반을 안내드릴 수 있어요.",
  en: "Hello! Curious about how UIS works?\nI can explain the pipeline, alert logic, ML models, and more.",
};

const PLACEHOLDER: Record<Lang, string> = {
  ko: "질문을 입력하세요 (Enter 전송 / Shift+Enter 줄바꿈)",
  en: "Ask a question (Enter to send / Shift+Enter for newline)",
};

const TITLE: Record<Lang, string> = { ko: "UIS 안내 챗봇", en: "UIS Guide Bot" };
const SUBTITLE: Record<Lang, string> = {
  ko: "Claude Haiku · 시스템 안내 전용",
  en: "Claude Haiku · system guide only",
};
const SEND_LABEL: Record<Lang, string> = { ko: "전송", en: "Send" };
const CLEAR_LABEL: Record<Lang, string> = { ko: "기록 지우기", en: "Clear chat" };

const QUICK_REPLIES: Record<Lang, string[]> = {
  ko: [
    "L1·L2·L3가 뭐예요?",
    "경보 레벨은 어떻게 결정되나요?",
    "F1 0.84는 어떤 의미인가요?",
  ],
  en: [
    "What are L1/L2/L3?",
    "How is the alert level decided?",
    "What does F1 0.84 mean?",
  ],
};

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

function clearHistory(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* noop */
  }
}

// ── 컴포넌트 ──────────────────────────────────────────────────────────────
export function ChatWidget({ lang }: ChatWidgetProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pulseFab, setPulseFab] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 첫 마운트: 로컬스토리지 복원 + 인삿말. FAB 펄스는 6초 후 자동 정지.
  useEffect(() => {
    const stored = loadHistory();
    if (stored.length === 0) {
      setMessages([{ role: "assistant", content: GREETING[lang] }]);
    } else {
      setMessages(stored);
    }
    const t = window.setTimeout(() => setPulseFab(false), 6000);
    return () => window.clearTimeout(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 언어 변경 시 히스토리가 비어 있으면 인삿말 갱신
  useEffect(() => {
    setMessages((prev) => {
      if (
        prev.length === 1 &&
        prev[0].role === "assistant" &&
        Object.values(GREETING).includes(prev[0].content)
      ) {
        return [{ role: "assistant", content: GREETING[lang] }];
      }
      return prev;
    });
  }, [lang]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (open) {
      setPulseFab(false);
      window.setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [open]);

  const sendText = useCallback(
    async (text: string) => {
      const trimmed = text.trim().slice(0, MAX_INPUT_LEN);
      if (!trimmed || loading) return;

      const userMsg: ChatMessage = { role: "user", content: trimmed };
      const nextMessages = [...messages, userMsg];
      setMessages(nextMessages);
      setInput("");
      setError(null);
      setLoading(true);

      const history = nextMessages.slice(-MAX_HISTORY - 1, -1);

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

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

        const finalMessages: ChatMessage[] = [
          ...nextMessages,
          { role: "assistant", content: accumulated },
        ];
        saveHistory(finalMessages);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setError(
          lang === "ko"
            ? "연결 오류가 발생했어요. 잠시 후 다시 시도해주세요."
            : "Connection error. Please try again."
        );
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setLoading(false);
      }
    },
    [loading, messages, lang]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText(input);
    }
  };

  const handleClear = () => {
    abortRef.current?.abort();
    clearHistory();
    setMessages([{ role: "assistant", content: GREETING[lang] }]);
    setError(null);
  };

  const showQuickReplies =
    !loading &&
    messages.length === 1 &&
    messages[0].role === "assistant" &&
    Object.values(GREETING).includes(messages[0].content);

  const inputLen = input.length;
  const canSend = !loading && input.trim().length > 0;

  return (
    <>
      {/* ── Floating 버튼 ─────────────────────────────── */}
      <button
        type="button"
        aria-label={TITLE[lang]}
        onClick={() => setOpen((v) => !v)}
        style={{
          ...fabStyle,
          animation: pulseFab && !open ? "uis-fab-pulse 1.8s ease-out 2" : undefined,
          transform: open ? "rotate(90deg)" : "rotate(0)",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = open ? "rotate(90deg) scale(1.06)" : "scale(1.06)")}
        onMouseLeave={(e) => (e.currentTarget.style.transform = open ? "rotate(90deg)" : "scale(1)")}
        title={TITLE[lang]}
      >
        {open ? <IconClose /> : <IconChat />}
      </button>

      {/* ── 채팅 카드 ──────────────────────────────────── */}
      {open && (
        <div style={cardStyle} role="dialog" aria-label={TITLE[lang]}>
          {/* 헤더 */}
          <div style={headerStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={botBadge}>🛡️</div>
              <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{TITLE[lang]}</span>
                <span style={{ fontSize: 10.5, opacity: 0.78, fontWeight: 400 }}>
                  <span style={statusDot} /> {SUBTITLE[lang]}
                </span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              <button
                type="button"
                aria-label={CLEAR_LABEL[lang]}
                title={CLEAR_LABEL[lang]}
                onClick={handleClear}
                style={iconBtn}
              >
                <IconTrash />
              </button>
              <button
                type="button"
                aria-label="닫기"
                title="닫기"
                onClick={() => setOpen(false)}
                style={iconBtn}
              >
                <IconX />
              </button>
            </div>
          </div>

          {/* 메시지 리스트 */}
          <div style={msgListStyle}>
            {messages.map((msg, i) => (
              <div key={i} style={bubbleWrap(msg.role)}>
                {msg.role === "assistant" && <div style={avatarStyle}>🛡️</div>}
                <div style={bubble(msg.role)}>
                  {msg.content || <TypingDots />}
                </div>
              </div>
            ))}
            {loading && messages[messages.length - 1]?.content === "" && (
              <div style={{ paddingLeft: 36, marginTop: -4, fontSize: 10.5, color: "var(--text-tertiary)" }}>
                {lang === "ko" ? "생각 중…" : "thinking…"}
              </div>
            )}

            {showQuickReplies && (
              <div style={quickRepliesWrap}>
                {QUICK_REPLIES[lang].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => sendText(q)}
                    style={chipStyle}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--primary-70)", e.currentTarget.style.color = "#fff")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "var(--surface)", e.currentTarget.style.color = "var(--primary-70)")}
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            {error && <div style={errorBanner}>⚠ {error}</div>}
            <div ref={bottomRef} />
          </div>

          {/* 입력창 */}
          <div style={inputAreaStyle}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, MAX_INPUT_LEN))}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder={PLACEHOLDER[lang]}
              disabled={loading}
              style={textareaStyle}
              aria-label={PLACEHOLDER[lang]}
            />
            <button
              type="button"
              onClick={() => sendText(input)}
              disabled={!canSend}
              style={sendBtnStyle(!canSend)}
              aria-label={SEND_LABEL[lang]}
              title={SEND_LABEL[lang]}
            >
              {loading ? <Spinner small /> : <IconSend />}
            </button>
          </div>
          <div style={footerHint}>
            <span>{inputLen}/{MAX_INPUT_LEN}</span>
            <span style={{ opacity: 0.7 }}>
              {lang === "ko" ? "AI 답변은 참고용입니다" : "AI answers are advisory"}
            </span>
          </div>
        </div>
      )}
    </>
  );
}

// ── 아이콘 (인라인 SVG) ────────────────────────────────────────────────────
function IconChat() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
function IconClose() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}
function IconX() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}
function IconTrash() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
    </svg>
  );
}
function IconSend() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  );
}

// ── 타이핑 닷 / 스피너 ─────────────────────────────────────────────────────
function TypingDots() {
  return (
    <span style={{ display: "inline-flex", gap: 4, alignItems: "center", padding: "2px 0" }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "var(--text-secondary)",
            display: "inline-block",
            animation: `uis-typing 1.2s ease-in-out ${i * 0.15}s infinite`,
          }}
        />
      ))}
    </span>
  );
}

function Spinner({ small }: { small?: boolean }) {
  const size = small ? 14 : 16;
  return (
    <span
      aria-label="로딩 중"
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: `2px solid rgba(255,255,255,0.35)`,
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
  width: 58,
  height: 58,
  borderRadius: "50%",
  background: "linear-gradient(135deg, var(--primary-30) 0%, var(--primary-90) 100%)",
  color: "#fff",
  border: "none",
  cursor: "pointer",
  display: "grid",
  placeItems: "center",
  boxShadow: "0 6px 20px rgba(30, 58, 138, 0.35)",
  zIndex: 9999,
  transition: "transform 0.18s ease, box-shadow 0.18s ease",
};

const cardStyle: CSSProperties = {
  position: "fixed",
  bottom: 100,
  right: 28,
  width: 360,
  height: 540,
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 16,
  boxShadow: "0 18px 48px rgba(15, 23, 42, 0.18), 0 4px 12px rgba(15, 23, 42, 0.08)",
  zIndex: 9998,
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
  fontFamily: "var(--font-sans)",
  animation: "uis-chat-pop 0.22s ease-out",
  transformOrigin: "bottom right",
};

const headerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "12px 14px",
  background: "linear-gradient(135deg, var(--primary-30) 0%, var(--primary-90) 100%)",
  color: "#fff",
  flexShrink: 0,
};

const botBadge: CSSProperties = {
  width: 32,
  height: 32,
  borderRadius: "50%",
  background: "rgba(255, 255, 255, 0.16)",
  display: "grid",
  placeItems: "center",
  fontSize: 16,
  flexShrink: 0,
};

const statusDot: CSSProperties = {
  display: "inline-block",
  width: 6,
  height: 6,
  borderRadius: "50%",
  background: "var(--risk-safe)",
  marginRight: 5,
  verticalAlign: "middle",
  boxShadow: "0 0 0 2px rgba(0, 158, 115, 0.25)",
};

const iconBtn: CSSProperties = {
  width: 26,
  height: 26,
  background: "rgba(255, 255, 255, 0.12)",
  border: "none",
  borderRadius: 6,
  color: "#fff",
  cursor: "pointer",
  display: "grid",
  placeItems: "center",
  transition: "background 0.15s",
};

const msgListStyle: CSSProperties = {
  flex: 1,
  overflowY: "auto",
  padding: "14px 12px",
  display: "flex",
  flexDirection: "column",
  gap: 10,
  background: "var(--bg-sub)",
};

function bubbleWrap(role: "user" | "assistant"): CSSProperties {
  return {
    display: "flex",
    justifyContent: role === "user" ? "flex-end" : "flex-start",
    alignItems: "flex-end",
    gap: 6,
  };
}

const avatarStyle: CSSProperties = {
  width: 26,
  height: 26,
  borderRadius: "50%",
  background: "linear-gradient(135deg, var(--primary-30), var(--primary-90))",
  color: "#fff",
  display: "grid",
  placeItems: "center",
  fontSize: 13,
  flexShrink: 0,
  boxShadow: "0 2px 6px rgba(30, 58, 138, 0.25)",
};

function bubble(role: "user" | "assistant"): CSSProperties {
  const isUser = role === "user";
  return {
    maxWidth: "78%",
    padding: "9px 13px",
    borderRadius: isUser ? "14px 14px 2px 14px" : "14px 14px 14px 2px",
    background: isUser
      ? "linear-gradient(135deg, var(--primary-30), var(--primary-70))"
      : "var(--surface)",
    color: isUser ? "#fff" : "var(--text)",
    fontSize: 13.5,
    lineHeight: 1.55,
    wordBreak: "break-word",
    whiteSpace: "pre-wrap",
    boxShadow: isUser
      ? "0 2px 8px rgba(30, 58, 138, 0.22)"
      : "0 1px 3px rgba(15, 23, 42, 0.08)",
    border: isUser ? "none" : "1px solid var(--border)",
  };
}

const quickRepliesWrap: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  marginTop: 4,
  paddingLeft: 32,
};

const chipStyle: CSSProperties = {
  alignSelf: "flex-start",
  padding: "6px 11px",
  background: "var(--surface)",
  color: "var(--primary-70)",
  border: "1px solid var(--primary-70)",
  borderRadius: 14,
  fontSize: 12,
  fontWeight: 500,
  cursor: "pointer",
  fontFamily: "inherit",
  transition: "background 0.15s, color 0.15s",
  textAlign: "left",
};

const errorBanner: CSSProperties = {
  padding: "8px 12px",
  background: "#fef2f2",
  color: "#b91c1c",
  borderRadius: 8,
  fontSize: 12,
  border: "1px solid #fecaca",
};

const inputAreaStyle: CSSProperties = {
  borderTop: "1px solid var(--border)",
  padding: "10px 12px 6px",
  display: "flex",
  gap: 8,
  alignItems: "flex-end",
  flexShrink: 0,
  background: "var(--surface)",
};

const textareaStyle: CSSProperties = {
  flex: 1,
  resize: "none",
  border: "1px solid var(--border)",
  borderRadius: 10,
  padding: "8px 10px",
  fontSize: 13,
  fontFamily: "inherit",
  background: "var(--bg-sub)",
  color: "var(--text)",
  lineHeight: 1.45,
  outline: "none",
  maxHeight: 96,
  minHeight: 36,
};

function sendBtnStyle(disabled: boolean): CSSProperties {
  return {
    width: 38,
    height: 38,
    background: disabled
      ? "var(--border)"
      : "linear-gradient(135deg, var(--primary-30), var(--primary-90))",
    color: disabled ? "var(--text-tertiary)" : "#fff",
    border: "none",
    borderRadius: 10,
    cursor: disabled ? "not-allowed" : "pointer",
    fontFamily: "inherit",
    flexShrink: 0,
    display: "grid",
    placeItems: "center",
    transition: "transform 0.12s, box-shadow 0.12s",
    boxShadow: disabled ? "none" : "0 3px 10px rgba(30, 58, 138, 0.28)",
  };
}

const footerHint: CSSProperties = {
  padding: "0 14px 8px",
  display: "flex",
  justifyContent: "space-between",
  fontSize: 10,
  color: "var(--text-tertiary)",
  background: "var(--surface)",
};
