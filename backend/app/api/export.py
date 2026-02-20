"""Export endpoints: Markdown and TXT format."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Book, Chapter, Scene, SceneTextVersion

router = APIRouter(prefix="/api/export", tags=["export"])


async def _get_chapter_text(
    db: AsyncSession, chapter: Chapter
) -> str:
    """Collect all scene text for a chapter."""
    result = await db.execute(
        select(Scene)
        .where(Scene.chapter_id == chapter.id)
        .order_by(Scene.sort_order)
    )
    scenes = result.scalars().all()

    parts = []
    for scene in scenes:
        ver_result = await db.execute(
            select(SceneTextVersion)
            .where(SceneTextVersion.scene_id == scene.id)
            .order_by(SceneTextVersion.version.desc())
            .limit(1)
        )
        version = ver_result.scalar_one_or_none()
        if version and version.content_md.strip():
            parts.append(version.content_md)
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

    if chapter_id:
        chapter = await db.get(Chapter, chapter_id)
        if not chapter or chapter.book_id != book_id:
            raise HTTPException(404, "Chapter not found")
        text = await _get_chapter_text(db, chapter)
        md = f"# {chapter.title}\n\n{text}"
        return PlainTextResponse(
            md, media_type="text/markdown; charset=utf-8"
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

    if chapter_id:
        chapter = await db.get(Chapter, chapter_id)
        if not chapter or chapter.book_id != book_id:
            raise HTTPException(404, "Chapter not found")
        text = await _get_chapter_text(db, chapter)
        return PlainTextResponse(
            f"{chapter.title}\n\n{text}",
            media_type="text/plain; charset=utf-8",
        )

    # Full book export
    result = await db.execute(
        select(Chapter)
        .where(Chapter.book_id == book_id)
        .order_by(Chapter.sort_order)
    )
    chapters = result.scalars().all()

    parts = [book.title, "=" * len(book.title)]
    for ch in chapters:
        parts.append(f"\n{ch.title}")
        parts.append("-" * len(ch.title))
        text = await _get_chapter_text(db, ch)
        if text:
            parts.append(text)

    return PlainTextResponse(
        "\n".join(parts),
        media_type="text/plain; charset=utf-8",
    )
