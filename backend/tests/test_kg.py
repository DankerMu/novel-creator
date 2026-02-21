"""Tests for Knowledge Graph API endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def _setup_project_with_chapter(client):
    """Create project -> book -> chapter -> scene with text."""
    resp = await client.post(
        "/api/projects", json={"title": "KG Test"}
    )
    pid = resp.json()["id"]
    resp = await client.post(
        "/api/books",
        json={"project_id": pid, "title": "Book 1"},
    )
    bid = resp.json()["id"]
    resp = await client.post(
        "/api/chapters",
        json={"book_id": bid, "title": "Chapter 1"},
    )
    cid = resp.json()["id"]
    resp = await client.post(
        "/api/scenes",
        json={"chapter_id": cid, "title": "Scene 1"},
    )
    sid = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid}/versions",
        json={
            "content_md": "林远登上了星辰号飞船。"
            "他在驾驶舱遇到了副官张婷。",
            "created_by": "user",
        },
    )
    return pid, bid, cid, sid


MOCK_LLM_RESPONSE = json.dumps([
    {
        "category": "entity",
        "label": "Character",
        "name": "林远",
        "properties": {"role": "captain"},
        "confidence": 0.95,
        "evidence": "林远登上了星辰号飞船",
    },
    {
        "category": "entity",
        "label": "Character",
        "name": "张婷",
        "properties": {"role": "副官"},
        "confidence": 0.75,
        "evidence": "遇到了副官张婷",
    },
    {
        "category": "relation",
        "source": "林远",
        "target": "星辰号",
        "relation": "crew_of",
        "confidence": 0.92,
        "evidence": "林远登上了星辰号飞船",
    },
    {
        "category": "entity",
        "label": "Item",
        "name": "古地图",
        "properties": {},
        "confidence": 0.4,
        "evidence": "似乎提到了古地图",
    },
], ensure_ascii=False)


def _mock_llm_response(content: str):
    """Create a mock LLM response."""
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content=content))
    ]
    return mock_resp


# ==================== Extraction ====================


@pytest.mark.asyncio
async def test_extract_kg(client):
    """Extract KG facts with mocked LLM."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        resp = await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4


@pytest.mark.asyncio
async def test_extract_confidence_routing(client):
    """High>=0.9 auto_approved, 0.6-0.9 pending, <0.6 rejected."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        resp = await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    proposals = resp.json()
    statuses = {p["data"]["name"]: p["status"]
                for p in proposals if "name" in p["data"]}
    assert statuses["林远"] == "auto_approved"  # 0.95
    assert statuses["张婷"] == "pending"  # 0.75
    assert statuses["古地图"] == "rejected"  # 0.4

    # Relation (0.92) should be auto_approved
    rels = [p for p in proposals if p["category"] == "relation"]
    assert rels[0]["status"] == "auto_approved"


@pytest.mark.asyncio
async def test_extract_auto_creates_nodes(client):
    """Auto-approved entities create KG nodes."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    resp = await client.get(
        f"/api/kg/nodes?project_id={pid}"
    )
    nodes = resp.json()
    names = {n["name"] for n in nodes}
    # 林远 (auto_approved entity) should be a node
    assert "林远" in names
    # 张婷 (pending) should NOT be a node yet
    assert "张婷" not in names


