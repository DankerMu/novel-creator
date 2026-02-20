"""Chapter summary endpoints: mark-done, extract, query."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ChapterSummaryOut
from app.core.database import get_db
from app.core.events import ChapterMarkDoneEvent, emit
from app.models import Book, Chapter, ChapterSummary
from app.services.summary import (
    EmptyChapterError,
    generate_chapter_summary,
)

router = APIRouter(prefix="/api", tags=["summary"])


@router.post(
    "/chapters/{chapter_id}/mark-done",
    response_model=ChapterSummaryOut,
)
async def mark_chapter_done(
    chapter_id: int, db: AsyncSession = Depends(get_db)
):
    """Mark chapter as done and auto-generate summary."""
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")

    # Idempotency: if already done, return existing summary
    if chapter.status == "done":
        result = await db.execute(
            select(ChapterSummary).where(
                ChapterSummary.chapter_id == chapter_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return _summary_to_out(existing)

    chapter.status = "done"
    await db.flush()

    # Resolve project_id for event
    book = await db.get(Book, chapter.book_id)
    if not book:
        raise HTTPException(404, "Book not found")

    # TODO: wire handlers for auto-bible-update etc.
    await emit(
        ChapterMarkDoneEvent(
            chapter_id=chapter_id,
            project_id=book.project_id,
        )
    )

    try:
        summary = await generate_chapter_summary(
            db, chapter_id
        )
    except EmptyChapterError:
        raise HTTPException(
            400, "Chapter has no text content"
        )

    return _summary_to_out(summary)


@router.post(
    "/chapters/{chapter_id}/extract-summary",
    response_model=ChapterSummaryOut,
)
async def extract_chapter_summary(
    chapter_id: int, db: AsyncSession = Depends(get_db)
):
    """Manually trigger summary extraction for a chapter."""
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")

    try:
        summary = await generate_chapter_summary(
            db, chapter_id
        )
    except EmptyChapterError:
        raise HTTPException(
            400, "Chapter has no text content"
        )

    return _summary_to_out(summary)


@router.get(
    "/chapters/{chapter_id}/summary",
    response_model=ChapterSummaryOut,
)
async def get_chapter_summary(
    chapter_id: int, db: AsyncSession = Depends(get_db)
):
    """Get existing chapter summary."""
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")

    result = await db.execute(
        select(ChapterSummary).where(
            ChapterSummary.chapter_id == chapter_id
        )
    )
    summary = result.scalar_one_or_none()
    if not summary:
        raise HTTPException(404, "Summary not found")

    return _summary_to_out(summary)


def _summary_to_out(summary: ChapterSummary) -> dict:
    """Convert ChapterSummary ORM to response dict."""
    return {
        "id": summary.id,
        "chapter_id": summary.chapter_id,
        "summary_md": summary.summary_md,
        "key_events": json.loads(
            summary.key_events_json
        ),
        "keywords": json.loads(summary.keywords_json),
        "entities": json.loads(summary.entities_json),
        "plot_threads": json.loads(
            summary.plot_threads_json
        ),
        "created_at": summary.created_at,
    }
