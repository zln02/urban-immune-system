"""RAG-LLM 기반 감염병 경보 리포트 생성기.

1. 현재 리스크 점수와 신호 요약을 프롬프트로 구성
2. Qdrant에서 관련 역학 문서 검색 (RAG)
3. Claude로 리포트 생성 요청

출력 구조: 9개 섹션 강제 (KDCA 주간 감염병 보고서 표준 포맷 기반)
"""
from __future__ import annotations

import logging
import os

from ml.rag.vectordb import EpidemiologyVectorDB

logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MAX_RAG_DOC_CHARS = 300


SYSTEM_PROMPT = """당신은 공중보건 전문가입니다.
3-Layer 감염병 조기경보 시스템(약국 OTC + 하수 바이오마커 + 검색어 트렌드)의
분석 결과를 바탕으로 KDCA 주간 감염병 보고서 표준 포맷에 맞는 경보 리포트를 작성합니다.
리포트는 한국어로 작성하며, 일반 시민과 보건 당국 모두가 이해할 수 있어야 합니다.
반드시 아래 지시에서 요구하는 9개 섹션 구조(## 번호. 제목 형식)를 정확히 따라 markdown으로 출력하세요."""


def _build_prompt(signals: dict, rag_docs: list[dict], region: str) -> str:
    # RAG 인용 텍스트 구성 (author, year, page 메타 포함)
    ref_lines: list[str] = []
    for i, d in enumerate(rag_docs):
        meta = d.get("metadata") or {}
        topic = meta.get("topic", "guideline")
        author = meta.get("author", "")
        year = meta.get("year", "")
        page = meta.get("page", "")
        citation = f"[참고 {i + 1}]"
        if author and year:
            citation += f" {author}({year})"
        if page:
            citation += f" p.{page}"
        text_excerpt = _sanitize_doc_text(d.get("text", ""))
        ref_lines.append(f"{citation} [{topic}] {text_excerpt}")

    docs_text = "\n\n".join(ref_lines) if ref_lines else "(가이드라인 없음)"

    # composite 증감 계산 (previous_composite 있을 때)
    composite_val = signals.get("composite", "N/A")
    prev_composite = signals.get("previous_composite")
    if prev_composite is not None and isinstance(composite_val, (int, float)):
        delta = composite_val - prev_composite
        delta_str = f"+{delta:.1f}%" if delta >= 0 else f"{delta:.1f}%"
        composite_display = f"{composite_val} (전주 대비 {delta_str})"
    else:
        composite_display = str(composite_val)

    alert_level = signals.get("alert_level", "N/A")
    # alert_level → 위험등급 한국어 매핑
    level_ko_map = {
        "GREEN": "정상",
        "YELLOW": "주의",
        "ORANGE": "경계",
        "RED": "심각",
    }
    level_ko = level_ko_map.get(str(alert_level), str(alert_level))

    l1 = signals.get("l1", "N/A")
    l2 = signals.get("l2", "N/A")
    l3 = signals.get("l3", "N/A")

    return f"""지역: {region}
분석 시점: {signals.get("time", "N/A")}

## 현재 신호 데이터
- Layer 1 (OTC 구매 트렌드): {l1} / 100
- Layer 2 (하수 바이오마커): {l2} / 100
- Layer 3 (검색어 트렌드): {l3} / 100
- 종합 위험도(composite): {composite_display} / 100
- 경보 레벨: {alert_level} (위험등급: {level_ko})

## 관련 역학 근거 문서 (RAG 인용)
{docs_text}

---
위 데이터와 가이드라인을 바탕으로 아래 9개 섹션을 **정확히 이 순서와 형식**으로 markdown 출력하세요.
섹션 헤더는 반드시 `## 번호. 제목` 형식을 사용하세요.

## 1. 요약(Executive Summary)
1문단(3~4문장). 위험등급({level_ko}) 한 단어를 첫 문장에 명시하세요.

## 2. 핵심 지표
- composite={composite_val}, 전주 대비 변화(있으면), alert_level={alert_level}
표 또는 bullet 형식으로 간결하게.

## 3. 레이어별 분석
- **L1 OTC약국판매** ({l1}/100): 의미 + 추세 해석
- **L2 하수기반감시** ({l2}/100): 의미 + Granger 선행성 언급(가이드라인 있으면)
- **L3 검색트렌드** ({l3}/100): 의미 + L3 단독발령 금지 원칙 적용 여부 명시

## 4. 7/14/21일 전망
TFT 예측 결과 인용(가이드라인에 있으면) 또는 현재 추세 기반 정성 예측. 3항목 bullet.

## 5. 권고 조치
아래 권고 기준을 참고해 {region} 지역 상황에 맞게 구체화하세요:
- **보건당국**: ...
- **의료기관**: ...
- **시민**: ...

## 6. 참고 문헌
RAG 인용 문서를 아래 형식으로 나열 (1~5건):
[번호] 저자(연도). 제목. (출처).

## 7. 면책
이 리포트는 AI 보조 자료로, 인간 전문가(역학조사관) 검토가 필요합니다.
의료적 진단·처방을 대체하지 않습니다. (ISMS-P 2.9 / EU AI Act Art.13·14 준수)
"""


def _sanitize_doc_text(text: str) -> str:
    sanitized = " ".join(text.split())
    return sanitized[:MAX_RAG_DOC_CHARS]


async def generate_alert_report(signals: dict, region: str = "서울특별시") -> dict:
    """RAG + LLM으로 경보 리포트를 생성한다."""
    vdb = EpidemiologyVectorDB()
    query = f"인플루엔자 조기경보 {signals.get('alert_level', '')} {region}"
    rag_docs = vdb.search(query, top_k=5)

    prompt = _build_prompt(signals, rag_docs, region)

    report_text = await _call_claude(prompt)

    # RAG 인용 메타 구성 (author, year, page 포함)
    rag_sources_meta = [
        {
            "topic": (d.get("metadata") or {}).get("topic", ""),
            "source": (d.get("metadata") or {}).get("source", ""),
            "author": (d.get("metadata") or {}).get("author", ""),
            "year": (d.get("metadata") or {}).get("year", ""),
            "page": (d.get("metadata") or {}).get("page", ""),
            "score": round(float(d.get("score", 0.0)), 4),
        }
        for d in rag_docs
    ]

    return {
        "region": region,
        "alert_level": signals.get("alert_level"),
        "summary": report_text,
        "rag_sources": len(rag_docs),
        "rag_sources_meta": rag_sources_meta,
        "model_used": LLM_MODEL,
    }


async def _call_claude(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    resp = await client.messages.create(
        model=LLM_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text if resp.content else ""
