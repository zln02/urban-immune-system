"""파이프라인 안내 챗봇 — 시스템 동작 방식만 답변, 내부 코드/데이터 차단."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import anthropic
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from backend.app.config import settings

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# 메시지 최대 길이 (sanitize)
_MAX_MSG_LEN = 300

_SYSTEM_PROMPT = """당신은 Urban Immune System(UIS) — 한국 감염병 조기경보 AI 시스템 — 의 안내 챗봇입니다.

## 답변 가능 범위 (이것만)
1. 시스템 전체 파이프라인 (수집 → 정규화 → 적재 → 앙상블 → ML → RAG → 대시보드)
2. 3계층 신호의 의미와 갱신 주기
   - L1 OTC 약국판매 (네이버 쇼핑인사이트, 매주 월 09:00)
   - L2 KOWAS 하수 바이오마커 (매주 화 10:00)
   - L3 검색 트렌드 (네이버 DataLab, 매주 월 09:05)
3. 앙상블 공식과 경보 레벨 임계값 (composite = 0.35·L1 + 0.40·L2 + 0.25·L3, GREEN/YELLOW/ORANGE/RED)
4. ML 모델 종류와 역할 (XGBoost·TFT·Autoencoder)
5. RAG 리포트 생성 방식과 트리거
6. 자동화 스케줄 (cron, 매일 12시 RAG 배치 등)
7. 시스템의 가치 제안 (왜 비의료 신호 교차검증이 필요한가, Google Flu Trends 교훈)

## 절대 답변 금지
- 소스 코드, 함수명, 클래스명, 파일 경로, SQL 쿼리
- 환경변수 값, API 키, DB 비밀번호
- 실제 지역별 risk_score 수치, 환자 수, 개별 데이터 조회 결과
- 팀원 개인정보, 내부 회의록, 이메일
- 다른 시스템·회사 비교 평가, 정치적 의견
- 의료적 진단·처방 — "AI 보조 자료, 의료 결정은 전문가 검토 필요" 명시

## 답변 스타일
- 한국어, 친근한 존댓말 ("~해요", "~입니다")
- 5문장 이내 간결 답변
- 비유 적극 활용 ("도시 면역 체계가 사람 면역과 비슷한 원리로 …")
- 답변 끝에 관련 후속 질문 1개 제안 ("혹시 ML 모델이 어떻게 학습되는지도 궁금하세요?")

## 거부 응답 형식
범위 밖 질문 시: "그 부분은 안내드릴 수 없어요. 대신 [관련 가능한 주제]는 설명드릴 수 있습니다."

지금 사용자 질문에 답하세요."""


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
