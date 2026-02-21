"""Lorebook service: trigger matching and context injection."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LoreEntry, Scene, SceneTextVersion


def _safe_loads(raw: str, default=None):
    """Safely parse JSON, return default on failure."""
    if default is None:
        default = []
    try:
        return json.loads(raw) if raw else default
    except (json.JSONDecodeError, TypeError):
        return default


def match_triggers(entry: LoreEntry, scan_text: str) -> bool:
    """Check if a lore entry's triggers match the scan text.

    - title and aliases are always checked (OR logic).
    - 'keywords': any keyword match triggers (OR logic).
    - 'and_keywords': ALL must match (AND logic).
    """
    if not scan_text:
        return False

    text_lower = scan_text.lower()
    triggers = _safe_loads(entry.triggers_json, {"keywords": [], "and_keywords": []})
    aliases = _safe_loads(entry.aliases_json, [])

    # Build candidate words: title + aliases + keywords (OR)
    or_words = [entry.title.lower()] + [a.lower() for a in aliases if a]
    keywords = triggers.get("keywords", []) or []
    or_words.extend(k.lower() for k in keywords if k)

    # OR match: any single word/phrase found
    or_matched = any(_word_in_text(w, text_lower) for w in or_words if w)

    # AND keywords: all must be present
    and_keywords = triggers.get("and_keywords", []) or []
    if and_keywords:
        and_matched = all(
            _word_in_text(k.lower(), text_lower) for k in and_keywords if k
        )
    else:
        and_matched = False

    return or_matched and (not and_keywords or and_matched)


def _word_in_text(word: str, text: str) -> bool:
    """Check if word/phrase exists in text (case-insensitive, already lowered)."""
    # Use simple substring match for CJK compatibility
    return word in text


async def get_scan_window(
    db: AsyncSession, scene_id: int, depth: int = 2
) -> str:
    """Get text from current scene + previous scenes for trigger scanning.

    Collects the latest version text from the current scene and
    up to (depth-1) preceding scenes in the same chapter.
    """
    scene = await db.get(Scene, scene_id)
    if not scene:
        return ""

    # Get scenes in the same chapter, ordered by sort_order
    result = await db.execute(
        select(Scene)
        .where(
            Scene.chapter_id == scene.chapter_id,
            Scene.sort_order <= scene.sort_order,
        )
        .order_by(Scene.sort_order.desc())
        .limit(depth)
    )
    scenes = result.scalars().all()

    texts = []
    for s in reversed(scenes):
        ver_result = await db.execute(
            select(SceneTextVersion)
            .where(SceneTextVersion.scene_id == s.id)
            .order_by(SceneTextVersion.version.desc())
            .limit(1)
        )
        version = ver_result.scalar_one_or_none()
        if version and version.content_md:
            texts.append(version.content_md)

    return "\n\n".join(texts)


def _truncate_to_sentence(text: str, budget: int) -> str:
    """Truncate text to budget chars, trimming at sentence boundary."""
    if len(text) <= budget:
        return text

    truncated = text[:budget]
    # Try to find last sentence-ending punctuation
    for sep in ["\n", "。", ".", "！", "!", "？", "?", "；", ";"]:
        idx = truncated.rfind(sep)
        if idx > budget // 2:  # Don't trim too aggressively
            return truncated[: idx + 1]
    return truncated


async def inject_lorebook(
    db: AsyncSession,
    project_id: int,
    scene_id: int,
    budget_chars: int = 4000,
) -> str:
    """Main injection function: assemble lorebook context for LLM prompt.

    1. Get scan window text
    2. Find all locked entries + triggered entries
    3. Sort by priority DESC
    4. Truncate to budget (trim to sentence boundary)
    5. Return assembled text
    """
    scan_text = await get_scan_window(db, scene_id)

    # Fetch all lore entries for this project
    result = await db.execute(
        select(LoreEntry)
        .where(LoreEntry.project_id == project_id)
        .order_by(LoreEntry.priority.desc(), LoreEntry.id)
    )
    all_entries = result.scalars().all()

    # Select: locked entries always included, others by trigger match
    selected = []
    for entry in all_entries:
        if entry.locked or match_triggers(entry, scan_text):
            selected.append(entry)

    if not selected:
        return ""

    # Already sorted by priority DESC from query
    # Assemble text blocks
    parts = []
    total_len = 0
    for entry in selected:
        block = f"## {entry.title} ({entry.type})\n{entry.content_md}"
        if total_len + len(block) > budget_chars:
            remaining = budget_chars - total_len
            if remaining > 50:  # Only add if meaningful space left
                block = _truncate_to_sentence(block, remaining)
                parts.append(block)
            break
        parts.append(block)
        total_len += len(block) + 2  # +2 for separator newlines

    if not parts:
        return ""

    return "# Lorebook\n\n" + "\n\n".join(parts)
