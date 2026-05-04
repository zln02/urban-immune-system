"use client";

import { useState, type ReactNode } from "react";

/**
 * 비전공자용 도움말 툴팁 — ⓘ 아이콘에 hover/focus 시 popover 표시.
 * 미리 정의된 GLOSSARY 키를 쓰거나 직접 텍스트 전달 가능.
 */

export type GlossaryKey =
  | "composite"
  | "alert_level"
  | "layers_above_30"
  | "leadtime"
  | "f1"
  | "recall"
  | "precision"
  | "far"
  | "granger"
  | "ccf"
  | "rag"
  | "sse"
  | "tft"
  | "walk_forward"
  | "audit"
  | "xai"
  | "three_layer";

export const GLOSSARY: Record<GlossaryKey, { title: string; body: string }> = {
  composite: {
    title: "종합 위험도 (composite)",
    body: "약국·하수·검색 3계층 점수를 가중평균(35:40:25)해 0–100으로 만든 한 숫자. 30/55/75 넘으면 노랑/주황/빨강 경보.",
  },
  alert_level: {
    title: "경보 레벨",
    body: "GREEN(<30)·YELLOW(30~55)·ORANGE(55~75)·RED(≥75). 하나만 오르면 무시, 2계층 이상 임계 초과여야 발령.",
  },
  layers_above_30: {
    title: "임계 초과 계층 수",
    body: "약국/하수/검색 중 30점 이상 올라간 신호 개수. 2개 이상이어야 경보 발령 (단일 계층 단독 발령 금지 — 구글 GFT 실패 교훈).",
  },
  leadtime: {
    title: "선행 시간 (lead time)",
    body: "임상 신고(KCDC)가 늘어나기 며칠/몇 주 전에 우리 신호가 먼저 올랐는지. 양수일수록 좋음. 17지역 평균 6.47주(약 45일) 선행.",
  },
  f1: {
    title: "F1 점수",
    body: "정밀도와 재현율을 합친 종합 정확도 (0~1). 1에 가까울수록 좋음. 시간 순 교차검증 기준 0.667 — 무작위 분할 0.85와 직접 비교 금지.",
  },
  recall: {
    title: "재현율 (Recall)",
    body: "진짜로 발생한 사건 중 시스템이 잡아낸 비율. 17지역 평균 0.838 = 진짜 중 약 84% 포착.",
  },
  precision: {
    title: "정밀도 (Precision)",
    body: "시스템이 경보 낸 것 중 실제로 맞았던 비율. 1.000 = 경보 낸 곳 100% 진짜였음.",
  },
  far: {
    title: "False Alert Rate (FAR)",
    body: "전체 평상시 주차 중 잘못 경보를 울린 비율. 낮을수록 좋음. 17지역 평균 0.557 — Phase 2 데이터 품질 개선 후 재측정 예정.",
  },
  granger: {
    title: "Granger 인과검정",
    body: "A의 과거값이 B의 현재값을 통계적으로 예측하는지 검정. p<0.05면 유의. 우리 측정: L3 검색 → 임상 p=0.007 (유의).",
  },
  ccf: {
    title: "CCF (교차상관)",
    body: "두 시계열이 시차를 두고 얼마나 닮았는지 (-1 ~ +1). 1에 가까울수록 좋음. 우리 composite vs 임상 = 0.588.",
  },
  rag: {
    title: "RAG (검색-증강 생성)",
    body: "AI가 답변 전에 WHO·KDCA 가이드 문서를 먼저 찾아본 뒤 그걸 인용해서 글을 씀. 환각 방지 + 출처 증명 (정부 납품 필수).",
  },
  sse: {
    title: "SSE (실시간 글자 전송)",
    body: "Server-Sent Events. 서버가 브라우저로 한 글자씩 흘려보내는 방식. ChatGPT처럼 답변이 한 자씩 나오는 그 효과.",
  },
  tft: {
    title: "TFT (Temporal Fusion Transformer)",
    body: "시계열 예측 전용 딥러닝 모델 (Google 2021). 변수별 중요도와 attention을 함께 출력해 '왜 그렇게 예측했는지' 설명 가능 (XAI).",
  },
  walk_forward: {
    title: "시간 순 교차검증 (walk-forward)",
    body: "AI가 미래를 절대 못 보게 시간 순서로만 학습·평가. 학습/검증 사이 4주 간격(gap=4)을 둬 즉각적 누출도 차단.",
  },
  audit: {
    title: "감사 로그 (audit)",
    body: "누가/언제/어떤 트리거로 경보를 생성했는지 모두 기록. ISMS-P 2.9 인증 필수 항목. 정부 납품 시 감사관 요청 대응.",
  },
  xai: {
    title: "XAI (설명 가능한 AI)",
    body: "AI 결정의 근거를 사람이 이해할 수 있게 표시. 우리 시스템은 변수 중요도·attention·인용 출처를 모두 응답에 포함.",
  },
  three_layer: {
    title: "3계층 (3-Layer)",
    body: "약국 OTC(2주 선행) · 하수 바이러스(3주 선행) · 검색 트렌드(1주 선행) — 사람이 병원 가기 전에 남기는 흔적 3종.",
  },
};

interface InfoTooltipProps {
  term?: GlossaryKey;
  title?: string;
  body?: string;
  size?: number;
  children?: ReactNode;
}

export function InfoTooltip({ term, title, body, size = 14 }: InfoTooltipProps) {
  const [open, setOpen] = useState(false);
  const content = term ? GLOSSARY[term] : { title: title ?? "", body: body ?? "" };

  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center", marginLeft: 4 }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label={`${content.title} 도움말`}
        tabIndex={0}
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          background: open ? "var(--primary-70)" : "var(--border-strong)",
          color: "#fff",
          border: "none",
          fontSize: Math.round(size * 0.7),
          fontWeight: 700,
          cursor: "help",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "inherit",
          padding: 0,
          lineHeight: 1,
          transition: "background 0.15s",
        }}
      >
        ?
      </button>
      {open && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            top: "100%",
            left: "50%",
            transform: "translateX(-50%)",
            marginTop: 6,
            zIndex: 100,
            width: 280,
            padding: "10px 14px",
            background: "var(--text)",
            color: "#fff",
            fontSize: 11.5,
            lineHeight: 1.5,
            fontWeight: 400,
            boxShadow: "0 6px 20px rgba(0,0,0,0.25)",
            pointerEvents: "none",
          }}
        >
          <span
            style={{
              position: "absolute",
              top: -5,
              left: "50%",
              transform: "translateX(-50%) rotate(45deg)",
              width: 10,
              height: 10,
              background: "var(--text)",
            }}
          />
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 4 }}>{content.title}</div>
          <div style={{ opacity: 0.9 }}>{content.body}</div>
        </span>
      )}
    </span>
  );
}
