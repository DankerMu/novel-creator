"""Knowledge Graph API endpoints."""

import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import KGEdgeOut, KGNodeOut, KGProposalOut
from app.core.database import get_db
from app.models.tables import KGEdge, KGNode, KGProposal
from app.services.graph_service import SQLiteGraphAdapter, _safe_loads
from app.services.kg_extraction import extract_kg_from_chapter

router = APIRouter(prefix="/api", tags=["knowledge-graph"])


# --- Request models ---

class ExtractRequest(BaseModel):
    chapter_id: int
    project_id: int


class BulkIdsRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)


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
        source_id = await graph.ensure_node(
            project_id=proposal.project_id,
            name=item.get("source", ""),
            fallback_label="Concept",
        )
        target_id = await graph.ensure_node(
            project_id=proposal.project_id,
            name=item.get("target", ""),
            fallback_label="Concept",
        )
        await graph.upsert_edge(
            project_id=proposal.project_id,
            source_id=source_id,
            target_id=target_id,
            relation=item.get("relation", "related_to"),
            properties={},
        )

    proposal.status = new_status
    proposal.reviewed_at = datetime.datetime.now(datetime.UTC)


# ---------- Extraction ----------

@router.post("/kg/extract", response_model=list[KGProposalOut])
async def trigger_extraction(
    body: ExtractRequest, db: AsyncSession = Depends(get_db)
):
    """Trigger KG extraction for a chapter."""
    proposals = await extract_kg_from_chapter(
        db, body.chapter_id, body.project_id
    )
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
        if status == "approved":
            stmt = stmt.where(
                KGProposal.status.in_(["auto_approved", "user_approved"])
            )
        else:
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
    body: BulkIdsRequest,
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Bulk approve proposals scoped to project_id."""
    result = await db.execute(
        select(KGProposal).where(
            KGProposal.id.in_(body.ids),
            KGProposal.project_id == project_id,
        )
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
    body: BulkIdsRequest,
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Bulk reject proposals scoped to project_id."""
    result = await db.execute(
        select(KGProposal).where(
            KGProposal.id.in_(body.ids),
            KGProposal.project_id == project_id,
        )
    )
    proposals = result.scalars().all()
    now = datetime.datetime.now(datetime.UTC)
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
    proposal_id: int,
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Approve a single pending proposal (scoped to project)."""
    p = await db.get(KGProposal, proposal_id)
    if not p or p.project_id != project_id:
        raise HTTPException(404, "Proposal not found")
    await _approve_proposal(p, db, "user_approved")
    await db.flush()
    await db.refresh(p)
    return _proposal_to_out(p)


@router.post("/kg/proposals/{proposal_id}/reject", response_model=KGProposalOut)
async def reject_proposal(
    proposal_id: int,
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Reject a single pending proposal (scoped to project)."""
    p = await db.get(KGProposal, proposal_id)
    if not p or p.project_id != project_id:
        raise HTTPException(404, "Proposal not found")
    p.status = "rejected"
    p.reviewed_at = datetime.datetime.now(datetime.UTC)
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
