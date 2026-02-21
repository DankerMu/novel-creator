"""Context Pack assembler: 4-layer partition budget with overflow degradation.

Layers:
  1. System   (5~10%)  – locked Bible fields
  2. Long-term(10~15%) – chapter summaries
  3. KG+Lore  (15~25%) – KG approved facts + lorebook triggered entries
  4. Recent   (>=50%)  – current scene text (gets leftover budget)

Overflow degradation: each layer is hard-capped at its max ratio.
Leftover budget from earlier layers flows to Recent (layer 4).
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BibleField, Chapter, ChapterSummary, Scene, SceneTextVersion
from app.models.tables import KGProposal
from app.services.lorebook import inject_lorebook
from app.services.text_utils import truncate_to_sentence

# Budget ratios (fraction of total_budget_chars)
_SYSTEM_MAX = 0.10
_LONGTERM_MAX = 0.15
_KG_LORE_MAX = 0.25
_RECENT_MIN = 0.50

_SEPARATOR = "\n\n---\n\n"

# Default total budget in chars (~8K tokens for CJK)
DEFAULT_BUDGET_CHARS = 32_000


# ---------- Layer 1: System (Bible) ----------

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
    # M1 fix: return empty if no fields had content
    if len(lines) <= 1:
        return ""
    return "\n\n".join(lines)


# ---------- Layer 2: Long-term (Summaries) ----------

async def get_chapter_summaries_text(
    db: AsyncSession, chapter_id: int, limit: int = 3
) -> str:
    """Layer 2: Long-term memory from recent chapter summaries."""
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


# ---------- Layer 3: KG+Lore ----------

async def _get_kg_facts_text(
    db: AsyncSession, project_id: int, budget: int
) -> str:
    """Collect approved KG facts (entities + relations) as text."""
    result = await db.execute(
        select(KGProposal)
        .where(
            KGProposal.project_id == project_id,
            KGProposal.status.in_(["auto_approved", "user_approved"]),
        )
        .order_by(KGProposal.confidence.desc())
    )
    proposals = result.scalars().all()
    if not proposals:
        return ""

    header = "# 知识图谱事实"
    lines = [header]
    # H3 fix: count header + join newline
    total = len(header) + 1
    for p in proposals:
        data = json.loads(p.data_json) if p.data_json else {}
        if p.category == "entity":
            name = data.get("name", "")
            label = data.get("label", "")
            props = data.get("properties", {})
            prop_str = ", ".join(f"{k}={v}" for k, v in props.items())
            line = f"- [{label}] {name}"
            if prop_str:
                line += f" ({prop_str})"
        elif p.category == "relation":
            src = data.get("source", "?")
            tgt = data.get("target", "?")
            rel = data.get("relation", "?")
            line = f"- {src} --{rel}--> {tgt}"
        else:
            continue

        if total + len(line) + 1 > budget:
            break
        lines.append(line)
        total += len(line) + 1

    return "\n".join(lines) if len(lines) > 1 else ""


async def get_kg_lore_text(
    db: AsyncSession,
    project_id: int,
    scene_id: int,
    budget: int,
) -> str:
    """Layer 3: KG facts + lorebook triggered entries within budget.

    Split: KG gets up to 40% of layer budget, lorebook gets the rest.
    """
    kg_budget = int(budget * 0.4)
    kg_text = await _get_kg_facts_text(db, project_id, kg_budget)
    kg_used = len(kg_text)

    # M2 fix: reserve separator between KG and Lore
    sep_cost = 2 if kg_used > 0 else 0
    lore_budget = max(0, budget - kg_used - sep_cost)
    lore_text = await inject_lorebook(
        db, project_id, scene_id, budget_chars=lore_budget
    )

    parts = [p for p in [kg_text, lore_text] if p]
    return "\n\n".join(parts)


# ---------- Layer 4: Recent ----------

async def get_recent_scene_text(
    db: AsyncSession, scene_id: int, paragraph_count: int = 3
) -> str:
    """Layer 4: Recent text from the current scene's latest version."""
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


# ---------- Resolution helper ----------

async def get_scene_project_id(
    db: AsyncSession, scene_id: int
) -> int | None:
    """Resolve scene_id → project_id."""
    from app.models import Book

    scene = await db.get(Scene, scene_id)
    if not scene:
        return None
    chapter = await db.get(Chapter, scene.chapter_id)
    if not chapter:
        return None
    book = await db.get(Book, chapter.book_id)
    return book.project_id if book else None


# ---------- Main assembler ----------

async def assemble_context_pack(
    db: AsyncSession,
    scene_id: int,
    chapter_id: int,
    project_id: int,
    total_budget: int = DEFAULT_BUDGET_CHARS,
) -> str:
    """Assemble 4-layer context pack with partition budgets.

    Budget allocation:
      System:    up to 10% of total
      Long-term: up to 15% of total
      KG+Lore:   up to 25% of total
      Recent:    at least 50% of total (gets all leftover)

    Each layer is hard-capped. Leftover from earlier layers flows to Recent.
    """
    # H2 fix: reserve space for separators (up to 3 × len(_SEPARATOR))
    sep_overhead = len(_SEPARATOR) * 3
    usable = total_budget - sep_overhead

    sys_budget = int(usable * _SYSTEM_MAX)
    lt_budget = int(usable * _LONGTERM_MAX)
    kl_budget = int(usable * _KG_LORE_MAX)
    recent_min = int(usable * _RECENT_MIN)

    # --- Collect raw content ---
    system_raw = await get_locked_bible_text(db, project_id)
    longterm_raw = await get_chapter_summaries_text(db, chapter_id)
    kglore_raw = await get_kg_lore_text(
        db, project_id, scene_id, kl_budget
    )
    recent_raw = await get_recent_scene_text(db, scene_id)

    # --- Apply budgets ---
    system_text = truncate_to_sentence(system_raw, sys_budget)
    sys_used = len(system_text)

    longterm_text = truncate_to_sentence(longterm_raw, lt_budget)
    lt_used = len(longterm_text)

    kglore_text = truncate_to_sentence(kglore_raw, kl_budget)
    kl_used = len(kglore_text)

    # Layer 4: Recent — gets all leftover budget
    used_by_others = sys_used + lt_used + kl_used
    recent_budget = max(recent_min, usable - used_by_others)
    recent_text = truncate_to_sentence(recent_raw, recent_budget)

    # --- Assemble ---
    parts = [p for p in [system_text, longterm_text, kglore_text, recent_text] if p]
    return _SEPARATOR.join(parts)
