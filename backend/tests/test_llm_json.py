from __future__ import annotations

import pytest

from core.llm import (
    _JSON_ONLY_SUFFIX,
    OpenAICompatibleClient,
    _estimate_tokens,
    _extract_json,
    _finalize_groq_system,
    _fit_groq_payload,
    _groq_messages_for_attempt,
    _groq_output_token_cap,
    _parse_groq_retry_seconds,
    _strip_json_suffix,
)


def test_extract_json_from_fence() -> None:
    text = 'Here is output:\n```json\n{"minimum_met": true, "overall_rating": "A"}\n```'
    data = _extract_json(text)
    assert data["minimum_met"] is True


def test_extract_json_truncated() -> None:
    text = '{"sections": [{"section_id": "S-1", "title": "A", "body": "hello"'
    data = _extract_json(text)
    assert "sections" in data


def test_extract_json_array_requirements() -> None:
    text = '[{"requirement_id": "REQ-001", "text": "must deliver"}]'
    data = _extract_json(text)
    assert isinstance(data.get("requirements"), list)


@pytest.mark.asyncio
async def test_chat_json_never_returns_coroutine(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSettings:
        llm_backend = "ollama"
        ollama_timeout_seconds = 30.0

    client = OpenAICompatibleClient(FakeSettings())  # type: ignore[arg-type]

    async def fake_ollama(system: str, user: str, timeout, max_tokens=2048):  # noqa: ANN001
        return {"questions": [{"question_id": "Q-001", "question_text": "What is the SLA?"}]}

    monkeypatch.setattr(client, "_chat_ollama", fake_ollama)
    result = await client.chat_json("sys", "user")
    assert isinstance(result, dict)
    assert "questions" in result


@pytest.mark.asyncio
async def test_chat_json_groq_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSettings:
        llm_backend = "groq"
        groq_api_key = "test-key"
        groq_base_url = "https://api.groq.com/openai/v1"
        groq_model = "llama-3.3-70b-versatile"
        ollama_timeout_seconds = 30.0

    client = OpenAICompatibleClient(FakeSettings())  # type: ignore[arg-type]

    async def fake_groq(system: str, user: str, timeout, max_tokens=2048):  # noqa: ANN001
        return {"minimum_met": True, "overall_rating": "A"}

    monkeypatch.setattr(client, "_chat_groq", fake_groq)
    result = await client.chat_json("sys", "user")
    assert result["minimum_met"] is True


def test_groq_8b_output_cap() -> None:
    class FakeSettings:
        groq_model = "llama-3.1-8b-instant"
        groq_max_output_tokens = 4096

    assert _groq_output_token_cap(FakeSettings(), 4096) == 1536  # type: ignore[arg-type]


def test_fit_groq_payload_truncates_large_user() -> None:
    class FakeSettings:
        groq_model = "llama-3.1-8b-instant"
        groq_max_output_tokens = 4096
        groq_max_request_tokens = 0

    system = "You are an agent. " * 200
    user = "RFP excerpt:\n" + ("Requirement line with details.\n" * 800)
    _, trimmed_user, out_tokens = _fit_groq_payload(
        system, user, 4096, FakeSettings()  # type: ignore[arg-type]
    )
    assert len(trimmed_user) < len(user)
    assert "truncated" in trimmed_user
    assert out_tokens <= 1536
    assert (
        _estimate_tokens(system) + _estimate_tokens(trimmed_user) + out_tokens
        <= 5500
    )


def test_groq_messages_preserve_json_suffix() -> None:
    class FakeSettings:
        groq_model = "llama-3.1-8b-instant"
        groq_max_output_tokens = 4096
        groq_max_request_tokens = 0

    system = ("You are an agent. " * 400) + _JSON_ONLY_SUFFIX
    user = "Payload:\n" + ("line\n" * 500)
    system_msg, _, _ = _groq_messages_for_attempt(
        system, user, 1200, FakeSettings(), shrink=1.0  # type: ignore[arg-type]
    )
    assert system_msg.endswith(_JSON_ONLY_SUFFIX.strip())
    assert _strip_json_suffix(system_msg) != system_msg


def test_finalize_groq_system_after_truncation() -> None:
    truncated = ("Instruction text. " * 50).rstrip() + "\n\n[... truncated ...]"
    final = _finalize_groq_system(truncated)
    assert _JSON_ONLY_SUFFIX.strip() in final


def test_parse_groq_retry_seconds_from_error_body() -> None:
    resp = type("Resp", (), {"headers": {}, "text": 'Please try again in 10.52s'})()
    assert _parse_groq_retry_seconds(resp, 0, 30.0) >= 11.0  # type: ignore[arg-type]
