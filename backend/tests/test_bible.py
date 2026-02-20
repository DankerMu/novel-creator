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

    # Get fields (auto-create)
    resp = await client.get(f"/api/bible?project_id={pid}")
    field = resp.json()[0]
    fid = field["id"]

    # Update content
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

    # Get and lock two fields
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

    # Check locked endpoint
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
