"""파이프라인 안내 챗봇 — 시스템 동작 방식만 답변, 내부 코드/데이터 차단.

지식 베이스는 docs/CHATBOT_KNOWLEDGE.md (텍스트 설명) +
backend/app/config.py · pipeline/scorer.py · ml/checkpoints/autoencoder/meta.json
(동적 수치) 합성으로 구성된다. 가중치·임계값을 코드에서 바꾸면 챗봇 답변도 자동 갱신.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import anthropic
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from backend.app.config import settings

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger(__name__)

_MAX_MSG_LEN = 300

_KNOWLEDGE_PATH = Path(__file__).resolve().parents[3] / "docs" / "CHATBOT_KNOWLEDGE.md"
_AUTOENCODER_META = Path(__file__).resolve().parents[3] / "ml" / "checkpoints" / "autoencoder" / "meta.json"

_RESPONSE_RULES = """
## 답변 스타일
- 한국어, 친근한 존댓말("~해요", "~입니다"), 5문장 이내
- 비유 적극 활용 ("도시 면역 체계가 사람 면역과 비슷한 원리로…")
- 답변 끝에 후속 질문 1개 제안

## 절대 답변 금지
- 소스 코드, 함수명, 클래스명, 파일 경로, SQL 쿼리
- 환경변수 값, API 키, DB 비밀번호
- 실제 지역별 risk_score 수치·환자 수 등 라이브 데이터 조회 결과
- 팀원 개인정보, 내부 회의록, 이메일
- 의료적 진단·처방 — "AI 보조 자료, 의료 결정은 전문가 검토 필요" 명시

범위 밖 질문 시: "그 부분은 안내드릴 수 없어요. 대신 [관련 가능 주제]는 설명드릴 수 있습니다."
"""


def _live_spec() -> dict:
    """코드/설정/체크포인트에서 실시간 수치 추출."""
    from pipeline.scorer import (
        _CROSS_VALIDATION_LAYER_THRESHOLD,
        _CROSS_VALIDATION_MIN_LAYERS,
        _RED_THRESHOLD,
    )

    spec: dict = {
        "w1": settings.ensemble_weight_l1,
        "w2": settings.ensemble_weight_l2,
        "w3": settings.ensemble_weight_l3,
        # scorer.py 레벨 분기 임계값 — 매직넘버 변경 시 여기도 같이 바꿀 것
        "yellow_threshold": 30.0,
        "orange_threshold": 55.0,
        "red_threshold": _RED_THRESHOLD,
        "gate_layer_threshold": _CROSS_VALIDATION_LAYER_THRESHOLD,
        "gate_min_layers": _CROSS_VALIDATION_MIN_LAYERS,
        "autoencoder_threshold": 0.0,
        "autoencoder_percentile": 95.0,
    }
    if _AUTOENCODER_META.exists():
        try:
            meta = json.loads(_AUTOENCODER_META.read_text(encoding="utf-8"))
            spec["autoencoder_threshold"] = float(meta.get("threshold", 0.0))
            spec["autoencoder_percentile"] = float(meta.get("threshold_percentile", 95.0))
        except Exception:
            logger.warning("autoencoder meta.json 파싱 실패 — 기본값 사용")
    return spec


def _render_knowledge(template: str, spec: dict) -> str:
    """{key} 또는 {key:fmt} 자리표시자만 안전하게 치환 (str.format 대체).

    - {w1}, {autoencoder_threshold:.4f} 같은 알려진 key는 spec 값으로 치환
    - {...}, {{...}}, {7,14,21} 같은 사양 외 brace는 원문 그대로 유지
    """
    import re

    pattern = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([^}]+))?\}")

    def replace(match: re.Match) -> str:
        key, fmt = match.group(1), match.group(2)
        if key not in spec:
            return match.group(0)
        try:
            return format(spec[key], fmt) if fmt else str(spec[key])
        except (ValueError, TypeError):
            return str(spec[key])

    return pattern.sub(replace, template)


def _build_system_prompt() -> str:
    """CHATBOT_KNOWLEDGE.md + 동적 수치를 합성한 system prompt."""
    try:
        template = _KNOWLEDGE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("CHATBOT_KNOWLEDGE.md 미발견: %s — fallback 안내문 사용", _KNOWLEDGE_PATH)
        template = "UIS는 한국 감염병 조기경보 AI 시스템입니다."

    knowledge = _render_knowledge(template, _live_spec())
    return (
        "당신은 Urban Immune System(UIS) 안내 챗봇입니다. 아래 시스템 사양만 참조해 답변하세요. "
        "이 사양은 라이브 코드/설정에서 추출한 최신 값입니다.\n\n"
        f"{knowledge}\n\n{_RESPONSE_RULES}\n\n지금 사용자 질문에 답하세요."
    )


# 부팅 시 1회 합성 (수치 변경 시 백엔드 재기동 필요 — 의도적 단순화)
_SYSTEM_PROMPT = _build_system_prompt()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None  # [{"role": "user|assistant", "content": "..."}]

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """메시지 300자 제한 (과도한 프롬프트 인젝션 방어)."""
        return v[:_MAX_MSG_LEN]


@router.post("/ask")
async def chat_ask(req: ChatRequest) -> StreamingResponse:
    """SSE 스트리밍 응답 — 파이프라인 안내 챗봇."""
    return StreamingResponse(
        _stream_chat(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_chat(req: ChatRequest) -> AsyncIterator[str]:
    """Claude Haiku로 SSE 스트리밍 생성."""
    # history 검증: role은 user/assistant만 허용, content 300자 제한
    safe_history: list[dict] = []
    for item in (req.history or []):
        if not isinstance(item, dict):
            continue
        role = item.get("role", "")
        content = str(item.get("content", ""))
        if role not in ("user", "assistant"):
            continue
        safe_history.append({"role": role, "content": content[:_MAX_MSG_LEN]})

    messages = safe_history + [{"role": "user", "content": req.message}]

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        async with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=_SYSTEM_PROMPT,
            messages=messages,
        ) as stream_resp:
            async for text in stream_resp.text_stream:
                yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
    except Exception:
        logger.exception("챗봇 SSE 스트리밍 오류")
        yield f"data: {json.dumps({'error': '챗봇 일시 오류가 발생했어요. 잠시 후 다시 시도해주세요.'}, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"
