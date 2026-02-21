"""Rule-based consistency checker for novel projects."""

import json
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Book, Chapter, KGEdge, KGNode, KGProposal, Scene, SceneTextVersion


def _safe_loads(raw: str, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(raw) if raw else default
    except (json.JSONDecodeError, TypeError):
        return default


def _extract_ngrams(text: str, n: int) -> list[str]:
    """Extract character-level n-grams from text."""
    tokens = text.split()
    if len(tokens) < n:
        # fall back to character n-grams for dense Chinese text
        chars = [c for c in text if c.strip()]
        return ["".join(chars[i : i + n]) for i in range(len(chars) - n + 1)]
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


async def _build_scene_index(db: AsyncSession, project_id: int) -> list[dict]:
    """Return ordered list of {chapter_sort, chapter_id, scene_id, scene_sort, text, location}."""
    latest = (
        select(
            SceneTextVersion.scene_id,
            func.max(SceneTextVersion.version).label("max_ver"),
        )
        .group_by(SceneTextVersion.scene_id)
        .subquery()
    )

    result = await db.execute(
        select(
            Book.id.label("book_id"),
            Book.sort_order.label("book_sort"),
            Chapter.id.label("chapter_id"),
            Chapter.sort_order.label("chapter_sort"),
            Scene.id.label("scene_id"),
            Scene.sort_order.label("scene_sort"),
            SceneTextVersion.content_md,
        )
        .join(Chapter, Chapter.book_id == Book.id)
        .join(Scene, Scene.chapter_id == Chapter.id)
        .join(latest, latest.c.scene_id == Scene.id)
        .join(
            SceneTextVersion,
            (SceneTextVersion.scene_id == Scene.id)
            & (SceneTextVersion.version == latest.c.max_ver),
        )
        .where(Book.project_id == project_id)
        .order_by(Book.sort_order, Chapter.sort_order, Scene.sort_order)
    )
    rows = result.all()

    scenes = []
    for row in rows:
        scenes.append(
            {
                "book_id": row.book_id,
                "book_sort": row.book_sort,
                "chapter_id": row.chapter_id,
                "chapter_sort": row.chapter_sort,
                "scene_id": row.scene_id,
                "scene_sort": row.scene_sort,
                "text": row.content_md or "",
                "location": f"chapter:{row.chapter_id}:scene:{row.scene_id}",
            }
        )
    return scenes


# ---------- Check 1: character_status ----------

async def _check_character_status(
    db: AsyncSession, project_id: int, scenes: list[dict]
) -> list[dict]:
    """Detect dead characters appearing in later scene text."""
    result = await db.execute(
        select(KGNode).where(
            KGNode.project_id == project_id,
            KGNode.label == "Character",
        )
    )
    characters = result.scalars().all()

    dead_chars: list[tuple[str, str]] = []  # (name, death_location or "")
    for char in characters:
        props = _safe_loads(char.properties_json, {})
        status = props.get("status", "") or props.get("Status", "")
        if str(status).lower() == "dead":
            death_loc = props.get("death_location", "")
            dead_chars.append((char.name, death_loc))

    if not dead_chars:
        return []

    conflicts = []
    for name, death_loc in dead_chars:
        # Find the earliest scene index where the character "dies"
        death_idx: int | None = None
        if death_loc:
            for i, scene in enumerate(scenes):
                if death_loc in scene["location"]:
                    death_idx = i
                    break

        # Scan scenes after death for name occurrence
        check_from = (death_idx + 1) if death_idx is not None else 0
        reappearances = [
            scene["location"]
            for scene in scenes[check_from:]
            if name in scene["text"]
        ]

        if reappearances:
            has_loc = death_idx is not None
            conf = 1.0 if has_loc else 0.6
            evidence = []
            if death_loc:
                evidence.append(f"Character '{name}' marked dead at {death_loc}")
            else:
                evidence.append(f"Character '{name}' has status=dead in KG")
            evidence.append(f"Reappears in: {reappearances[0]}")

            conflicts.append(
                {
                    "type": "character_status",
                    "severity": "high",
                    "confidence": conf,
                    "source": "rule",
                    "message": f"Dead character '{name}' appears in later scene text.",
                    "evidence": evidence,
                    "evidence_locations": ([death_loc] if death_loc else []) + reappearances,
                    "suggest_fix": (
                        f"Remove or justify all references to '{name}'"
                        " after their death."
                    ),
                }
            )
    return conflicts


# ---------- Check 2: timeline ----------

async def _check_timeline(db: AsyncSession, project_id: int) -> list[dict]:
    """Detect events with narrative_day property ordered inconsistently with chapter sort."""
    # Gather events from KGProposals with narrative_day in data_json
    result = await db.execute(
        select(KGProposal).where(KGProposal.project_id == project_id)
    )
    proposals = result.scalars().all()

    # Also look at KGEdge properties for narrative_day
    edge_result = await db.execute(
        select(KGEdge).where(KGEdge.project_id == project_id)
    )
    edges = edge_result.scalars().all()

    # Map chapter_id -> sort_order
    ch_result = await db.execute(
        select(Chapter.id, Chapter.sort_order)
        .join(Book, Book.id == Chapter.book_id)
        .where(Book.project_id == project_id)
    )
    chapter_sort: dict[int, int] = {row[0]: row[1] for row in ch_result.all()}

    events: list[dict] = []  # {name, narrative_day, chapter_id, chapter_sort, location}

    for p in proposals:
        data = _safe_loads(p.data_json, {})
        day = data.get("narrative_day") or data.get("properties", {}).get("narrative_day")
        if day is not None:
            try:
                day = int(day)
            except (ValueError, TypeError):
                continue
            ch_sort = chapter_sort.get(p.chapter_id, 0)
            events.append(
                {
                    "name": data.get("name") or data.get("label") or f"proposal:{p.id}",
                    "narrative_day": day,
                    "chapter_id": p.chapter_id,
                    "chapter_sort": ch_sort,
                    "location": p.evidence_location or f"chapter:{p.chapter_id}",
                }
            )

    for e in edges:
        props = _safe_loads(e.properties_json, {})
        day = props.get("narrative_day")
        if day is not None:
            try:
                day = int(day)
            except (ValueError, TypeError):
                continue
            events.append(
                {
                    "name": f"edge:{e.id}",
                    "narrative_day": day,
                    "chapter_id": None,
                    "chapter_sort": 0,
                    "location": f"edge:{e.id}",
                }
            )

    conflicts = []
    # Compare every pair: if A has higher narrative_day but lower chapter_sort than B -> conflict
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            a, b = events[i], events[j]
            # a appears textually before b (lower chapter_sort) but has later narrative_day
            if a["chapter_sort"] < b["chapter_sort"] and a["narrative_day"] > b["narrative_day"]:
                conflicts.append(
                    {
                        "type": "timeline",
                        "severity": "medium",
                        "confidence": 1.0,
                        "source": "rule",
                        "message": (
                            f"Timeline conflict: '{a['name']}'"
                            f" (narrative_day={a['narrative_day']})"
                            f" appears before '{b['name']}'"
                            f" (narrative_day={b['narrative_day']})"
                            " in chapter order."
                        ),
                        "evidence": [
                            f"'{a['name']}' narrative_day={a['narrative_day']} at {a['location']}",
                            f"'{b['name']}' narrative_day={b['narrative_day']} at {b['location']}",
                        ],
                        "evidence_locations": [a["location"], b["location"]],
                        "suggest_fix": (
                            f"Reorder events so narrative_day={b['narrative_day']} "
                            f"comes before narrative_day={a['narrative_day']}."
                        ),
                    }
                )
    return conflicts


# ---------- Check 3: possession ----------

async def _check_possession(db: AsyncSession, project_id: int) -> list[dict]:
    """Detect items owned by multiple characters simultaneously."""
    result = await db.execute(
        select(KGEdge).where(
            KGEdge.project_id == project_id,
            KGEdge.relation.in_(["owns", "possesses"]),
        )
    )
    edges = result.scalars().all()

    # Group by target_node_id -> list of source_node_ids
    ownership: dict[int, list[int]] = defaultdict(list)
    for e in edges:
        ownership[e.target_node_id].append(e.source_node_id)

    # Batch-fetch all node names to avoid N+1 queries
    all_ids: set[int] = set()
    for target_id, owners in ownership.items():
        if len(owners) > 1:
            all_ids.add(target_id)
            all_ids.update(owners)

    if not all_ids:
        return []

    node_result = await db.execute(
        select(KGNode).where(KGNode.id.in_(all_ids))
    )
    node_map = {n.id: n.name for n in node_result.scalars().all()}

    conflicts = []
    for target_id, owners in ownership.items():
        if len(owners) <= 1:
            continue

        item_name = node_map.get(target_id, str(target_id))
        owner_names = [
            node_map.get(oid, str(oid)) for oid in owners
        ]

        conflicts.append(
            {
                "type": "possession",
                "severity": "medium",
                "confidence": 1.0,
                "source": "rule",
                "message": (
                    f"Item '{item_name}' is simultaneously owned by multiple characters: "
                    + ", ".join(f"'{n}'" for n in owner_names)
                    + "."
                ),
                "evidence": [
                    f"'{n}' owns '{item_name}'" for n in owner_names
                ],
                "evidence_locations": [f"kg_node:{target_id}"],
                "suggest_fix": (
                    f"Clarify which character currently owns '{item_name}', "
                    "or add a transfer-of-ownership event."
                ),
            }
        )
    return conflicts


# ---------- Check 4: plot_thread ----------

async def _check_plot_thread(db: AsyncSession, project_id: int, scenes: list[dict]) -> list[dict]:
    """Detect resolved plot threads referenced as active in later scenes."""
    result = await db.execute(
        select(KGNode).where(
            KGNode.project_id == project_id,
            KGNode.label.in_(["Event", "PlotThread", "Plot"]),
        )
    )
    nodes = result.scalars().all()

    conflicts = []
    for node in nodes:
        props = _safe_loads(node.properties_json, {})
        status = str(props.get("status", "") or props.get("Status", "")).lower()
        if status != "resolved":
            continue

        resolved_loc = props.get("resolved_location", "")
        resolved_idx: int | None = None
        if resolved_loc:
            for i, scene in enumerate(scenes):
                if resolved_loc in scene["location"]:
                    resolved_idx = i
                    break

        check_from = (resolved_idx + 1) if resolved_idx is not None else 0
        reappearances = [
            scene["location"]
            for scene in scenes[check_from:]
            if node.name in scene["text"]
        ]

        if reappearances:
            has_loc = resolved_idx is not None
            conf = 1.0 if has_loc else 0.6
            evidence = [f"Plot thread '{node.name}' marked resolved"]
            if resolved_loc:
                evidence.append(f"Resolved at {resolved_loc}")
            evidence.append(f"Referenced again at {reappearances[0]}")

            conflicts.append(
                {
                    "type": "plot_thread",
                    "severity": "medium",
                    "confidence": conf,
                    "source": "rule",
                    "message": (
                        f"Resolved plot thread '{node.name}' is referenced again in later scenes."
                    ),
                    "evidence": evidence,
                    "evidence_locations": ([resolved_loc] if resolved_loc else []) + reappearances,
                    "suggest_fix": (
                        f"Remove or update references to '{node.name}' after it was resolved."
                    ),
                }
            )
    return conflicts


# ---------- Check 5: repetition ----------

def _check_repetition_in_scene(
    scene: dict, ngram_n: int, ngram_threshold: int
) -> list[dict]:
    """Return conflicts for repeated n-grams within a single scene."""
    text = scene["text"]
    if not text.strip():
        return []

    ngrams = _extract_ngrams(text, ngram_n)
    counts: dict[str, int] = defaultdict(int)
    for ng in ngrams:
        counts[ng] += 1

    conflicts = []
    for ng, count in counts.items():
        if count >= ngram_threshold:
            conflicts.append(
                {
                    "type": "repetition",
                    "severity": "low",
                    "confidence": 1.0,
                    "source": "rule",
                    "message": (
                        f"{ngram_n}-gram '{ng}' appears {count} times "
                        f"(threshold={ngram_threshold}) in scene."
                    ),
                    "evidence": [
                        f"Repeated phrase: '{ng}' ({count}x)",
                    ],
                    "evidence_locations": [scene["location"]],
                    "suggest_fix": (
                        f"Rephrase repeated text to avoid repetitive use of '{ng}'."
                    ),
                }
            )
    return conflicts


# ---------- Main entry point ----------

async def run_consistency_check(
    db: AsyncSession,
    project_id: int,
    ngram_n: int = 4,
    ngram_threshold: int = 3,
) -> list[dict]:
    """Run all consistency checks and return a flat list of conflict dicts."""
    scenes = await _build_scene_index(db, project_id)

    results: list[dict] = []
    results.extend(await _check_character_status(db, project_id, scenes))
    results.extend(await _check_timeline(db, project_id))
    results.extend(await _check_possession(db, project_id))
    results.extend(await _check_plot_thread(db, project_id, scenes))

    for scene in scenes:
        results.extend(
            _check_repetition_in_scene(scene, ngram_n, ngram_threshold)
        )

    return results
