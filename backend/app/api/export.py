"""Export endpoints: Markdown and TXT format."""

import unicodedata
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Book, Chapter, Scene, SceneTextVersion

router = APIRouter(prefix="/api/export", tags=["export"])


def _cjk_width(text: str) -> int:
    """Compute display width accounting for CJK double-width chars."""
    w = 0
    for ch in text:
        eaw = unicodedata.east_asian_width(ch)
        w += 2 if eaw in ("W", "F") else 1
    return w


def _content_disposition(filename: str) -> str:
    """RFC 5987 Content-Disposition header value."""
    encoded = quote(filename)
    return f"attachment; filename*=UTF-8''{encoded}"


async def _get_chapter_text(
    db: AsyncSession, chapter: Chapter
) -> str:
    """Collect all scene text for a chapter (single query)."""
    latest_ver = (
        select(
            SceneTextVersion.scene_id,
            func.max(SceneTextVersion.version).label(
                "max_ver"
            ),
        )
        .group_by(SceneTextVersion.scene_id)
        .subquery()
    )

    result = await db.execute(
        select(SceneTextVersion.content_md)
        .join(Scene, Scene.id == SceneTextVersion.scene_id)
        .join(
            latest_ver,
            (latest_ver.c.scene_id == SceneTextVersion.scene_id)
            & (
                SceneTextVersion.version
                == latest_ver.c.max_ver
            ),
        )
        .where(Scene.chapter_id == chapter.id)
        .order_by(Scene.sort_order)
    )
    rows = result.scalars().all()

    parts = [r for r in rows if r and r.strip()]
    return "\n\n".join(parts)


@router.get("/markdown", response_class=PlainTextResponse)
async def export_markdown(
    book_id: int = Query(...),
    chapter_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export as Markdown with heading hierarchy."""
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")

    if chapter_id is not None:
        chapter = await db.get(Chapter, chapter_id)
        if not chapter or chapter.book_id != book_id:
            raise HTTPException(404, "Chapter not found")
        text = await _get_chapter_text(db, chapter)
        md = f"# {chapter.title}\n\n{text}"
        return PlainTextResponse(
            md,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": _content_disposition(
                    f"{chapter.title}.md"
                )
            },
        )

    # Full book export
    result = await db.execute(
        select(Chapter)
        .where(Chapter.book_id == book_id)
        .order_by(Chapter.sort_order)
    )
    chapters = result.scalars().all()

    parts = [f"# {book.title}"]
    for ch in chapters:
        text = await _get_chapter_text(db, ch)
        if text:
            parts.append(f"## {ch.title}\n\n{text}")
        else:
            parts.append(f"## {ch.title}")

    return PlainTextResponse(
        "\n\n".join(parts),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": _content_disposition(
                f"{book.title}.md"
            )
        },
    )


@router.get("/txt", response_class=PlainTextResponse)
async def export_txt(
    book_id: int = Query(...),
    chapter_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export as plain text with scene breaks."""
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")

    if chapter_id is not None:
        chapter = await db.get(Chapter, chapter_id)
        if not chapter or chapter.book_id != book_id:
            raise HTTPException(404, "Chapter not found")
        text = await _get_chapter_text(db, chapter)
        return PlainTextResponse(
            f"{chapter.title}\n\n{text}",
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": _content_disposition(
                    f"{chapter.title}.txt"
                )
            },
        )

    # Full book export
    result = await db.execute(
        select(Chapter)
        .where(Chapter.book_id == book_id)
        .order_by(Chapter.sort_order)
    )
    chapters = result.scalars().all()

    parts = [book.title, "=" * _cjk_width(book.title)]
    for ch in chapters:
        parts.append(f"\n{ch.title}")
        parts.append("-" * _cjk_width(ch.title))
        text = await _get_chapter_text(db, ch)
        if text:
            parts.append(text)

    return PlainTextResponse(
        "\n".join(parts),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": _content_disposition(
                f"{book.title}.txt"
            )
        },
    )
