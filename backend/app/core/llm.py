"""LLM provider abstraction via LiteLLM + Instructor."""

from functools import lru_cache

import instructor
from litellm import acompletion
from openai import AsyncOpenAI

from app.core.config import settings


@lru_cache(maxsize=1)
def get_instructor_client():
    """Lazy-init Instructor client (avoids import-time HTTP client creation)."""
    client = AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE,
    )
    return instructor.from_openai(client, mode=instructor.Mode.JSON)


# Module-level alias for backward compatibility
class _InstructorProxy:
    """Proxy that lazily initializes the instructor client."""
    @property
    def chat(self):
        return get_instructor_client().chat


instructor_client = _InstructorProxy()


def _litellm_model(model: str | None = None) -> str:
    """Add openai/ prefix for LiteLLM routing."""
    m = model or settings.LLM_MODEL
    if "/" not in m:
        return f"openai/{m}"
    return m


async def call_llm(
    messages: list[dict],
    model: str | None = None,
    stream: bool = False,
    **kwargs,
):
    """Unified LLM call via LiteLLM for non-structured outputs."""
    response = await acompletion(
        model=_litellm_model(model),
        messages=messages,
        api_base=settings.LLM_API_BASE,
        api_key=settings.LLM_API_KEY,
        stream=stream,
        **kwargs,
    )
    return response


async def call_llm_stream(
    messages: list[dict], model: str | None = None, **kwargs
):
    """Streaming LLM call, yields text chunks."""
    response = await acompletion(
        model=_litellm_model(model),
        messages=messages,
        api_base=settings.LLM_API_BASE,
        api_key=settings.LLM_API_KEY,
        stream=True,
        **kwargs,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
