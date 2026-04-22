"""RAG-LLM 기반 감염병 경보 리포트 생성기.

1. 현재 리스크 점수와 신호 요약을 프롬프트로 구성
2. Qdrant에서 관련 역학 문서 검색 (RAG)
3. GPT-4o 또는 Claude에 리포트 생성 요청
"""
from __future__ import annotations

import logging
import os

from ml.rag.vectordb import EpidemiologyVectorDB

logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MAX_RAG_DOC_CHARS = 300


SYSTEM_PROMPT = """당신은 공중보건 전문가입니다.
3-Layer 감염병 조기경보 시스템(약국 OTC + 하수 바이오마커 + 검색어 트렌드)의
분석 결과를 바탕으로 간결하고 실용적인 경보 리포트를 작성합니다.
리포트는 한국어로 작성하며, 일반 시민과 보건 당국 모두가 이해할 수 있어야 합니다."""


def _build_prompt(signals: dict, rag_docs: list[dict], region: str) -> str:
    docs_text = "\n\n".join(
        [f"[참고 {i + 1}] {_sanitize_doc_text(d.get('text', ''))}" for i, d in enumerate(rag_docs)]
    )
    return f"""
지역: {region}
분석 시점: {signals.get('time', 'N/A')}

## 현재 신호 요약
- Layer 1 (OTC 구매 트렌드): {signals.get('l1', 'N/A')} / 100
- Layer 2 (하수 바이오마커): {signals.get('l2', 'N/A')} / 100
- Layer 3 (검색어 트렌드): {signals.get('l3', 'N/A')} / 100
- 종합 위험도 점수: {signals.get('composite', 'N/A')} / 100
- 경보 레벨: {signals.get('alert_level', 'N/A')}

## 관련 역학 근거 문서
{docs_text}

---
위 데이터를 바탕으로 다음 항목을 포함한 경보 리포트를 작성하세요:
1. 현황 요약 (2~3문장)
2. 각 Layer 신호 해석
3. 7/14/21일 전망
4. 권고 조치 (시민 대상 / 보건 당국 대상)
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

    if LLM_MODEL.startswith("claude"):
        report_text = await _call_claude(prompt)
    else:
        report_text = await _call_openai(prompt)

    return {
        "region": region,
        "alert_level": signals.get("alert_level"),
        "summary": report_text,
        "rag_sources": len(rag_docs),
        "model_used": LLM_MODEL,
    }


async def _call_openai(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    resp = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1500,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


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
