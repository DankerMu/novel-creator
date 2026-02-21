"""KG extraction service: parse chapter scenes and extract facts via LLM."""

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import call_llm
from app.models.tables import Chapter, KGProposal, Scene, SceneTextVersion
from app.services.graph_service import SQLiteGraphAdapter

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = """\
You are a knowledge graph extractor for a novel.
Given chapter text, extract entities and relations.
Return a JSON object with a single key "items" containing an array.
Each item must be one of:

  Entity:
  {"category": "entity", "label": "Character|Location|Item|Event|Concept|Organization",
   "name": "<name>", "properties": {<key>: <value>},
   "confidence": 0.0-1.0, "evidence": "<short snippet>"}

  Relation:
  {"category": "relation", "source": "<name>", "target": "<name>",
   "relation": "<verb_phrase>", "confidence": 0.0-1.0, "evidence": "<short snippet>"}

Rules:
- Output ONLY valid JSON: {"items": [...]}
- All strings must use proper JSON escaping (escape inner quotes with backslash).
- Use consistent names (same spelling for the same entity).
- confidence: 0.9+ only when the fact is stated explicitly.
- Keep evidence short (under 30 chars) to avoid quoting issues.
- Skip obvious/generic facts; focus on story-specific ones.
"""


def _safe_loads_list(raw: str) -> list:
    """Parse JSON array from LLM output, return [] on failure."""
    # Strip markdown fences and preamble text
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    else:
        # Find first JSON structure
        idx_arr = raw.find("[")
        idx_obj = raw.find("{")
        idx = -1
        if idx_arr >= 0 and idx_obj >= 0:
            idx = min(idx_arr, idx_obj)
        elif idx_arr >= 0:
            idx = idx_arr
        elif idx_obj >= 0:
            idx = idx_obj
        if idx > 0:
            raw = raw[idx:]

    # Fix unescaped ASCII double quotes used as Chinese quotation marks
    # Only match CJK unified ideographs, exclude fullwidth punctuation
    raw = re.sub(
        r'(?<=[\u4e00-\u9fff\u3400-\u4dbf])"(?=[\u4e00-\u9fff\u3400-\u4dbf])',
        r'\\"',
        raw,
    )

    try:
        data = json.loads(raw)
        # Support {"items": [...]} wrapper
        if isinstance(data, dict) and "items" in data:
            return data["items"] if isinstance(data["items"], list) else []
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse KG extraction JSON: %s", raw[:200])
        return []


async def _collect_chapter_text(db: AsyncSession, chapter_id: int) -> str:
    """Concatenate latest scene texts for a chapter."""
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
        if version and version.content_md:
            parts.append(version.content_md)

    return "\n\n".join(parts)


async def _approve_entity(graph: SQLiteGraphAdapter, project_id: int, item: dict) -> None:
    """Create or update a node from an auto-approved entity proposal."""
    await graph.upsert_node(
        project_id=project_id,
        label=item.get("label", "Concept"),
        name=item.get("name", ""),
        properties=item.get("properties", {}),
    )


async def _approve_relation(
    graph: SQLiteGraphAdapter, project_id: int, item: dict
) -> None:
    """Create nodes for source/target then add edge for an auto-approved relation."""
    source_id = await graph.ensure_node(
        project_id=project_id,
        name=item.get("source", ""),
        fallback_label="Concept",
    )
    target_id = await graph.ensure_node(
        project_id=project_id,
        name=item.get("target", ""),
        fallback_label="Concept",
    )
    await graph.upsert_edge(
        project_id=project_id,
        source_id=source_id,
        target_id=target_id,
        relation=item.get("relation", "related_to"),
        properties={},
    )


async def extract_kg_from_chapter(
    db: AsyncSession, chapter_id: int, project_id: int
) -> list[KGProposal]:
    """Extract KG facts from all scenes in a chapter.

    - Confidence >= 0.9 → auto_approved (node/edge created immediately)
    - Confidence 0.6-0.9 → pending (awaits user review)
    - Confidence < 0.6  → rejected (too uncertain)
    """
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        logger.warning("Chapter %d not found, skipping extraction.", chapter_id)
        return []

    text = await _collect_chapter_text(db, chapter_id)
    if not text.strip():
        return []

    messages = [
        {"role": "system", "content": _EXTRACTION_SYSTEM},
        {"role": "user", "content": text},
    ]

    try:
        response = await call_llm(
            messages, response_format={"type": "json_object"}
        )
        raw_content = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM call failed during KG extraction: %s", exc)
        return []

    items = _safe_loads_list(raw_content)
    graph = SQLiteGraphAdapter(db)
    proposals: list[KGProposal] = []

    for item in items:
        confidence = float(item.get("confidence", 0.0))
        category = item.get("category", "entity")
        evidence = item.get("evidence", "")

        if confidence < 0.6:
            status = "rejected"
        elif confidence >= 0.9:
            status = "auto_approved"
        else:
            status = "pending"

        # Materialise high-confidence facts immediately
        if status == "auto_approved":
            try:
                if category == "entity":
                    await _approve_entity(graph, project_id, item)
                elif category == "relation":
                    await _approve_relation(graph, project_id, item)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to materialise auto-approved fact: %s", exc)
                status = "pending"  # degrade gracefully

        proposal = KGProposal(
            project_id=project_id,
            chapter_id=chapter_id,
            category=category,
            data_json=json.dumps(item, ensure_ascii=False),
            confidence=confidence,
            status=status,
            evidence_text=evidence,
            evidence_location=f"chapter:{chapter_id}",
        )
        db.add(proposal)
        proposals.append(proposal)

    if proposals:
        await db.flush()
        for p in proposals:
            await db.refresh(p)

    return proposals
