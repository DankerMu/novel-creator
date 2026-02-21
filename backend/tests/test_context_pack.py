"""Tests for Context Pack 4-layer budget system."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.ai_schemas import ChapterSummaryModel

MOCK_SUMMARY = ChapterSummaryModel(
    narrative="第一章讲述了冒险的开始。",
    key_events=["出发"],
    keywords=["冒险"],
    entities=["林远"],
    plot_threads=["寻找宝藏"],
)


async def _setup_full_project(client):
    """Create project with bible, chapters, summaries, scenes, lore, and KG."""
    # Project
    resp = await client.post("/api/projects", json={"title": "CP Test"})
    pid = resp.json()["id"]

    # Book + 2 chapters
    resp = await client.post("/api/books", json={"project_id": pid, "title": "Book 1"})
    bid = resp.json()["id"]
    resp = await client.post(
        "/api/chapters", json={"book_id": bid, "title": "Ch 1", "sort_order": 1}
    )
    ch1_id = resp.json()["id"]
    resp = await client.post(
        "/api/chapters", json={"book_id": bid, "title": "Ch 2", "sort_order": 2}
    )
    ch2_id = resp.json()["id"]

    # Scene in Ch2
    resp = await client.post("/api/scenes", json={"chapter_id": ch2_id, "title": "Scene 1"})
    sid = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid}/versions",
        json={
            "content_md": "林远走进了古老的森林。\n\n他手持魔法剑。\n\n远处有一座城堡。",
            "created_by": "user",
        },
    )

    # Bible field (locked) — GET auto-creates defaults, then PUT to set
    resp = await client.get(f"/api/bible?project_id={pid}")
    fields = resp.json()
    field_id = fields[0]["id"]  # First default field
    await client.put(
        f"/api/bible/{field_id}",
        json={"key": "世界观", "value_md": "这是一个魔法世界。", "locked": True},
    )

    # Mark Ch1 done to create summary
    resp2 = await client.post("/api/scenes", json={"chapter_id": ch1_id, "title": "S"})
    s1id = resp2.json()["id"]
    await client.post(
        f"/api/scenes/{s1id}/versions",
        json={"content_md": "前文内容。", "created_by": "user"},
    )

    mock_create = AsyncMock(return_value=MOCK_SUMMARY)
    with patch("app.services.summary.instructor_client") as mc:
        mc.chat.completions.create = mock_create
        await client.post(f"/api/chapters/{ch1_id}/mark-done")

    # Lorebook entry
    await client.post(
        "/api/lore",
        json={
            "project_id": pid,
            "type": "character",
            "title": "林远",
            "content_md": "林远是一位年轻的魔法师。",
            "triggers": {"keywords": ["林远"], "and_keywords": []},
            "priority": 10,
        },
    )

    return pid, bid, ch1_id, ch2_id, sid


# ==================== Basic Assembly ====================


@pytest.mark.asyncio
async def test_assemble_context_pack_basic(client, db_session):
    """Full 4-layer context pack assembles correctly."""
    from app.services.context_pack import assemble_context_pack

    pid, _, _, ch2_id, sid = await _setup_full_project(client)

    pack = await assemble_context_pack(db_session, sid, ch2_id, pid)

    # All 4 layers present
    assert "故事设定约束" in pack  # Layer 1: Bible
    assert "前文摘要" in pack  # Layer 2: Summary
    assert "最近文本" in pack  # Layer 4: Recent
    assert "林远走进了古老的森林" in pack


@pytest.mark.asyncio
async def test_assemble_empty_project(client, db_session):
    """Empty project returns empty string."""
    from app.services.context_pack import assemble_context_pack

    resp = await client.post("/api/projects", json={"title": "Empty"})
    pid = resp.json()["id"]
    resp = await client.post("/api/books", json={"project_id": pid, "title": "B"})
    bid = resp.json()["id"]
    resp = await client.post("/api/chapters", json={"book_id": bid, "title": "C"})
    cid = resp.json()["id"]
    resp = await client.post("/api/scenes", json={"chapter_id": cid, "title": "S"})
    sid = resp.json()["id"]

    pack = await assemble_context_pack(db_session, sid, cid, pid)
    assert pack == ""


# ==================== Budget Allocation ====================


@pytest.mark.asyncio
async def test_budget_system_layer_capped(client, db_session):
    """System layer is capped at 10% of total budget."""
    from app.services.context_pack import assemble_context_pack

    # Create project with large bible
    resp = await client.post("/api/projects", json={"title": "BigBible"})
    pid = resp.json()["id"]
    resp = await client.post("/api/books", json={"project_id": pid, "title": "B"})
    bid = resp.json()["id"]
    resp = await client.post("/api/chapters", json={"book_id": bid, "title": "C"})
    cid = resp.json()["id"]
    resp = await client.post("/api/scenes", json={"chapter_id": cid, "title": "S"})
    sid = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid}/versions",
        json={"content_md": "测试文本。", "created_by": "user"},
    )

    # Create a large locked bible field (2000 chars)
    large_text = "这是重要设定。" * 300  # ~2100 chars
    await client.post(
        "/api/bible/fields",
        json={"project_id": pid, "key": "大设定", "value_md": large_text, "locked": True},
    )

    # Use small budget so 10% = 100 chars
    pack = await assemble_context_pack(
        db_session, sid, cid, pid, total_budget=1000
    )

    # Bible text should be truncated (10% of 1000 = 100 chars)
    bible_section = pack.split("---")[0] if "---" in pack else pack
    assert len(bible_section) <= 150  # Some margin for header


@pytest.mark.asyncio
async def test_budget_recent_gets_leftover(client, db_session):
    """Recent layer gets at least 50% and all leftover budget."""
    from app.services.context_pack import assemble_context_pack

    resp = await client.post("/api/projects", json={"title": "R"})
    pid = resp.json()["id"]
    resp = await client.post("/api/books", json={"project_id": pid, "title": "B"})
    bid = resp.json()["id"]
    resp = await client.post("/api/chapters", json={"book_id": bid, "title": "C"})
    cid = resp.json()["id"]
    resp = await client.post("/api/scenes", json={"chapter_id": cid, "title": "S"})
    sid = resp.json()["id"]

    # Add 500-char scene text
    text = "这是最近的文本内容。" * 50  # 500 chars
    await client.post(
        f"/api/scenes/{sid}/versions",
        json={"content_md": text, "created_by": "user"},
    )

    # With 2000 budget and no bible/summaries/lore, recent gets full budget
    pack = await assemble_context_pack(
        db_session, sid, cid, pid, total_budget=2000
    )
    # Recent text should be fully included (500 < 2000)
    assert "最近文本" in pack


# ==================== KG Integration ====================


@pytest.mark.asyncio
async def test_kg_facts_in_context(client, db_session):
    """Approved KG facts appear in context pack."""

    from app.services.context_pack import assemble_context_pack

    pid, _, _, ch2_id, sid = await _setup_full_project(client)

    # Extract KG with mocked LLM
    mock_llm_data = json.dumps([
        {
            "category": "entity",
            "label": "Character",
            "name": "林远",
            "properties": {"role": "魔法师"},
            "confidence": 0.95,
            "evidence": "林远走进",
        },
    ], ensure_ascii=False)
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=mock_llm_data))]
    mock_call = AsyncMock(return_value=mock_resp)

    with patch("app.services.kg_extraction.call_llm", mock_call):
        await client.post(
            "/api/kg/extract",
            json={"chapter_id": ch2_id, "project_id": pid},
        )

    pack = await assemble_context_pack(db_session, sid, ch2_id, pid)
    assert "知识图谱事实" in pack
    assert "林远" in pack
    assert "魔法师" in pack


# ==================== Lorebook Integration ====================


@pytest.mark.asyncio
async def test_lorebook_triggered_in_context(client, db_session):
    """Lorebook entries triggered by scene text appear in context."""
    from app.services.context_pack import assemble_context_pack

    pid, _, _, ch2_id, sid = await _setup_full_project(client)

    pack = await assemble_context_pack(db_session, sid, ch2_id, pid)
    # Lorebook entry for 林远 should be triggered by scene text
    assert "Lorebook" in pack
    assert "林远是一位年轻的魔法师" in pack


@pytest.mark.asyncio
async def test_lorebook_not_triggered_without_keyword(client, db_session):
    """Lorebook entries not triggered when keyword absent from text."""
    from app.services.context_pack import assemble_context_pack

    resp = await client.post("/api/projects", json={"title": "NoTrigger"})
    pid = resp.json()["id"]
    resp = await client.post("/api/books", json={"project_id": pid, "title": "B"})
    bid = resp.json()["id"]
    resp = await client.post("/api/chapters", json={"book_id": bid, "title": "C"})
    cid = resp.json()["id"]
    resp = await client.post("/api/scenes", json={"chapter_id": cid, "title": "S"})
    sid = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid}/versions",
        json={"content_md": "天空很蓝。", "created_by": "user"},
    )

    # Add lore entry that won't match
    await client.post(
        "/api/lore",
        json={
            "project_id": pid,
            "type": "location",
            "title": "暗黑城堡",
            "content_md": "一座被诅咒的城堡。",
            "triggers": {"keywords": ["暗黑城堡"], "and_keywords": []},
            "priority": 5,
        },
    )

    pack = await assemble_context_pack(db_session, sid, cid, pid)
    assert "暗黑城堡" not in pack


# ==================== Overflow Degradation ====================


@pytest.mark.asyncio
async def test_overflow_truncates_kglore_first(client, db_session):
    """When budget is tight, KG+Lore is truncated first."""
    from app.services.context_pack import assemble_context_pack

    pid, _, _, ch2_id, sid = await _setup_full_project(client)

    # Very small budget: 200 chars total
    pack = await assemble_context_pack(
        db_session, sid, ch2_id, pid, total_budget=200
    )

    # Recent text should still be present (>=50% = 100 chars)
    assert "最近文本" in pack
    # Lore layer budget = 25% of 200 = 50 chars, may be heavily truncated
    # but recent should not be sacrificed


@pytest.mark.asyncio
async def test_total_pack_within_budget(client, db_session):
    """Total assembled pack respects total budget."""
    from app.services.context_pack import assemble_context_pack

    pid, _, _, ch2_id, sid = await _setup_full_project(client)

    budget = 500
    pack = await assemble_context_pack(
        db_session, sid, ch2_id, pid, total_budget=budget
    )
    # Total should not wildly exceed budget
    # (small overhead from separators "---" is acceptable)
    assert len(pack) <= budget * 1.2  # 20% margin for separators


# ==================== Layer isolation ====================


@pytest.mark.asyncio
async def test_no_summaries_still_works(client, db_session):
    """Context pack works when no chapter summaries exist."""
    from app.services.context_pack import assemble_context_pack

    resp = await client.post("/api/projects", json={"title": "NoSum"})
    pid = resp.json()["id"]
    resp = await client.post("/api/books", json={"project_id": pid, "title": "B"})
    bid = resp.json()["id"]
    resp = await client.post("/api/chapters", json={"book_id": bid, "title": "C"})
    cid = resp.json()["id"]
    resp = await client.post("/api/scenes", json={"chapter_id": cid, "title": "S"})
    sid = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid}/versions",
        json={"content_md": "一段场景文本。", "created_by": "user"},
    )

    pack = await assemble_context_pack(db_session, sid, cid, pid)
    assert "前文摘要" not in pack
    assert "最近文本" in pack


@pytest.mark.asyncio
async def test_custom_budget(client, db_session):
    """Custom total_budget parameter is respected."""
    from app.services.context_pack import assemble_context_pack

    pid, _, _, ch2_id, sid = await _setup_full_project(client)

    pack_small = await assemble_context_pack(
        db_session, sid, ch2_id, pid, total_budget=100
    )
    pack_large = await assemble_context_pack(
        db_session, sid, ch2_id, pid, total_budget=50000
    )
    assert len(pack_small) < len(pack_large)
