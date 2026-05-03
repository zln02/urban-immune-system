"""E2E 통합 테스트 — /api/v1/chat/ask 챗봇 엔드포인트.

Anthropic API 호출은 unittest.mock.patch로 차단 — 실제 API 키 불필요.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.app.main import app

# ── fixture ──────────────────────────────────────────────────────────────────


def _make_stream_mock(chunks: list[str]):
    """AsyncAnthropic.messages.stream 컨텍스트 매니저 목."""

    async def _text_stream():
        for chunk in chunks:
            yield chunk

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=cm)
    cm.__aexit__ = AsyncMock(return_value=False)
    cm.text_stream = _text_stream()
    return cm


# ── 테스트 ─────────────────────────────────────────────────────────────────


class TestChatAsk:
    """정상 흐름: 파이프라인 질문 → 200 + SSE 스트림."""

    def test_normal_question_returns_200_sse(self):
        stream_mock = _make_stream_mock(["안녕하세요! ", "UIS는 ", "3계층 시스템이에요."])

        with patch("backend.app.api.chat.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.stream.return_value = stream_mock

            client = TestClient(app, raise_server_exceptions=False)
            with client.stream(
                "POST",
                "/api/v1/chat/ask",
                json={"message": "이 시스템은 어떻게 동작하나요?"},
            ) as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers.get("content-type", "")
                raw = resp.read().decode("utf-8")

            # SSE 첫 chunk 수신 확인
            lines = [line for line in raw.split("\n") if line.startswith("data: ")]
            assert len(lines) >= 1
            # 첫 data line이 유효한 JSON인지 확인 (DONE 제외)
            first_data = lines[0][len("data: "):]
            if first_data != "[DONE]":
                parsed = json.loads(first_data)
                assert "text" in parsed or "error" in parsed

    def test_done_sentinel_at_end(self):
        """스트림 마지막에 [DONE] sentinel 포함 확인."""
        stream_mock = _make_stream_mock(["완료"])

        with patch("backend.app.api.chat.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.stream.return_value = stream_mock

            client = TestClient(app, raise_server_exceptions=False)
            with client.stream("POST", "/api/v1/chat/ask", json={"message": "테스트"}) as resp:
                raw = resp.read().decode("utf-8")

            assert "data: [DONE]" in raw

    def test_empty_message_truncated_not_crash(self):
        """빈 메시지 → 422 (Pydantic min_length 없음) 또는 정상 처리.

        ChatRequest.message에 min_length 제약이 없으므로 빈 문자열도 통과.
        (LLM이 빈 메시지를 받아도 안전하게 응답해야 함)
        """
        stream_mock = _make_stream_mock([])

        with patch("backend.app.api.chat.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.stream.return_value = stream_mock

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v1/chat/ask", json={"message": ""})
            # 빈 메시지는 200 (LLM 처리) 또는 422 모두 허용
            assert resp.status_code in (200, 422)

    def test_message_sanitized_to_300_chars(self):
        """300자 초과 메시지는 내부에서 잘림 — 400 에러 없이 200 반환."""
        long_msg = "가" * 500
        stream_mock = _make_stream_mock(["짧게 답변드릴게요."])

        with patch("backend.app.api.chat.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.stream.return_value = stream_mock

            client = TestClient(app, raise_server_exceptions=False)
            with client.stream("POST", "/api/v1/chat/ask", json={"message": long_msg}) as resp:
                assert resp.status_code == 200

    def test_api_error_yields_error_event(self):
        """Anthropic API 예외 → error 이벤트 스트리밍 (500 아님)."""
        with patch("backend.app.api.chat.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            # stream 컨텍스트 매니저가 예외를 던지도록 설정
            cm = AsyncMock()
            cm.__aenter__ = AsyncMock(side_effect=RuntimeError("API 장애"))
            cm.__aexit__ = AsyncMock(return_value=False)
            mock_client.messages.stream.return_value = cm

            client = TestClient(app, raise_server_exceptions=False)
            with client.stream("POST", "/api/v1/chat/ask", json={"message": "오류 테스트"}) as resp:
                assert resp.status_code == 200
                raw = resp.read().decode("utf-8")

            error_lines = [line for line in raw.split("\n") if '"error"' in line]
            assert len(error_lines) >= 1
            parsed = json.loads(error_lines[0][len("data: "):])
            assert "error" in parsed

    def test_history_passed_to_llm(self):
        """history가 있을 때 LLM messages에 포함되는지 확인."""
        captured_messages: list = []

        async def _text_stream():
            return
            yield  # 빈 async generator

        # side_effect 대신 미리 만들어 둔 CM에 call-through 로직 삽입
        stream_mock = MagicMock()

        async def _stream_aenter(self_cm):
            # __aenter__ 호출 시점에 stream() 의 call_args를 통해 messages 캡처
            call_kwargs = mock_client.messages.stream.call_args
            if call_kwargs:
                captured_messages.extend(call_kwargs.kwargs.get("messages", []))
            stream_mock.text_stream = _text_stream()
            return stream_mock

        stream_mock.__aenter__ = _stream_aenter
        stream_mock.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.app.api.chat.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.stream.return_value = stream_mock

            history = [
                {"role": "user", "content": "안녕"},
                {"role": "assistant", "content": "안녕하세요!"},
            ]
            client = TestClient(app, raise_server_exceptions=False)
            with client.stream(
                "POST",
                "/api/v1/chat/ask",
                json={"message": "파이프라인 설명해줘", "history": history},
            ) as resp:
                resp.read()

        # LLM에 전달된 messages에 history + 새 메시지 포함 확인
        assert len(captured_messages) == 3  # history 2 + 새 메시지 1
        assert captured_messages[-1]["content"] == "파이프라인 설명해줘"
