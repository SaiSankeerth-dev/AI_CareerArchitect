import json
import re

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class LLMUnavailableError(Exception):
    """Raised when no LLM backend is reachable. Callers fall back to
    deterministic analysis so the product still works without any model."""


class _RetryableLLMError(Exception):
    pass


@retry(
    retry=retry_if_exception_type(_RetryableLLMError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True,
)
async def _call(messages: list[dict], json_mode: bool) -> str:
    import litellm

    kwargs: dict = {
        "model": settings.llm_model,
        "messages": messages,
        "timeout": settings.llm_timeout,
    }
    if settings.llm_model.startswith("ollama/"):
        kwargs["api_base"] = settings.llm_api_base
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        response = await litellm.acompletion(**kwargs)
    except Exception as exc:  # noqa: BLE001 - classify below
        text = str(exc).lower()
        if any(word in text for word in ("timeout", "rate", "overload", "connection reset")):
            raise _RetryableLLMError(str(exc)) from exc
        raise LLMUnavailableError(str(exc)) from exc
    return response.choices[0].message.content or ""


async def complete(prompt: str, system: str = "", json_mode: bool = False) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        return await _call(messages, json_mode)
    except LLMUnavailableError:
        raise
    except _RetryableLLMError as exc:
        raise LLMUnavailableError(str(exc)) from exc


def parse_json(text: str) -> dict | list:
    """Parse JSON from an LLM reply, salvaging fenced or embedded JSON."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No JSON found in LLM reply: {text[:200]}")
