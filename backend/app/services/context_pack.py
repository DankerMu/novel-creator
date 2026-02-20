"""Context Pack assembler: builds LLM prompt from Bible + summaries + recent text."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BibleField, ChapterSummary, Scene, SceneTextVersion


async def get_locked_bible_text(
    db: AsyncSession, project_id: int
) -> str:
    """Layer 1: System constraints from locked Bible fields."""
    result = await db.execute(
        select(BibleField)
        .where(
            BibleField.project_id == project_id,
            BibleField.locked.is_(True),
        )
        .order_by(BibleField.id)
    )
    fields = result.scalars().all()
    if not fields:
        return ""
    lines = ["# 故事设定约束（必须遵守）"]
    for f in fields:
        if f.value_md.strip():
            lines.append(f"## {f.key}\n{f.value_md}")
    return "\n\n".join(lines)


async def get_chapter_summaries_text(
    db: AsyncSession, chapter_id: int, limit: int = 3
) -> str:
    """Layer 2: Long-term memory from recent chapter summaries."""
    # Get the chapter's book_id to find sibling chapters
    from app.models import Chapter

    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        return ""

    result = await db.execute(
        select(ChapterSummary)
        .join(Chapter, Chapter.id == ChapterSummary.chapter_id)
        .where(
            Chapter.book_id == chapter.book_id,
            Chapter.sort_order < chapter.sort_order,
        )
        .order_by(Chapter.sort_order.desc())
        .limit(limit)
    )
    summaries = result.scalars().all()
    if not summaries:
        return ""
    lines = ["# 前文摘要"]
    for s in reversed(summaries):
        lines.append(s.summary_md)
    return "\n\n".join(lines)


async def get_recent_scene_text(
    db: AsyncSession, scene_id: int, paragraph_count: int = 3
) -> str:
    """Layer 3: Recent text from the current scene's latest version."""
    result = await db.execute(
        select(SceneTextVersion)
        .where(SceneTextVersion.scene_id == scene_id)
        .order_by(SceneTextVersion.version.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version or not version.content_md:
        return ""
    paragraphs = version.content_md.strip().split("\n\n")
    recent = paragraphs[-paragraph_count:]
    return "# 最近文本\n\n" + "\n\n".join(recent)


async def get_scene_project_id(
    db: AsyncSession, scene_id: int
) -> int | None:
    """Resolve scene_id → project_id."""
    from app.models import Book, Chapter

    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene_id)
    )
    scene = result.scalar_one_or_none()
    if not scene:
        return None
    chapter = await db.get(Chapter, scene.chapter_id)
    if not chapter:
        return None
    book = await db.get(Book, chapter.book_id)
    return book.project_id if book else None


async def assemble_context_pack(
    db: AsyncSession,
    scene_id: int,
    chapter_id: int,
    project_id: int,
) -> str:
    """Assemble full context pack from all layers."""
    bible = await get_locked_bible_text(db, project_id)
    summaries = await get_chapter_summaries_text(
        db, chapter_id
    )
    recent = await get_recent_scene_text(db, scene_id)

    parts = [p for p in [bible, summaries, recent] if p]
    return "\n\n---\n\n".join(parts)
