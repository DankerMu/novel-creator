"""Async event bus for single-process coordination."""

import asyncio
from collections import defaultdict
from typing import Callable

from pydantic import BaseModel

_handlers: dict[type, list[Callable]] = defaultdict(list)
_queue: asyncio.Queue | None = None


def on_event(event_type: type):
    """Decorator to register an event handler."""
    def decorator(func: Callable):
        _handlers[event_type].append(func)
        return func
    return decorator


async def emit(event: BaseModel):
    """Dispatch event to all registered handlers."""
    for handler in _handlers.get(type(event), []):
        await handler(event)


class ChapterMarkDoneEvent(BaseModel):
    chapter_id: int
    project_id: int
