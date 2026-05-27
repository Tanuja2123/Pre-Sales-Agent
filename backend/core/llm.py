from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx

from core.config import Settings
from core.logging import get_logger

log = get_logger(__name__)

_JSON_ONLY_SUFFIX = (
    "\n\nRespond with a single valid JSON object only. "
    "No markdown, no code fences, no explanation before or after."
)


class LLMError(RuntimeError):
    """Raised when the LLM backend is unreachable, misconfigured, times out, or returns an error."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


def format_pipeline_error(exc: Exception) -> str:
    """Human-readable pipeline error (httpx timeouts often have empty str())."""
    if isinstance(exc, LLMError):
        return str(exc)
    msg = str(exc).strip()
    if msg:
        return msg
    name = type(exc).__name__
    if name in ("ReadTimeout", "WriteTimeout", "ConnectTimeout", "PoolTimeout"):
        return (
            "LLM request timed out. Check GROQ_API_KEY / network, or set LLM_BACKEND=mock for offline runs."
        )
    if name == "ConnectError":
        return "Cannot connect to the LLM service. Check .env LLM_BACKEND and API keys."
    return f"{name}: pipeline step failed (see server logs for details)"


def _backend_hint(settings: Settings) -> str:
    backend = settings.llm_backend
    if backend == "groq":
        return (
            f"Check Groq API key and model ({settings.groq_model}) at {settings.groq_base_url}, "
            "or set LLM_BACKEND=mock in .env."
        )
    if backend == "ollama":
        return (
            f"Check Ollama at {settings.ollama_base_url} (model: {settings.ollama_model}), "
            "or set LLM_BACKEND=mock in .env."
        )
    if backend == "azure_openai":
        return "Check AZURE_OPENAI_* settings in .env, or set LLM_BACKEND=mock."
    return "Set LLM_BACKEND=mock in .env for offline runs."


def _wrap_http_error(settings: Settings, exc: BaseException) -> LLMError:
    if isinstance(exc, httpx.TimeoutException):
        return LLMError(
            f"LLM request timed out ({settings.llm_backend}, "
            f"{settings.ollama_timeout_seconds:.0f}s). {_backend_hint(settings)}",
            cause=exc,
        )
    if isinstance(exc, httpx.HTTPStatusError):
        detail = ""
        try:
            detail = exc.response.text[:200]
        except Exception:  # noqa: BLE001
            pass
        if exc.response.status_code == 429 and settings.llm_backend == "groq":
            return LLMError(
                "Groq rate limit (429) after retries. Wait 1–2 minutes, use a smaller RFP, "
                f"or increase GROQ_INTER_REQUEST_DELAY_SECONDS (now "
                f"{settings.groq_inter_request_delay_seconds:.0f}s). {detail}".strip(),
                cause=exc,
            )
        if exc.response.status_code == 413 and settings.llm_backend == "groq":
            return LLMError(
                "Groq request too large (413). The pipeline auto-truncates prompts; try a smaller "
                f"RFP, lower GROQ_MAX_OUTPUT_TOKENS (now {settings.groq_max_output_tokens}), "
                f"or switch to a larger-context model. {detail}".strip(),
                cause=exc,
            )
        return LLMError(
            f"LLM HTTP {exc.response.status_code} from {settings.llm_backend}. {detail}".strip(),
            cause=exc,
        )
    if isinstance(exc, httpx.ConnectError):
        target = settings.groq_base_url if settings.llm_backend == "groq" else settings.ollama_base_url
        return LLMError(
            f"Cannot connect to LLM ({settings.llm_backend}) at {target}. {_backend_hint(settings)}",
            cause=exc,
        )
    msg = str(exc).strip() or type(exc).__name__
    return LLMError(f"LLM call failed: {msg}. {_backend_hint(settings)}", cause=exc)


def _normalize_root(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        if value and all(isinstance(x, dict) for x in value):
            if any("requirement_id" in x for x in value):
                return {"requirements": value}
            if any("question_id" in x for x in value):
                return {"questions": value}
            if any("section_id" in x for x in value):
                return {"sections": value}
        return {"items": value}
    return None


def _try_parse_object(candidate: str) -> dict[str, Any] | None:
    text = candidate.strip()
    if not text:
        return None

    for attempt in (text, _close_truncated_json(text)):
        if not attempt:
            continue
        try:
            parsed = json.loads(attempt)
            normalized = _normalize_root(parsed)
            if normalized is not None:
                return normalized
        except json.JSONDecodeError:
            continue

    try:
        obj, _end = json.JSONDecoder().raw_decode(text)
        return _normalize_root(obj)
    except json.JSONDecodeError:
        return None


def _close_truncated_json(text: str) -> str | None:
    """Close unbalanced { [ in nesting order so truncated model output can parse."""
    brace = text.find("{")
    bracket = text.find("[")
    if brace == -1 and bracket == -1:
        return None
    if bracket != -1 and (brace == -1 or bracket < brace):
        start = bracket
    else:
        start = brace
    fragment = text[start:]
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in fragment:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in "}]" and stack and stack[-1] == ch:
            stack.pop()
    if not stack:
        return None
    return fragment + "".join(reversed(stack))


def _extract_json(text: str) -> dict[str, Any]:
    """Parse JSON from model output (handles fences, prose, truncation, arrays)."""
    raw = (text or "").strip()
    if not raw:
        return {"_unparsed": ""}

    candidates: list[str] = []

    for block in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE):
        piece = block.group(1).strip()
        if piece:
            candidates.append(piece)

    bracket = raw.find("[")
    brace = raw.find("{")
    array_rooted = bracket != -1 and (brace == -1 or bracket < brace)

    if bracket != -1 and array_rooted:
        end_b = raw.rfind("]")
        if end_b > bracket:
            candidates.append(raw[bracket : end_b + 1])
        candidates.append(raw[bracket:])

    if brace != -1 and not array_rooted:
        end_brace = raw.rfind("}")
        if end_brace > brace:
            candidates.append(raw[brace : end_brace + 1])
        candidates.append(raw[brace:])

    candidates.append(raw)

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        parsed = _try_parse_object(candidate)
        if parsed is not None:
            return parsed

    return {"_unparsed": raw}


def _estimate_tokens(text: str) -> int:
    """Conservative token estimate for English-ish text (Groq has no local tokenizer)."""
    if not text:
        return 0
    return max(1, (len(text) + 2) // 3)


def _groq_request_token_budget(settings: Settings) -> int:
    if settings.groq_max_request_tokens > 0:
        return settings.groq_max_request_tokens
    model = settings.groq_model.lower()
    if "8b" in model or "instant" in model:
        return 5500
    if "70b" in model or "versatile" in model:
        return 12000
    return 8000


def _groq_output_token_cap(settings: Settings, requested: int) -> int:
    cap = min(requested, settings.groq_max_output_tokens)
    model = settings.groq_model.lower()
    if "8b" in model or "instant" in model:
        cap = min(cap, 1536)
    return max(256, cap)


def _fit_groq_payload(
    system: str,
    user: str,
    max_tokens: int,
    settings: Settings,
    *,
    shrink: float = 1.0,
) -> tuple[str, str, int]:
    """Trim Groq prompts so input + max_tokens stays under the model TPM/request budget."""
    budget = max(2048, int(_groq_request_token_budget(settings) * shrink))
    output_tokens = _groq_output_token_cap(settings, max_tokens)
    input_budget = max(512, budget - output_tokens)

    system_tokens = _estimate_tokens(system)
    user_tokens = _estimate_tokens(user)

    if system_tokens + user_tokens > input_budget:
        allowed_user_tokens = max(128, input_budget - system_tokens)
        if allowed_user_tokens < user_tokens:
            max_user_chars = max(256, allowed_user_tokens * 3)
            if len(user) > max_user_chars:
                user = (
                    user[:max_user_chars].rstrip()
                    + "\n\n[... truncated to fit Groq token limit ...]"
                )
            user_tokens = _estimate_tokens(user)

    if system_tokens + user_tokens > input_budget:
        allowed_system_tokens = max(128, input_budget - user_tokens)
        max_system_chars = max(256, allowed_system_tokens * 3)
        if len(system) > max_system_chars:
            system = (
                system[:max_system_chars].rstrip()
                + "\n\n[... system prompt truncated for Groq token limit ...]"
            )
        system_tokens = _estimate_tokens(system)

    total = system_tokens + user_tokens + output_tokens
    if total > budget:
        overflow = total - budget
        output_tokens = max(256, output_tokens - overflow)

    return system, user, output_tokens


def _strip_json_suffix(system: str) -> str:
    if system.endswith(_JSON_ONLY_SUFFIX):
        return system[: -len(_JSON_ONLY_SUFFIX)].rstrip()
    return system.rstrip()


def _finalize_groq_system(system: str) -> str:
    return _strip_json_suffix(system).rstrip() + _JSON_ONLY_SUFFIX


def _groq_payload_too_large(response: httpx.Response) -> bool:
    if response.status_code == 413:
        return True
    if response.status_code != 400:
        return False
    text = response.text.lower()
    if "rate limit" in text or "please try again" in text:
        return False
    return any(
        marker in text
        for marker in (
            "too large",
            "request too large",
            "context length",
            "maximum context",
            "reduce the length",
            "max_tokens",
            "invalid request",
        )
    )


def _parse_groq_retry_seconds(response: httpx.Response, attempt: int, base_seconds: float) -> float:
    retry_after = response.headers.get("retry-after") or response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 1.0)
        except ValueError:
            pass
    match = re.search(r"try again in\s+([0-9]+(?:\.[0-9]+)?)\s*s", response.text, re.IGNORECASE)
    if match:
        return max(float(match.group(1)) + 0.5, 1.0)
    return min(base_seconds * (attempt + 1), 65.0)


async def groq_cooldown(settings: Settings) -> None:
    """Pause between Groq calls to stay under free-tier TPM limits."""
    if settings.llm_backend != "groq":
        return
    delay = settings.groq_inter_request_delay_seconds
    model = settings.groq_model.lower()
    if "70b" in model or "versatile" in model:
        delay = max(delay, 55.0)
    elif "8b" in model or "instant" in model:
        delay = max(delay, 25.0)
    if delay > 0:
        log.info("groq.cooldown", seconds=delay, model=settings.groq_model)
        await asyncio.sleep(delay)


def _groq_messages_for_attempt(
    system: str,
    user: str,
    max_tokens: int,
    settings: Settings,
    *,
    shrink: float,
) -> tuple[str, str, int]:
    """Fit Groq messages and always preserve the JSON response suffix on the system prompt."""
    base_system = _strip_json_suffix(system)
    fitted_system, user_msg, output_tokens = _fit_groq_payload(
        base_system, user, max_tokens, settings, shrink=shrink
    )
    system_msg = _finalize_groq_system(fitted_system)

    budget = max(2048, int(_groq_request_token_budget(settings) * shrink))
    total = _estimate_tokens(system_msg) + _estimate_tokens(user_msg) + output_tokens
    if total <= budget:
        return system_msg, user_msg, output_tokens

    overflow = total - budget
    max_user_chars = max(256, len(user_msg) - overflow * 3)
    if len(user_msg) > max_user_chars:
        user_msg = (
            user_msg[:max_user_chars].rstrip()
            + "\n\n[... truncated to fit Groq token limit ...]"
        )

    total = _estimate_tokens(system_msg) + _estimate_tokens(user_msg) + output_tokens
    if total > budget:
        output_tokens = max(256, output_tokens - (total - budget))

    return system_msg, user_msg, output_tokens


def _ensure_dict(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = f"Internal error: expected dict from {context}, got {type(value).__name__}"
        raise TypeError(msg)
    return value


class OpenAICompatibleClient:
    """OpenAI-compatible chat for Groq, Ollama, and Azure OpenAI."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _ensure_groq_configured(self) -> None:
        if not self._settings.groq_api_key.strip():
            raise LLMError(
                "GROQ_API_KEY is not set. Create a key at https://console.groq.com and add it to .env."
            )

    async def chat_json(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 2048,
        repair_schema: str | None = None,
    ) -> dict[str, Any]:
        if self._settings.llm_backend == "mock":
            if getattr(self._settings, "llm_only_mode", False):
                raise LLMError(
                    "LLM-only mode is enabled. Set LLM_BACKEND to groq, ollama, or azure_openai."
                )
            return {"raw": user[:2000], "mock": True}

        if self._settings.llm_backend == "groq":
            self._ensure_groq_configured()

        timeout = httpx.Timeout(self._settings.ollama_timeout_seconds)
        system_msg = system.rstrip() + _JSON_ONLY_SUFFIX

        try:
            parsed = await self._dispatch_chat(system_msg, user, timeout, max_tokens)
        except LLMError:
            raise
        except httpx.HTTPError as exc:
            raise _wrap_http_error(self._settings, exc) from exc

        parsed = _ensure_dict(parsed, context="primary LLM call")

        if "_unparsed" not in parsed:
            return parsed

        repaired = await self._repair_with_llm(
            parsed["_unparsed"],
            timeout=timeout,
            max_tokens=max_tokens,
            repair_schema=repair_schema,
        )
        return _ensure_dict(repaired, context="LLM repair call")

    async def _repair_with_llm(
        self,
        unparsed: str,
        *,
        timeout: httpx.Timeout,
        max_tokens: int,
        repair_schema: str | None,
    ) -> dict[str, Any]:
        snippet = str(unparsed)[:4000]
        schema_hint = repair_schema or (
            "Return one valid JSON object with the keys requested in the system prompt."
        )
        repair_user = (
            f"{schema_hint}\n\n"
            "Convert the text below into one compact valid JSON object only. "
            "Do not echo input field names as the answer.\n\n"
            f"{snippet}"
        )
        repair_system = "You output only valid JSON objects. Never echo input payloads."

        try:
            result = await self._dispatch_chat(repair_system, repair_user, timeout, max_tokens)
        except httpx.HTTPError as exc:
            raise _wrap_http_error(self._settings, exc) from exc

        result = _ensure_dict(result, context="repair LLM call")

        if "_unparsed" in result:
            preview = str(result["_unparsed"])[:300].replace("\n", " ")
            raise LLMError(
                "Model did not return parseable JSON after retry. "
                f"Preview: {preview}… {_backend_hint(self._settings)}"
            )
        return result

    async def chat_text(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 2048,
    ) -> str:
        if self._settings.llm_backend == "mock":
            if getattr(self._settings, "llm_only_mode", False):
                raise LLMError(
                    "LLM-only mode is enabled. Set LLM_BACKEND to groq, ollama, or azure_openai."
                )
            return user[:2000]

        if self._settings.llm_backend == "groq":
            self._ensure_groq_configured()

        timeout = httpx.Timeout(self._settings.ollama_timeout_seconds)
        try:
            return await self._dispatch_chat_text(system, user, timeout, max_tokens)
        except LLMError:
            raise
        except httpx.HTTPError as exc:
            raise _wrap_http_error(self._settings, exc) from exc

    async def _dispatch_chat_text(
        self,
        system: str,
        user: str,
        timeout: httpx.Timeout,
        max_tokens: int,
    ) -> str:
        backend = self._settings.llm_backend
        if backend == "ollama":
            return await self._chat_ollama_text(system, user, timeout, max_tokens)
        if backend == "groq":
            return await self._chat_groq_text(system, user, timeout, max_tokens)
        if backend == "azure_openai":
            return await self._chat_azure_text(system, user, timeout, max_tokens)
        raise LLMError(f"Unsupported LLM_BACKEND={backend!r}. Use groq, ollama, azure_openai, or mock.")

    async def _dispatch_chat(
        self,
        system: str,
        user: str,
        timeout: httpx.Timeout,
        max_tokens: int,
    ) -> dict[str, Any]:
        backend = self._settings.llm_backend
        if backend == "ollama":
            return await self._chat_ollama(system, user, timeout, max_tokens)
        if backend == "groq":
            return await self._chat_groq(system, user, timeout, max_tokens)
        if backend == "azure_openai":
            return await self._chat_azure(system, user, timeout, max_tokens)
        raise LLMError(f"Unsupported LLM_BACKEND={backend!r}. Use groq, ollama, azure_openai, or mock.")

    async def _chat_groq(
        self, system: str, user: str, timeout: httpx.Timeout, max_tokens: int = 2048
    ) -> dict[str, Any]:
        url = f"{self._settings.groq_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        max_attempts = max(1, self._settings.groq_max_retries + 1)
        last_response: httpx.Response | None = None
        shrink = 1.0

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_attempts):
                system_msg, user_msg, output_tokens = _groq_messages_for_attempt(
                    system, user, max_tokens, self._settings, shrink=shrink
                )
                payload: dict[str, Any] = {
                    "model": self._settings.groq_model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.1,
                    "max_tokens": output_tokens,
                    "response_format": {"type": "json_object"},
                }
                r = await client.post(url, json=payload, headers=headers)
                last_response = r
                if _groq_payload_too_large(r) and attempt < max_attempts - 1:
                    shrink *= 0.7
                    log.warning(
                        "groq.payload_too_large",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        shrink=shrink,
                        model=self._settings.groq_model,
                        status_code=r.status_code,
                        detail=r.text[:240],
                        est_input_tokens=_estimate_tokens(system_msg) + _estimate_tokens(user_msg),
                        max_tokens=output_tokens,
                    )
                    await asyncio.sleep(1.0)
                    continue
                if r.status_code == 429 and attempt < max_attempts - 1:
                    wait = _parse_groq_retry_seconds(
                        r, attempt, self._settings.groq_retry_base_seconds
                    )
                    log.warning(
                        "groq.rate_limit",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        wait_seconds=wait,
                        model=self._settings.groq_model,
                    )
                    await asyncio.sleep(wait)
                    continue
                try:
                    r.raise_for_status()
                except httpx.HTTPStatusError:
                    raise
                data = r.json()
                content = data["choices"][0]["message"].get("content") or ""
                return _extract_json(content)

        detail = (last_response.text[:200] if last_response is not None else "") or "rate limit"
        raise LLMError(
            f"Groq rate limit (429) after {max_attempts} attempts. {detail}",
        )

    async def _chat_groq_text(
        self, system: str, user: str, timeout: httpx.Timeout, max_tokens: int = 2048
    ) -> str:
        url = f"{self._settings.groq_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        max_attempts = max(1, self._settings.groq_max_retries + 1)
        last_response: httpx.Response | None = None
        shrink = 1.0

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_attempts):
                system_msg, user_msg, output_tokens = _groq_messages_for_attempt(
                    system, user, max_tokens, self._settings, shrink=shrink
                )
                payload: dict[str, Any] = {
                    "model": self._settings.groq_model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.1,
                    "max_tokens": output_tokens,
                }
                r = await client.post(url, json=payload, headers=headers)
                last_response = r
                if _groq_payload_too_large(r) and attempt < max_attempts - 1:
                    shrink *= 0.7
                    await asyncio.sleep(1.0)
                    continue
                if r.status_code == 429 and attempt < max_attempts - 1:
                    wait = _parse_groq_retry_seconds(
                        r, attempt, self._settings.groq_retry_base_seconds
                    )
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                return str(data["choices"][0]["message"].get("content") or "").strip()

        detail = (last_response.text[:200] if last_response is not None else "") or "rate limit"
        raise LLMError(f"Groq rate limit (429) after {max_attempts} attempts. {detail}")

    async def _chat_ollama(
        self, system: str, user: str, timeout: httpx.Timeout, max_tokens: int = 2048
    ) -> dict[str, Any]:
        url = f"{self._settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": self._settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"].get("content") or ""
        return _extract_json(content)

    async def _chat_ollama_text(
        self, system: str, user: str, timeout: httpx.Timeout, max_tokens: int = 2048
    ) -> str:
        url = f"{self._settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": self._settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        return str(data["choices"][0]["message"].get("content") or "").strip()

    async def _chat_azure(
        self, system: str, user: str, timeout: httpx.Timeout, max_tokens: int = 2048
    ) -> dict[str, Any]:
        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        url = (
            f"{endpoint}/openai/deployments/{self._settings.azure_openai_deployment}"
            "/chat/completions?api-version=" + self._settings.azure_openai_api_version
        )
        headers = {
            "api-key": self._settings.azure_openai_api_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"].get("content") or ""
        return _extract_json(content)

    async def _chat_azure_text(
        self, system: str, user: str, timeout: httpx.Timeout, max_tokens: int = 2048
    ) -> str:
        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        url = (
            f"{endpoint}/openai/deployments/{self._settings.azure_openai_deployment}"
            "/chat/completions?api-version=" + self._settings.azure_openai_api_version
        )
        headers = {
            "api-key": self._settings.azure_openai_api_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        return str(data["choices"][0]["message"].get("content") or "").strip()
