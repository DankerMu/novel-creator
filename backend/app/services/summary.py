"""Chapter summary generation service."""

import json
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.llm import call_llm
from app.models import (
    Chapter,
    ChapterSummary,
    Scene,
    SceneTextVersion,
)

logger = logging.getLogger(__name__)

# Rough char-to-token ratio for Chinese text
_MAX_PROMPT_CHARS = 20000

_SUMMARY_SYSTEM = """\
你是一位专业的小说编辑。请为给定的章节内容生成结构化摘要。
返回一个 JSON 对象，包含以下字段：

{
  "narrative": "1-2 段叙事总结",
  "key_events": ["关键事件1", "关键事件2"],
  "keywords": ["关键词1", "关键词2"],
  "entities": ["人物/地点/物品1", "人物/地点/物品2"],
  "plot_threads": ["情节线索1", "情节线索2"]
}

规则：
- 只输出合法 JSON，不要 markdown 围栏
- 所有字符串必须正确 JSON 转义
- narrative 用中文书写
"""


async def _collect_chapter_text(
    db: AsyncSession, chapter_id: int
) -> str:
    """Concatenate all scene texts in a chapter (single query)."""
    # Subquery: latest version per scene
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
        select(Scene.title, SceneTextVersion.content_md)
        .join(latest_ver, latest_ver.c.scene_id == Scene.id)
        .join(
            SceneTextVersion,
            (SceneTextVersion.scene_id == Scene.id)
            & (
                SceneTextVersion.version
                == latest_ver.c.max_ver
            ),
        )
        .where(Scene.chapter_id == chapter_id)
        .order_by(Scene.sort_order)
    )
    rows = result.all()

    parts = []
    for title, content_md in rows:
        if content_md and content_md.strip():
            parts.append(f"## {title}\n\n{content_md}")

    text = "\n\n".join(parts)
    if len(text) > _MAX_PROMPT_CHARS:
        text = text[:_MAX_PROMPT_CHARS] + "\n\n[...截断...]"
    return text


def _parse_summary_json(raw: str) -> dict:
    """Parse summary JSON from LLM output with fence/quote repair."""
    # Strip markdown fences
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    else:
        idx = raw.find("{")
        if idx > 0:
            raw = raw[idx:]
    # Fix unescaped CJK quotes
    raw = re.sub(
        r'(?<=[\u4e00-\u9fff\u3400-\u4dbf])"(?=[\u4e00-\u9fff\u3400-\u4dbf])',
        r'\\"',
        raw,
    )
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse summary JSON: %s", raw[:200])
        return {}


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

    prompt = f"# 章节：{chapter.title}\n\n{full_text}"

    messages = [
        {"role": "system", "content": _SUMMARY_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    try:
        response = await call_llm(
            messages, response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        logger.error("LLM call failed during summary generation: %s", exc)
        raise

    result = _parse_summary_json(raw)
    if not result.get("narrative"):
        raise EmptyChapterError("LLM returned empty summary")

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
        summary.summary_md = result["narrative"]
        summary.key_events_json = _dumps(result.get("key_events", []))
        summary.keywords_json = _dumps(result.get("keywords", []))
        summary.entities_json = _dumps(result.get("entities", []))
        summary.plot_threads_json = _dumps(
            result.get("plot_threads", [])
        )
    else:
        summary = ChapterSummary(
            chapter_id=chapter_id,
            summary_md=result["narrative"],
            key_events_json=_dumps(result.get("key_events", [])),
            keywords_json=_dumps(result.get("keywords", [])),
            entities_json=_dumps(result.get("entities", [])),
            plot_threads_json=_dumps(result.get("plot_threads", [])),
        )
        db.add(summary)
        try:
            await db.flush()
        except IntegrityError:
            # Concurrent insert race: reload existing
            await db.rollback()
            existing = await db.execute(
                select(ChapterSummary).where(
                    ChapterSummary.chapter_id == chapter_id
                )
            )
            summary = existing.scalar_one()
            return summary

    await db.flush()
    await db.refresh(summary)
    return summary
