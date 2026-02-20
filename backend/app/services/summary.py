"""Chapter summary generation service."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai_schemas import ChapterSummaryModel
from app.core.config import settings
from app.core.llm import instructor_client
from app.models import (
    Chapter,
    ChapterSummary,
    Scene,
    SceneTextVersion,
)

# Rough char-to-token ratio for Chinese text
_MAX_PROMPT_CHARS = 20000


async def _collect_chapter_text(
    db: AsyncSession, chapter_id: int
) -> str:
    """Concatenate all scene texts in a chapter."""
    result = await db.execute(
        select(Scene)
        .where(Scene.chapter_id == chapter_id)
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
            parts.append(
                f"## {scene.title}\n\n{version.content_md}"
            )
    text = "\n\n".join(parts)
    # Truncate to stay within model context limits
    if len(text) > _MAX_PROMPT_CHARS:
        text = text[:_MAX_PROMPT_CHARS] + "\n\n[...截断...]"
    return text


class EmptyChapterError(Exception):
    """Raised when chapter has no text content."""


async def generate_chapter_summary(
    db: AsyncSession, chapter_id: int
) -> ChapterSummary:
    """Generate and save a structured chapter summary."""
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")

    full_text = await _collect_chapter_text(db, chapter_id)
    if not full_text.strip():
        raise EmptyChapterError(
            "Chapter has no text content"
        )

    prompt = f"""\
你是一位专业的小说编辑。请为以下章节内容生成结构化摘要。

# 章节：{chapter.title}

{full_text}

请提取：
1. 1-2 段叙事总结（narrative）
2. 关键事件列表（key_events）
3. 关键词（keywords）
4. 出场实体：人物、地点、物品（entities）
5. 情节线索（plot_threads）"""

    result = await instructor_client.chat.completions.create(
        model=settings.LLM_MODEL,
        response_model=ChapterSummaryModel,
        messages=[{"role": "user", "content": prompt}],
        max_retries=settings.LLM_MAX_RETRIES,
    )

    def _dumps(obj):
        return json.dumps(obj, ensure_ascii=False)

    # Upsert: replace existing summary if present
    existing = await db.execute(
        select(ChapterSummary).where(
            ChapterSummary.chapter_id == chapter_id
        )
    )
    summary = existing.scalar_one_or_none()

    if summary:
        summary.summary_md = result.narrative
        summary.key_events_json = _dumps(result.key_events)
        summary.keywords_json = _dumps(result.keywords)
        summary.entities_json = _dumps(result.entities)
        summary.plot_threads_json = _dumps(
            result.plot_threads
        )
    else:
        summary = ChapterSummary(
            chapter_id=chapter_id,
            summary_md=result.narrative,
            key_events_json=_dumps(result.key_events),
            keywords_json=_dumps(result.keywords),
            entities_json=_dumps(result.entities),
            plot_threads_json=_dumps(result.plot_threads),
        )
        db.add(summary)

    await db.flush()
    await db.refresh(summary)
    return summary
