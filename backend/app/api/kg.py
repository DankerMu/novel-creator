"""Knowledge Graph API endpoints."""

import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import KGEdgeOut, KGNodeOut, KGProposalOut
from app.core.database import get_db
from app.models.tables import KGEdge, KGNode, KGProposal
from app.services.graph_service import SQLiteGraphAdapter, _safe_loads
from app.services.kg_extraction import extract_kg_from_chapter

router = APIRouter(prefix="/api", tags=["knowledge-graph"])


def _safe_loads_dict(raw: str) -> dict:
    return _safe_loads(raw, {})


def _proposal_to_out(p: KGProposal) -> dict:
    return {
        "id": p.id,
        "project_id": p.project_id,
        "chapter_id": p.chapter_id,
        "category": p.category,
        "data": _safe_loads_dict(p.data_json),
        "confidence": p.confidence,
        "status": p.status,
        "evidence_text": p.evidence_text,
        "evidence_location": p.evidence_location,
        "reviewed_at": p.reviewed_at,
        "created_at": p.created_at,
    }


def _node_to_out(n: KGNode) -> dict:
    return {
        "id": n.id,
        "project_id": n.project_id,
        "label": n.label,
        "name": n.name,
        "properties": _safe_loads_dict(n.properties_json),
        "created_at": n.created_at,
    }


def _edge_to_out(e: KGEdge) -> dict:
    return {
        "id": e.id,
        "project_id": e.project_id,
        "source_node_id": e.source_node_id,
        "target_node_id": e.target_node_id,
        "relation": e.relation,
        "properties": _safe_loads_dict(e.properties_json),
        "created_at": e.created_at,
    }


async def _approve_proposal(
    proposal: KGProposal, db: AsyncSession, new_status: str
) -> None:
    """Materialise an entity/relation proposal into the graph, then mark reviewed."""
    graph = SQLiteGraphAdapter(db)
    item = _safe_loads_dict(proposal.data_json)
    category = proposal.category

    if category == "entity":
        await graph.upsert_node(
            project_id=proposal.project_id,
            label=item.get("label", "Concept"),
            name=item.get("name", ""),
            properties=item.get("properties", {}),
        )
    elif category == "relation":
        source_id = await graph.upsert_node(
            project_id=proposal.project_id,
            label="Concept",
            name=item.get("source", ""),
            properties={},
        )
        target_id = await graph.upsert_node(
            project_id=proposal.project_id,
            label="Concept",
            name=item.get("target", ""),
            properties={},
        )
        await graph.add_edge(
            project_id=proposal.project_id,
            source_id=source_id,
            target_id=target_id,
            relation=item.get("relation", "related_to"),
            properties={},
        )

    proposal.status = new_status
    proposal.reviewed_at = datetime.datetime.utcnow()


# ---------- Extraction ----------

@router.post("/kg/extract", response_model=list[KGProposalOut])
async def trigger_extraction(
    body: dict, db: AsyncSession = Depends(get_db)
):
    """Trigger KG extraction for a chapter. Body: {chapter_id, project_id}"""
    chapter_id = body.get("chapter_id")
    project_id = body.get("project_id")
    if not chapter_id or not project_id:
        raise HTTPException(400, "chapter_id and project_id are required")
    proposals = await extract_kg_from_chapter(db, chapter_id, project_id)
    return [_proposal_to_out(p) for p in proposals]


# ---------- Proposals ----------

@router.get("/kg/proposals", response_model=list[KGProposalOut])
async def list_proposals(
    project_id: int,
    status: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List KG proposals with optional status / category filters."""
    stmt = select(KGProposal).where(KGProposal.project_id == project_id)
    if status:
        stmt = stmt.where(KGProposal.status == status)
    if category:
        stmt = stmt.where(KGProposal.category == category)
    stmt = stmt.order_by(KGProposal.confidence.desc(), KGProposal.id)
    result = await db.execute(stmt)
    proposals = result.scalars().all()
    return [_proposal_to_out(p) for p in proposals]


# Bulk endpoints MUST come before /{id} routes to avoid routing conflicts.

@router.post("/kg/proposals/bulk-approve", response_model=list[KGProposalOut])
async def bulk_approve_proposals(
    body: dict, db: AsyncSession = Depends(get_db)
):
    """Bulk approve proposals. Body: {ids: [...]}"""
    ids: list[int] = body.get("ids", [])
    if not ids:
        raise HTTPException(400, "ids list is required")
    result = await db.execute(
        select(KGProposal).where(KGProposal.id.in_(ids))
    )
    proposals = result.scalars().all()
    for p in proposals:
        if p.status == "pending":
            await _approve_proposal(p, db, "user_approved")
    await db.flush()
    for p in proposals:
        await db.refresh(p)
    return [_proposal_to_out(p) for p in proposals]


@router.post("/kg/proposals/bulk-reject", response_model=list[KGProposalOut])
async def bulk_reject_proposals(
    body: dict, db: AsyncSession = Depends(get_db)
):
    """Bulk reject proposals. Body: {ids: [...]}"""
    ids: list[int] = body.get("ids", [])
    if not ids:
        raise HTTPException(400, "ids list is required")
    result = await db.execute(
        select(KGProposal).where(KGProposal.id.in_(ids))
    )
    proposals = result.scalars().all()
    now = datetime.datetime.utcnow()
    for p in proposals:
        if p.status == "pending":
            p.status = "rejected"
            p.reviewed_at = now
    await db.flush()
    for p in proposals:
        await db.refresh(p)
    return [_proposal_to_out(p) for p in proposals]


@router.post("/kg/proposals/{proposal_id}/approve", response_model=KGProposalOut)
async def approve_proposal(
    proposal_id: int, db: AsyncSession = Depends(get_db)
):
    """Approve a single pending proposal."""
    p = await db.get(KGProposal, proposal_id)
    if not p:
        raise HTTPException(404, "Proposal not found")
    await _approve_proposal(p, db, "user_approved")
    await db.flush()
    await db.refresh(p)
    return _proposal_to_out(p)


@router.post("/kg/proposals/{proposal_id}/reject", response_model=KGProposalOut)
async def reject_proposal(
    proposal_id: int, db: AsyncSession = Depends(get_db)
):
    """Reject a single pending proposal."""
    p = await db.get(KGProposal, proposal_id)
    if not p:
        raise HTTPException(404, "Proposal not found")
    p.status = "rejected"
    p.reviewed_at = datetime.datetime.utcnow()
    await db.flush()
    await db.refresh(p)
    return _proposal_to_out(p)


# ---------- Graph query ----------

@router.get("/kg/nodes", response_model=list[KGNodeOut])
async def list_nodes(
    project_id: int,
    label: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List KG nodes for a project, optionally filtered by label."""
    graph = SQLiteGraphAdapter(db)
    nodes = await graph.get_nodes(project_id, label)
    return [_node_to_out(n) for n in nodes]


@router.get("/kg/edges", response_model=list[KGEdgeOut])
async def list_edges(
    project_id: int,
    node_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List KG edges for a project, optionally filtered by node involvement."""
    graph = SQLiteGraphAdapter(db)
    edges = await graph.get_edges(project_id, node_id)
    return [_edge_to_out(e) for e in edges]
