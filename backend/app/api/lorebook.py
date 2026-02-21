"""Lorebook CRUD + import/export endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LoreEntryCreate, LoreEntryOut, LoreEntryUpdate
from app.core.database import get_db
from app.models import LoreEntry, Project

router = APIRouter(prefix="/api", tags=["lorebook"])


def _safe_loads(raw: str, default=None):
    if default is None:
        default = []
    try:
        return json.loads(raw) if raw else default
    except (json.JSONDecodeError, TypeError):
        return default


def _entry_to_out(entry: LoreEntry) -> dict:
    """Convert LoreEntry ORM to response dict with parsed JSON fields."""
    return {
        "id": entry.id,
        "project_id": entry.project_id,
        "type": entry.type,
        "title": entry.title,
        "aliases": _safe_loads(entry.aliases_json, []),
        "content_md": entry.content_md,
        "secrets_md": entry.secrets_md,
        "triggers": _safe_loads(
            entry.triggers_json, {"keywords": [], "and_keywords": []}
        ),
        "priority": entry.priority,
        "locked": entry.locked,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


# ---------- Import / Export (must be before {entry_id} routes) ----------

@router.post("/lore/import", response_model=list[LoreEntryOut])
async def import_lore_entries(
    payload: dict, db: AsyncSession = Depends(get_db)
):
    """Import lorebook entries from SillyTavern JSON format.

    Expected format:
    {
        "project_id": 1,
        "entries": {
            "0": {"key": ["keyword1"], "keysecondary": ["kw2"],
                   "comment": "title", "content": "...", "order": 5,
                   "constant": false, ...},
            ...
        }
    }
    """
    project_id = payload.get("project_id")
    if not project_id:
        raise HTTPException(400, "project_id is required")
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    entries_data = payload.get("entries", {})
    created = []
    for _idx, item in entries_data.items():
        keywords = item.get("key", [])
        and_keywords = item.get("keysecondary", [])
        entry = LoreEntry(
            project_id=project_id,
            type="Concept",
            title=item.get("comment", "Untitled"),
            aliases_json=json.dumps([], ensure_ascii=False),
            content_md=item.get("content", ""),
            secrets_md="",
            triggers_json=json.dumps(
                {"keywords": keywords, "and_keywords": and_keywords},
                ensure_ascii=False,
            ),
            priority=item.get("order", 5),
            locked=item.get("constant", False),
        )
        db.add(entry)
        created.append(entry)

    await db.flush()
    for e in created:
        await db.refresh(e)
    return [_entry_to_out(e) for e in created]


@router.get("/lore/export")
async def export_lore_entries(
    project_id: int, db: AsyncSession = Depends(get_db)
):
    """Export all lorebook entries as SillyTavern-compatible JSON."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    result = await db.execute(
        select(LoreEntry)
        .where(LoreEntry.project_id == project_id)
        .order_by(LoreEntry.priority.desc(), LoreEntry.id)
    )
    entries = result.scalars().all()

    st_entries = {}
    for idx, entry in enumerate(entries):
        triggers = _safe_loads(
            entry.triggers_json, {"keywords": [], "and_keywords": []}
        )
        st_entries[str(idx)] = {
            "uid": entry.id,
            "key": triggers.get("keywords", []),
            "keysecondary": triggers.get("and_keywords", []),
            "comment": entry.title,
            "content": entry.content_md,
            "order": entry.priority,
            "constant": entry.locked,
            "enabled": True,
        }

    return {
        "entries": st_entries,
        "originalData": {
            "name": f"Lorebook - {project.title}",
            "description": "",
        },
    }


# ---------- CRUD ----------

@router.get("/lore", response_model=list[LoreEntryOut])
async def list_lore_entries(
    project_id: int, db: AsyncSession = Depends(get_db)
):
    """List all lorebook entries for a project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    result = await db.execute(
        select(LoreEntry)
        .where(LoreEntry.project_id == project_id)
        .order_by(LoreEntry.priority.desc(), LoreEntry.id)
    )
    entries = result.scalars().all()
    return [_entry_to_out(e) for e in entries]


@router.get("/lore/{entry_id}", response_model=LoreEntryOut)
async def get_lore_entry(
    entry_id: int, db: AsyncSession = Depends(get_db)
):
    entry = await db.get(LoreEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Lore entry not found")
    return _entry_to_out(entry)


@router.post("/lore", response_model=LoreEntryOut, status_code=201)
async def create_lore_entry(
    data: LoreEntryCreate, db: AsyncSession = Depends(get_db)
):
    project = await db.get(Project, data.project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    entry = LoreEntry(
        project_id=data.project_id,
        type=data.type,
        title=data.title,
        aliases_json=json.dumps(data.aliases, ensure_ascii=False),
        content_md=data.content_md,
        secrets_md=data.secrets_md,
        triggers_json=json.dumps(data.triggers, ensure_ascii=False),
        priority=data.priority,
        locked=data.locked,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return _entry_to_out(entry)


@router.put("/lore/{entry_id}", response_model=LoreEntryOut)
async def update_lore_entry(
    entry_id: int,
    data: LoreEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(LoreEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Lore entry not found")

    updates = data.model_dump(exclude_unset=True)
    # Handle JSON fields specially
    if "aliases" in updates:
        entry.aliases_json = json.dumps(updates.pop("aliases"), ensure_ascii=False)
    if "triggers" in updates:
        entry.triggers_json = json.dumps(updates.pop("triggers"), ensure_ascii=False)
    for k, v in updates.items():
        setattr(entry, k, v)

    await db.flush()
    await db.refresh(entry)
    return _entry_to_out(entry)


@router.delete("/lore/{entry_id}", status_code=204)
async def delete_lore_entry(
    entry_id: int, db: AsyncSession = Depends(get_db)
):
    entry = await db.get(LoreEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Lore entry not found")
    await db.delete(entry)
    await db.flush()
