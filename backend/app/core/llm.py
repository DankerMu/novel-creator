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
    return instructor.from_openai(client)


# Module-level alias for backward compatibility
class _InstructorProxy:
    """Proxy that lazily initializes the instructor client."""
    @property
    def chat(self):
        return get_instructor_client().chat


instructor_client = _InstructorProxy()


async def call_llm(
    messages: list[dict],
    model: str | None = None,
    stream: bool = False,
    **kwargs,
):
    """Unified LLM call via LiteLLM for non-structured outputs."""
    model = model or settings.LLM_MODEL
    response = await acompletion(
        model=model,
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
    model = model or settings.LLM_MODEL
    response = await acompletion(
        model=model,
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
