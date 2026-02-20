"""LLM provider abstraction via LiteLLM + Instructor."""

from openai import AsyncOpenAI
import instructor
from litellm import acompletion

from app.core.config import settings

# Instructor client for structured outputs (SceneCard, ChapterSummary, etc.)
_openai_client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_API_BASE)
instructor_client = instructor.from_openai(_openai_client)


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


async def call_llm_stream(messages: list[dict], model: str | None = None, **kwargs):
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
