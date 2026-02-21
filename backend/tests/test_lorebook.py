import pytest

from app.services.lorebook import _truncate_to_sentence, match_triggers

# ==================== CRUD ====================

@pytest.mark.asyncio
async def test_create_lore_entry(client):
    resp = await client.post("/api/projects", json={"title": "Lore Test"})
    pid = resp.json()["id"]

    resp = await client.post("/api/lore", json={
        "project_id": pid,
        "type": "Character",
        "title": "张三",
        "aliases": ["老张", "张先生"],
        "content_md": "一个神秘的人物。",
        "secrets_md": "其实是卧底。",
        "triggers": {"keywords": ["张三", "老张"], "and_keywords": []},
        "priority": 8,
        "locked": False,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "张三"
    assert data["type"] == "Character"
    assert data["aliases"] == ["老张", "张先生"]
    assert data["priority"] == 8
    assert data["triggers"]["keywords"] == ["张三", "老张"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_list_lore_entries(client):
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    await client.post("/api/lore", json={
        "project_id": pid, "title": "Entry A", "priority": 3,
    })
    await client.post("/api/lore", json={
        "project_id": pid, "title": "Entry B", "priority": 9,
    })

    resp = await client.get(f"/api/lore?project_id={pid}")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 2
    # Should be sorted by priority DESC
    assert entries[0]["title"] == "Entry B"
    assert entries[1]["title"] == "Entry A"


@pytest.mark.asyncio
async def test_get_lore_entry(client):
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    resp = await client.post("/api/lore", json={
        "project_id": pid, "title": "Solo",
    })
    eid = resp.json()["id"]

    resp = await client.get(f"/api/lore/{eid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Solo"


@pytest.mark.asyncio
async def test_update_lore_entry(client):
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    resp = await client.post("/api/lore", json={
        "project_id": pid, "title": "Before",
    })
    eid = resp.json()["id"]

    resp = await client.put(f"/api/lore/{eid}", json={
        "title": "After",
        "aliases": ["别名"],
        "priority": 10,
        "triggers": {"keywords": ["new_kw"], "and_keywords": ["a", "b"]},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "After"
    assert data["aliases"] == ["别名"]
    assert data["priority"] == 10
    assert data["triggers"]["keywords"] == ["new_kw"]
    assert data["triggers"]["and_keywords"] == ["a", "b"]


@pytest.mark.asyncio
async def test_delete_lore_entry(client):
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    resp = await client.post("/api/lore", json={
        "project_id": pid, "title": "Doomed",
    })
    eid = resp.json()["id"]

    resp = await client.delete(f"/api/lore/{eid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/lore/{eid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lore_404(client):
    resp = await client.get("/api/lore/9999")
    assert resp.status_code == 404

    resp = await client.put("/api/lore/9999", json={"title": "x"})
    assert resp.status_code == 404

    resp = await client.delete("/api/lore/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lore_project_not_found(client):
    resp = await client.get("/api/lore?project_id=9999")
    assert resp.status_code == 404

    resp = await client.post("/api/lore", json={
        "project_id": 9999, "title": "x",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lore_cascade_delete(client):
    """Lore entries deleted when project is deleted."""
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    await client.post("/api/lore", json={
        "project_id": pid, "title": "Will vanish",
    })

    resp = await client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/lore?project_id={pid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lore_chinese_content(client):
    """Chinese content stored and returned correctly."""
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    resp = await client.post("/api/lore", json={
        "project_id": pid,
        "title": "龙王",
        "aliases": ["东海龙王", "敖广"],
        "content_md": "东海龙宫的统治者，掌管降雨。",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "龙王"
    assert "东海龙王" in data["aliases"]
    assert "降雨" in data["content_md"]


# ==================== Trigger Matching ====================

def _make_entry(**kwargs):
    """Create a mock LoreEntry-like object for trigger testing."""
    import json

    class MockEntry:
        pass

    e = MockEntry()
    e.title = kwargs.get("title", "TestEntry")
    e.aliases_json = json.dumps(kwargs.get("aliases", []), ensure_ascii=False)
    e.triggers_json = json.dumps(
        kwargs.get("triggers", {"keywords": [], "and_keywords": []}),
        ensure_ascii=False,
    )
    return e


def test_trigger_match_by_title():
    entry = _make_entry(title="张三")
    assert match_triggers(entry, "今天张三来了") is True
    assert match_triggers(entry, "今天李四来了") is False


def test_trigger_match_by_alias():
    entry = _make_entry(title="张三", aliases=["老张", "张先生"])
    assert match_triggers(entry, "老张说") is True
    assert match_triggers(entry, "张先生好") is True
    assert match_triggers(entry, "王五说") is False


def test_trigger_match_by_keyword_or():
    entry = _make_entry(
        title="NoMatch",
        triggers={"keywords": ["魔法", "咒语"], "and_keywords": []},
    )
    assert match_triggers(entry, "他施展了魔法") is True
    assert match_triggers(entry, "念了一段咒语") is True
    assert match_triggers(entry, "普通的日子") is False


def test_trigger_match_and_keywords():
    """AND keywords alone should NOT trigger — they are constraints on primary match."""
    entry = _make_entry(
        title="NoMatch",
        triggers={"keywords": [], "and_keywords": ["黑暗", "森林"]},
    )
    # No primary match (title "NoMatch" not in text, no keywords), so AND alone won't trigger
    assert match_triggers(entry, "黑暗的森林深处") is False
    assert match_triggers(entry, "黑暗的夜晚") is False
    assert match_triggers(entry, "美丽的森林") is False


def test_trigger_match_and_keywords_with_primary():
    """AND keywords constrain primary match: both OR + AND must satisfy."""
    entry = _make_entry(
        title="NoMatch",
        triggers={"keywords": ["魔法"], "and_keywords": ["黑暗", "森林"]},
    )
    # Primary keyword matches, AND keywords both present
    assert match_triggers(entry, "黑暗的森林里施展了魔法") is True
    # Primary matches but AND incomplete
    assert match_triggers(entry, "魔法在黑暗中") is False
    # AND complete but no primary match
    assert match_triggers(entry, "黑暗的森林深处") is False


def test_trigger_match_empty_text():
    entry = _make_entry(title="张三")
    assert match_triggers(entry, "") is False


def test_trigger_match_case_insensitive():
    entry = _make_entry(
        title="Dragon",
        triggers={"keywords": ["FIRE"], "and_keywords": []},
    )
    assert match_triggers(entry, "the dragon breathes fire") is True
    assert match_triggers(entry, "THE DRAGON BREATHES FIRE") is True


# ==================== Budget Truncation ====================

def test_truncate_within_budget():
    text = "短文本。"
    assert _truncate_to_sentence(text, 100) == text


def test_truncate_at_sentence_boundary():
    text = "第一句话。第二句话。第三句话。"
    result = _truncate_to_sentence(text, 12)
    # Should cut at a sentence boundary
    assert result.endswith("。")
    assert len(result) <= 12


def test_truncate_hard_limit():
    text = "一" * 200
    result = _truncate_to_sentence(text, 50)
    assert len(result) <= 50


# ==================== Import / Export ====================

@pytest.mark.asyncio
async def test_import_sillytavern(client):
    resp = await client.post("/api/projects", json={"title": "Import Test"})
    pid = resp.json()["id"]

    payload = {
        "project_id": pid,
        "entries": {
            "0": {
                "key": ["魔法"],
                "keysecondary": ["火焰", "冰霜"],
                "comment": "魔法系统",
                "content": "这个世界的魔法分为元素系。",
                "order": 7,
                "constant": True,
            },
            "1": {
                "key": ["王国"],
                "keysecondary": [],
                "comment": "亚特兰王国",
                "content": "大陆东部的强大王国。",
                "order": 3,
                "constant": False,
            },
        },
    }

    resp = await client.post("/api/lore/import", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = {e["title"] for e in data}
    assert "魔法系统" in titles
    assert "亚特兰王国" in titles

    # Verify the imported entry details
    magic = next(e for e in data if e["title"] == "魔法系统")
    assert magic["triggers"]["keywords"] == ["魔法"]
    assert magic["triggers"]["and_keywords"] == ["火焰", "冰霜"]
    assert magic["priority"] == 7
    assert magic["locked"] is True


@pytest.mark.asyncio
async def test_export_sillytavern(client):
    resp = await client.post("/api/projects", json={"title": "Export Test"})
    pid = resp.json()["id"]

    await client.post("/api/lore", json={
        "project_id": pid,
        "title": "角色A",
        "triggers": {"keywords": ["角色A"], "and_keywords": []},
        "priority": 5,
        "locked": True,
    })

    resp = await client.get(f"/api/lore/export?project_id={pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "originalData" in data
    assert "0" in data["entries"]
    entry_0 = data["entries"]["0"]
    assert entry_0["comment"] == "角色A"
    assert entry_0["key"] == ["角色A"]
    assert entry_0["constant"] is True


@pytest.mark.asyncio
async def test_import_missing_project_id(client):
    resp = await client.post("/api/lore/import", json={"entries": {}})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_project_not_found(client):
    resp = await client.post("/api/lore/import", json={
        "project_id": 9999, "entries": {},
    })
    assert resp.status_code == 404


# ==================== Locked entries always included ====================

@pytest.mark.asyncio
async def test_locked_entries_always_included(client):
    """Locked entries should appear in list regardless of triggers."""
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    # Create a locked entry
    resp = await client.post("/api/lore", json={
        "project_id": pid,
        "title": "World Rule",
        "locked": True,
        "priority": 10,
        "content_md": "重力为地球的两倍。",
    })
    assert resp.status_code == 201
    assert resp.json()["locked"] is True

    # Verify it shows in the list
    resp = await client.get(f"/api/lore?project_id={pid}")
    assert len(resp.json()) == 1
    assert resp.json()[0]["locked"] is True


@pytest.mark.asyncio
async def test_partial_update_preserves_fields(client):
    """Updating one field should not reset others."""
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    resp = await client.post("/api/lore", json={
        "project_id": pid,
        "title": "Original",
        "content_md": "内容",
        "priority": 7,
    })
    eid = resp.json()["id"]

    # Update only title
    resp = await client.put(f"/api/lore/{eid}", json={"title": "Updated"})
    data = resp.json()
    assert data["title"] == "Updated"
    assert data["content_md"] == "内容"
    assert data["priority"] == 7


@pytest.mark.asyncio
async def test_lore_default_values(client):
    """Creating with minimal fields uses proper defaults."""
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]

    resp = await client.post("/api/lore", json={
        "project_id": pid, "title": "Minimal",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "Concept"
    assert data["aliases"] == []
    assert data["content_md"] == ""
    assert data["secrets_md"] == ""
    assert data["priority"] == 5
    assert data["locked"] is False
    assert data["triggers"] == {"keywords": [], "and_keywords": []}
