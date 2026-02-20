"""Tests for chapter summary endpoints with mocked LLM."""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.ai_schemas import ChapterSummaryModel


async def _setup_chapter_with_text(client):
    """Create project → book → chapter → scene with text."""
    resp = await client.post(
        "/api/projects", json={"title": "摘要测试项目"}
    )
    pid = resp.json()["id"]

    resp = await client.post(
        "/api/books",
        json={"project_id": pid, "title": "第一卷"},
    )
    bid = resp.json()["id"]

    resp = await client.post(
        "/api/chapters",
        json={"book_id": bid, "title": "第一章"},
    )
    cid = resp.json()["id"]

    resp = await client.post(
        "/api/scenes",
        json={"chapter_id": cid, "title": "场景一"},
    )
    sid = resp.json()["id"]

    # Add text content to the scene
    await client.post(
        f"/api/scenes/{sid}/versions",
        json={
            "content_md": "林远站在飞船驾驶舱里，"
            "望着窗外的荒漠星球。引擎发出异常的轰鸣声。",
            "created_by": "user",
        },
    )
    return pid, bid, cid, sid


MOCK_SUMMARY = ChapterSummaryModel(
    narrative="林远在荒漠星球遭遇飞船故障，"
    "必须在恶劣环境中寻找修复方案。",
    key_events=["飞船引擎故障", "发现外星遗迹"],
    keywords=["飞船", "荒漠星球", "引擎故障"],
    entities=["林远", "荒漠星球", "飞船"],
    plot_threads=["引擎修复", "外星文明线索"],
)


@pytest.mark.asyncio
async def test_mark_done_generates_summary(client):
    """Mark chapter done triggers summary generation."""
    _pid, _bid, cid, _sid = await _setup_chapter_with_text(
        client
    )

    mock_create = AsyncMock(return_value=MOCK_SUMMARY)

    with patch(
        "app.services.summary.instructor_client"
    ) as mock_client:
        mock_client.chat.completions.create = mock_create
        resp = await client.post(
            f"/api/chapters/{cid}/mark-done"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["chapter_id"] == cid
    assert "林远" in data["summary_md"]
    assert "飞船" in data["keywords"]
    assert "林远" in data["entities"]
    assert len(data["plot_threads"]) == 2

    # Verify chapter status is now "done"
    ch_resp = await client.get(f"/api/chapters/{cid}")
    assert ch_resp.json()["status"] == "done"


@pytest.mark.asyncio
async def test_mark_done_404(client):
    resp = await client.post("/api/chapters/9999/mark-done")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_summary(client):
    """Get summary after generation."""
    _pid, _bid, cid, _sid = await _setup_chapter_with_text(
        client
    )

    mock_create = AsyncMock(return_value=MOCK_SUMMARY)

    with patch(
        "app.services.summary.instructor_client"
    ) as mock_client:
        mock_client.chat.completions.create = mock_create
        await client.post(f"/api/chapters/{cid}/mark-done")

    resp = await client.get(
        f"/api/chapters/{cid}/summary"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary_md"] == MOCK_SUMMARY.narrative


@pytest.mark.asyncio
async def test_get_summary_404(client):
    """Summary not found for chapter without summary."""
    resp = await client.post(
        "/api/projects", json={"title": "空项目"}
    )
    pid = resp.json()["id"]
    resp = await client.post(
        "/api/books",
        json={"project_id": pid, "title": "卷"},
    )
    bid = resp.json()["id"]
    resp = await client.post(
        "/api/chapters",
        json={"book_id": bid, "title": "章"},
    )
    cid = resp.json()["id"]

    resp = await client.get(
        f"/api/chapters/{cid}/summary"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_extract_chapter_summary(client):
    """Manual summary extraction endpoint."""
    _pid, _bid, cid, _sid = await _setup_chapter_with_text(
        client
    )

    mock_create = AsyncMock(return_value=MOCK_SUMMARY)

    with patch(
        "app.services.summary.instructor_client"
    ) as mock_client:
        mock_client.chat.completions.create = mock_create
        resp = await client.post(
            f"/api/extract/chapter-summary?chapter_id={cid}"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "引擎故障" in data["keywords"]


@pytest.mark.asyncio
async def test_summary_in_context_pack(client):
    """Summary appears in next chapter's Context Pack."""
    _pid, _bid, cid1, _sid = (
        await _setup_chapter_with_text(client)
    )

    # Generate summary for chapter 1
    mock_create = AsyncMock(return_value=MOCK_SUMMARY)
    with patch(
        "app.services.summary.instructor_client"
    ) as mock_client:
        mock_client.chat.completions.create = mock_create
        await client.post(f"/api/chapters/{cid1}/mark-done")

    # Create chapter 2 in the same book
    ch1_resp = await client.get(f"/api/chapters/{cid1}")
    book_id = ch1_resp.json()["book_id"]
    resp = await client.post(
        "/api/chapters",
        json={
            "book_id": book_id,
            "title": "第二章",
            "sort_order": 1,
        },
    )
    cid2 = resp.json()["id"]

    # Verify summary in context pack
    from app.core.database import get_db
    from app.main import app
    from app.services.context_pack import (
        get_chapter_summaries_text,
    )

    db_gen = app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()

    summaries_text = await get_chapter_summaries_text(
        db, cid2
    )
    assert "林远" in summaries_text
    assert "前文摘要" in summaries_text