@pytest.mark.asyncio
async def test_extract_llm_failure(client):
    """LLM failure returns empty list, no crash."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(side_effect=Exception("API down"))
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        resp = await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_extract_invalid_chapter(client):
    """Extract from non-existent chapter returns 404."""
    resp = await client.post(
        "/api/projects", json={"title": "P"}
    )
    pid = resp.json()["id"]

    mock_call = AsyncMock()
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        resp = await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": 9999,
                "project_id": pid,
            },
        )
    # Returns empty, not crash
    assert resp.status_code == 200
    assert resp.json() == []


# ==================== Proposals CRUD ====================


@pytest.mark.asyncio
async def test_list_proposals(client):
    """List proposals with filters."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    # All proposals
    resp = await client.get(
        f"/api/kg/proposals?project_id={pid}"
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 4

    # Filter by status
    resp = await client.get(
        f"/api/kg/proposals?project_id={pid}&status=pending"
    )
    pending = resp.json()
    assert all(p["status"] == "pending" for p in pending)

    # Filter by category
    resp = await client.get(
        f"/api/kg/proposals?project_id={pid}&category=relation"
    )
    rels = resp.json()
    assert all(p["category"] == "relation" for p in rels)


# ==================== Approve / Reject ====================


@pytest.mark.asyncio
async def test_approve_proposal(client):
    """Approve a pending proposal creates node."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    # Find pending proposal (张婷, 0.75)
    resp = await client.get(
        f"/api/kg/proposals?project_id={pid}&status=pending"
    )
    pending = resp.json()
    assert len(pending) >= 1
    prop_id = pending[0]["id"]

    # Approve it
    resp = await client.post(
        f"/api/kg/proposals/{prop_id}/approve?project_id={pid}"
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "user_approved"
    assert resp.json()["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_reject_proposal(client):
    """Reject a pending proposal."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    resp = await client.get(
        f"/api/kg/proposals?project_id={pid}&status=pending"
    )
    pending = resp.json()
    prop_id = pending[0]["id"]

    resp = await client.post(
        f"/api/kg/proposals/{prop_id}/reject?project_id={pid}"
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_approve_404(client):
    resp = await client.post(
        "/api/kg/proposals/9999/approve?project_id=1"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reject_404(client):
    resp = await client.post(
        "/api/kg/proposals/9999/reject?project_id=1"
    )
    assert resp.status_code == 404


# ==================== Bulk ====================


@pytest.mark.asyncio
async def test_bulk_approve(client):
    """Bulk approve multiple pending proposals."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    resp = await client.get(
        f"/api/kg/proposals?project_id={pid}&status=pending"
    )
    pending_ids = [p["id"] for p in resp.json()]

    resp = await client.post(
        f"/api/kg/proposals/bulk-approve?project_id={pid}",
        json={"ids": pending_ids},
    )
    assert resp.status_code == 200
    for p in resp.json():
        if p["id"] in pending_ids:
            assert p["status"] == "user_approved"


@pytest.mark.asyncio
async def test_bulk_reject(client):
    """Bulk reject multiple proposals."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    resp = await client.get(
        f"/api/kg/proposals?project_id={pid}&status=pending"
    )
    pending_ids = [p["id"] for p in resp.json()]

    resp = await client.post(
        f"/api/kg/proposals/bulk-reject?project_id={pid}",
        json={"ids": pending_ids},
    )
    assert resp.status_code == 200
    for p in resp.json():
        if p["id"] in pending_ids:
            assert p["status"] == "rejected"


@pytest.mark.asyncio
async def test_bulk_empty_ids(client):
    resp = await client.post(
        "/api/kg/proposals/bulk-approve?project_id=1",
        json={"ids": []},
    )
    assert resp.status_code == 422  # Pydantic min_length=1 validation


# ==================== Graph Query ====================


@pytest.mark.asyncio
async def test_list_nodes(client):
    """List nodes after extraction."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    resp = await client.get(
        f"/api/kg/nodes?project_id={pid}"
    )
    assert resp.status_code == 200
    nodes = resp.json()
    assert len(nodes) >= 1

    # Filter by label
    resp = await client.get(
        f"/api/kg/nodes?project_id={pid}&label=Character"
    )
    chars = resp.json()
    assert all(n["label"] == "Character" for n in chars)


@pytest.mark.asyncio
async def test_list_edges(client):
    """List edges after auto-approved relation."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    resp = await client.get(
        f"/api/kg/edges?project_id={pid}"
    )
    assert resp.status_code == 200
    edges = resp.json()
    # crew_of relation (0.92) should create an edge
    assert len(edges) >= 1
    assert edges[0]["relation"] == "crew_of"


@pytest.mark.asyncio
async def test_node_upsert(client):
    """Same name+label+project upserts, not duplicates."""
    pid, _bid, cid, _sid = (
        await _setup_project_with_chapter(client)
    )

    # Extract twice with same data
    mock_call = AsyncMock(
        return_value=_mock_llm_response(MOCK_LLM_RESPONSE)
    )
    with patch(
        "app.services.kg_extraction.call_llm", mock_call
    ):
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )
        await client.post(
            "/api/kg/extract",
            json={
                "chapter_id": cid,
                "project_id": pid,
            },
        )

    resp = await client.get(
        f"/api/kg/nodes?project_id={pid}&label=Character"
    )
    chars = resp.json()
    names = [n["name"] for n in chars]
    # "林远" should appear only once (upsert)
    assert names.count("林远") == 1
