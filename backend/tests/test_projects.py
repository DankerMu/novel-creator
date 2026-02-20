import pytest


@pytest.mark.asyncio
async def test_crud_project(client):
    # Create
    resp = await client.post(
        "/api/projects",
        json={"title": "测试小说", "description": "一个测试项目"},
    )
    assert resp.status_code == 201
    project = resp.json()
    pid = project["id"]
    assert project["title"] == "测试小说"

    # List
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Get
    resp = await client.get(f"/api/projects/{pid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "测试小说"

    # Update
    resp = await client.put(f"/api/projects/{pid}", json={"title": "更新后的标题"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "更新后的标题"

    # Delete
    resp = await client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 204

    # Verify deleted
    resp = await client.get(f"/api/projects/{pid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_crud_book(client):
    # Create project first
    resp = await client.post("/api/projects", json={"title": "P1"})
    pid = resp.json()["id"]

    # Create book
    resp = await client.post("/api/books", json={"project_id": pid, "title": "第一卷"})
    assert resp.status_code == 201
    bid = resp.json()["id"]

    # List
    resp = await client.get(f"/api/books?project_id={pid}")
    assert len(resp.json()) == 1

    # Update
    resp = await client.put(f"/api/books/{bid}", json={"title": "卷一·起"})
    assert resp.json()["title"] == "卷一·起"

    # Delete
    resp = await client.delete(f"/api/books/{bid}")
    assert resp.status_code == 204

    # Book with invalid project
    resp = await client.post("/api/books", json={"project_id": 9999, "title": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_crud_chapter(client):
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]
    resp = await client.post("/api/books", json={"project_id": pid, "title": "B"})
    bid = resp.json()["id"]

    # Create chapter
    resp = await client.post("/api/chapters", json={"book_id": bid, "title": "第一章"})
    assert resp.status_code == 201
    cid = resp.json()["id"]
    assert resp.json()["status"] == "draft"

    # Update status
    resp = await client.put(f"/api/chapters/{cid}", json={"status": "done"})
    assert resp.json()["status"] == "done"

    # Delete
    resp = await client.delete(f"/api/chapters/{cid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_crud_scene_and_versions(client):
    # Setup hierarchy
    resp = await client.post("/api/projects", json={"title": "P"})
    pid = resp.json()["id"]
    resp = await client.post("/api/books", json={"project_id": pid, "title": "B"})
    bid = resp.json()["id"]
    resp = await client.post("/api/chapters", json={"book_id": bid, "title": "C"})
    cid = resp.json()["id"]

    # Create scene
    resp = await client.post("/api/scenes", json={"chapter_id": cid, "title": "场景一"})
    assert resp.status_code == 201
    sid = resp.json()["id"]

    # Initial version should exist
    resp = await client.get(f"/api/scenes/{sid}/versions")
    assert len(resp.json()) == 1
    assert resp.json()[0]["version"] == 1

    # Save new version
    resp = await client.post(
        f"/api/scenes/{sid}/versions",
        json={"content_md": "这是场景的正文内容。"}
    )
    assert resp.status_code == 201
    assert resp.json()["version"] == 2
    assert resp.json()["char_count"] == 10

    # Get latest version
    resp = await client.get(f"/api/scenes/{sid}/versions/latest")
    assert resp.json()["version"] == 2
    assert resp.json()["content_md"] == "这是场景的正文内容。"


@pytest.mark.asyncio
async def test_project_tree(client):
    # Build hierarchy
    resp = await client.post("/api/projects", json={"title": "我的小说"})
    pid = resp.json()["id"]
    resp = await client.post("/api/books", json={"project_id": pid, "title": "第一卷"})
    bid = resp.json()["id"]
    resp = await client.post("/api/chapters", json={"book_id": bid, "title": "第一章"})
    cid = resp.json()["id"]
    await client.post("/api/scenes", json={"chapter_id": cid, "title": "开篇"})
    await client.post("/api/scenes", json={"chapter_id": cid, "title": "冲突"})

    # Get tree
    resp = await client.get(f"/api/projects/{pid}/tree")
    assert resp.status_code == 200
    tree = resp.json()
    assert tree["title"] == "我的小说"
    assert len(tree["books"]) == 1
    assert len(tree["books"][0]["chapters"]) == 1
    assert len(tree["books"][0]["chapters"][0]["scenes"]) == 2


@pytest.mark.asyncio
async def test_404_errors(client):
    assert (await client.get("/api/projects/999")).status_code == 404
    assert (await client.get("/api/books/999")).status_code == 404
    assert (await client.get("/api/chapters/999")).status_code == 404
    assert (await client.get("/api/scenes/999")).status_code == 404
    assert (await client.delete("/api/projects/999")).status_code == 404
