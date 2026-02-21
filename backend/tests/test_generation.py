"""Tests for AI generation endpoints with mocked LLM."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.ai_schemas import SceneCard


async def _setup_hierarchy(client):
    """Create project → book → chapter → scene with bible fields."""
    resp = await client.post(
        "/api/projects", json={"title": "AI测试项目"}
    )
    pid = resp.json()["id"]

    # Create and lock a bible field
    resp = await client.get(f"/api/bible?project_id={pid}")
    fields = resp.json()
    await client.put(
        f"/api/bible/{fields[0]['id']}",
        json={"value_md": "科幻", "locked": True},
    )

    resp = await client.post(
        "/api/books", json={"project_id": pid, "title": "第一卷"}
    )
    bid = resp.json()["id"]
    resp = await client.post(
        "/api/chapters", json={"book_id": bid, "title": "第一章"}
    )
    cid = resp.json()["id"]
    resp = await client.post(
        "/api/scenes",
        json={"chapter_id": cid, "title": "开篇场景"},
    )
    sid = resp.json()["id"]
    return pid, bid, cid, sid


MOCK_SCENE_CARD_DICT = {
    "title": "飞船坠落",
    "location": "荒漠星球",
    "time": "公元3050年",
    "characters": ["林远", "AI助手"],
    "conflict": "飞船引擎故障，必须在日落前修复",
    "turning_point": "发现外星遗迹",
    "reveal": "遗迹中有修复零件",
    "target_chars": 1500,
}

MOCK_SCENE_CARD = SceneCard(**MOCK_SCENE_CARD_DICT)


def _mock_llm_response(data: dict):
    """Create a mock LLM response with JSON content."""
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(data, ensure_ascii=False)
            )
        )
    ]
    return mock_resp


@pytest.mark.asyncio
async def test_generate_scene_card(client):
    """Scene card generation with mocked LLM."""
    _pid, _bid, cid, sid = await _setup_hierarchy(client)

    mock_llm = AsyncMock(
        return_value=_mock_llm_response(MOCK_SCENE_CARD_DICT)
    )

    with patch(
        "app.api.generation.call_llm", new=mock_llm
    ):
        resp = await client.post(
            "/api/generate/scene-card",
            json={
                "chapter_id": cid,
                "scene_id": sid,
                "hints": "要有紧迫感",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "飞船坠落"
    assert "林远" in data["characters"]
    assert data["target_chars"] == 1500

    # Verify context pack was included in the prompt
    call_args = mock_llm.call_args
    messages = call_args.args[0]
    user_msg = messages[1]["content"]
    assert "科幻" in user_msg  # locked bible field injected


@pytest.mark.asyncio
async def test_generate_scene_card_404(client):
    resp = await client.post(
        "/api/generate/scene-card",
        json={
            "chapter_id": 9999,
            "scene_id": 9999,
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stream_scene_draft(client):
    """SSE streaming with mocked LLM."""
    _pid, _bid, _cid, sid = await _setup_hierarchy(client)

    async def mock_stream(*args, **kwargs):
        chunks = ["林远", "望着", "窗外的", "荒漠星球"]
        for chunk in chunks:
            yield chunk

    with patch(
        "app.api.generation.call_llm_stream",
        side_effect=mock_stream,
    ):
        resp = await client.post(
            "/api/generate/scene-draft",
            json={
                "scene_id": sid,
                "scene_card": MOCK_SCENE_CARD.model_dump(),
            },
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "text/event-stream"
    )

    # Parse SSE events
    lines = resp.text.strip().split("\n\n")
    events = []
    for line in lines:
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # Should have text chunks + done event
    assert len(events) >= 2
    text_events = [e for e in events if "text" in e]
    assert len(text_events) >= 1

    done_event = events[-1]
    assert done_event["done"] is True
    assert done_event["char_count"] > 0


@pytest.mark.asyncio
async def test_stream_scene_draft_404(client):
    resp = await client.post(
        "/api/generate/scene-draft",
        json={
            "scene_id": 9999,
            "scene_card": MOCK_SCENE_CARD.model_dump(),
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_context_pack_includes_bible(client):
    """Context Pack includes locked Bible fields."""
    pid, _bid, cid, sid = await _setup_hierarchy(client)

    # Get a fresh db session from the app
    from app.core.database import get_db
    from app.main import app
    from app.services.context_pack import assemble_context_pack

    db_gen = app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()

    context = await assemble_context_pack(
        db, sid, cid, pid
    )
    assert "科幻" in context
    assert "故事设定约束" in context
