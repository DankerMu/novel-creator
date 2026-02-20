import pytest


@pytest.mark.asyncio
async def test_bible_auto_create_defaults(client):
    """First GET creates default Bible fields."""
    resp = await client.post(
        "/api/projects", json={"title": "Bible Test"}
    )
    pid = resp.json()["id"]

    resp = await client.get(f"/api/bible?project_id={pid}")
    assert resp.status_code == 200
    fields = resp.json()
    assert len(fields) == 9
    keys = [f["key"] for f in fields]
    assert "Genre" in keys
    assert "Style" in keys
    assert "Characters" in keys


@pytest.mark.asyncio
async def test_bible_update_field(client):
    resp = await client.post(
        "/api/projects", json={"title": "P"}
    )
    pid = resp.json()["id"]

    resp = await client.get(f"/api/bible?project_id={pid}")
    field = resp.json()[0]
    fid = field["id"]

    resp = await client.put(
        f"/api/bible/{fid}",
        json={"value_md": "科幻", "locked": True},
    )
    assert resp.status_code == 200
    assert resp.json()["value_md"] == "科幻"
    assert resp.json()["locked"] is True


@pytest.mark.asyncio
async def test_bible_locked_fields(client):
    """Locked fields endpoint returns only locked ones."""
    resp = await client.post(
        "/api/projects", json={"title": "P"}
    )
    pid = resp.json()["id"]

    resp = await client.get(f"/api/bible?project_id={pid}")
    fields = resp.json()

    await client.put(
        f"/api/bible/{fields[0]['id']}",
        json={"value_md": "科幻", "locked": True},
    )
    await client.put(
        f"/api/bible/{fields[1]['id']}",
        json={"value_md": "第三人称", "locked": True},
    )

    resp = await client.get(f"/api/bible/locked?project_id={pid}")
    assert resp.status_code == 200
    locked = resp.json()
    assert len(locked) == 2
    assert all(f["locked"] for f in locked)


@pytest.mark.asyncio
async def test_bible_404(client):
    resp = await client.put(
        "/api/bible/9999", json={"value_md": "x"}
    )
    assert resp.status_code == 404

    resp = await client.get("/api/bible?project_id=9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bible_empty_value(client):
    """Empty string value_md is valid."""
    resp = await client.post(
        "/api/projects", json={"title": "P"}
    )
    pid = resp.json()["id"]

    resp = await client.get(f"/api/bible?project_id={pid}")
    fid = resp.json()[0]["id"]

    resp = await client.put(
        f"/api/bible/{fid}", json={"value_md": ""}
    )
    assert resp.status_code == 200
    assert resp.json()["value_md"] == ""


@pytest.mark.asyncio
async def test_bible_long_value(client):
    """Long value_md is accepted."""
    resp = await client.post(
        "/api/projects", json={"title": "P"}
    )
    pid = resp.json()["id"]

    resp = await client.get(f"/api/bible?project_id={pid}")
    fid = resp.json()[0]["id"]

    long_text = "这是一段很长的文本。" * 500
    resp = await client.put(
        f"/api/bible/{fid}", json={"value_md": long_text}
    )
    assert resp.status_code == 200
    assert resp.json()["value_md"] == long_text


@pytest.mark.asyncio
async def test_bible_special_characters(client):
    """Markdown and special chars in value_md."""
    resp = await client.post(
        "/api/projects", json={"title": "P"}
    )
    pid = resp.json()["id"]

    resp = await client.get(f"/api/bible?project_id={pid}")
    fid = resp.json()[0]["id"]

    md_text = "# 标题\n**粗体** `代码` <script>alert(1)</script>"
    resp = await client.put(
        f"/api/bible/{fid}", json={"value_md": md_text}
    )
    assert resp.status_code == 200
    assert resp.json()["value_md"] == md_text


@pytest.mark.asyncio
async def test_bible_cascade_delete(client):
    """Bible fields are deleted when project is deleted."""
    resp = await client.post(
        "/api/projects", json={"title": "P"}
    )
    pid = resp.json()["id"]

    # Create bible fields
    resp = await client.get(f"/api/bible?project_id={pid}")
    assert len(resp.json()) == 9

    # Delete project
    resp = await client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 204

    # Bible fields should be gone
    resp = await client.get(f"/api/bible?project_id={pid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bible_toggle_lock_off(client):
    """Unlock a previously locked field."""
    resp = await client.post(
        "/api/projects", json={"title": "P"}
    )
    pid = resp.json()["id"]

    resp = await client.get(f"/api/bible?project_id={pid}")
    fid = resp.json()[0]["id"]

    # Lock
    await client.put(
        f"/api/bible/{fid}", json={"locked": True}
    )
    # Unlock
    resp = await client.put(
        f"/api/bible/{fid}", json={"locked": False}
    )
    assert resp.json()["locked"] is False

    # Should not appear in locked endpoint
    resp = await client.get(
        f"/api/bible/locked?project_id={pid}"
    )
    assert len(resp.json()) == 0
