"""Tests for export endpoints."""

import pytest


async def _setup_book_with_content(client):
    """Create project → book → 2 chapters → scenes with text."""
    resp = await client.post(
        "/api/projects", json={"title": "导出测试项目"}
    )
    pid = resp.json()["id"]

    resp = await client.post(
        "/api/books",
        json={"project_id": pid, "title": "测试之书"},
    )
    bid = resp.json()["id"]

    # Chapter 1 with 2 scenes
    resp = await client.post(
        "/api/chapters",
        json={
            "book_id": bid,
            "title": "第一章 启程",
            "sort_order": 0,
        },
    )
    cid1 = resp.json()["id"]

    resp = await client.post(
        "/api/scenes",
        json={
            "chapter_id": cid1,
            "title": "场景一",
            "sort_order": 0,
        },
    )
    sid1 = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid1}/versions",
        json={"content_md": "林远站在飞船驾驶舱里。"},
    )

    resp = await client.post(
        "/api/scenes",
        json={
            "chapter_id": cid1,
            "title": "场景二",
            "sort_order": 1,
        },
    )
    sid2 = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid2}/versions",
        json={"content_md": "引擎发出异常的轰鸣声。"},
    )

    # Chapter 2 with 1 scene
    resp = await client.post(
        "/api/chapters",
        json={
            "book_id": bid,
            "title": "第二章 发现",
            "sort_order": 1,
        },
    )
    cid2 = resp.json()["id"]

    resp = await client.post(
        "/api/scenes",
        json={
            "chapter_id": cid2,
            "title": "场景三",
            "sort_order": 0,
        },
    )
    sid3 = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid3}/versions",
        json={"content_md": "他发现了外星遗迹。"},
    )

    return pid, bid, cid1, cid2


@pytest.mark.asyncio
async def test_export_markdown_full_book(client):
    """Export full book as Markdown with heading hierarchy."""
    _pid, bid, _cid1, _cid2 = (
        await _setup_book_with_content(client)
    )

    resp = await client.get(
        f"/api/export/markdown?book_id={bid}"
    )
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "content-disposition" in resp.headers
    text = resp.text

    assert text.startswith("# 测试之书")
    assert "## 第一章 启程" in text
    assert "## 第二章 发现" in text
    assert "林远站在飞船驾驶舱里。" in text
    assert "引擎发出异常的轰鸣声。" in text
    assert "他发现了外星遗迹。" in text


@pytest.mark.asyncio
async def test_export_markdown_single_chapter(client):
    """Export single chapter as Markdown."""
    _pid, bid, cid1, _cid2 = (
        await _setup_book_with_content(client)
    )

    resp = await client.get(
        f"/api/export/markdown?book_id={bid}"
        f"&chapter_id={cid1}"
    )
    assert resp.status_code == 200
    text = resp.text

    assert text.startswith("# 第一章 启程")
    assert "林远站在飞船驾驶舱里。" in text
    assert "引擎发出异常的轰鸣声。" in text
    assert "他发现了外星遗迹。" not in text


@pytest.mark.asyncio
async def test_export_txt_full_book(client):
    """Export full book as plain text with CJK-width underlines."""
    _pid, bid, _cid1, _cid2 = (
        await _setup_book_with_content(client)
    )

    resp = await client.get(
        f"/api/export/txt?book_id={bid}"
    )
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "content-disposition" in resp.headers
    text = resp.text

    assert "测试之书" in text
    assert "第一章 启程" in text
    assert "第二章 发现" in text
    assert "林远站在飞船驾驶舱里。" in text
    assert "他发现了外星遗迹。" in text
    assert "# " not in text
    assert "## " not in text
    # CJK-width underline: "测试之书" = 4 CJK chars = 8 display width
    assert "========" in text


@pytest.mark.asyncio
async def test_export_txt_single_chapter(client):
    """Export single chapter as plain text."""
    _pid, bid, cid1, _cid2 = (
        await _setup_book_with_content(client)
    )

    resp = await client.get(
        f"/api/export/txt?book_id={bid}&chapter_id={cid1}"
    )
    assert resp.status_code == 200
    text = resp.text

    assert "第一章 启程" in text
    assert "林远站在飞船驾驶舱里。" in text
    assert "他发现了外星遗迹。" not in text


@pytest.mark.asyncio
async def test_export_markdown_404_book(client):
    resp = await client.get(
        "/api/export/markdown?book_id=9999"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_txt_404_book(client):
    resp = await client.get(
        "/api/export/txt?book_id=9999"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_markdown_404_chapter(client):
    """Chapter not found or not in book."""
    _pid, bid, _cid1, _cid2 = (
        await _setup_book_with_content(client)
    )

    resp = await client.get(
        f"/api/export/markdown?book_id={bid}"
        "&chapter_id=9999"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_txt_404_chapter(client):
    _pid, bid, _cid1, _cid2 = (
        await _setup_book_with_content(client)
    )

    resp = await client.get(
        f"/api/export/txt?book_id={bid}&chapter_id=9999"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_empty_book_markdown(client):
    """Export book with no chapters returns title only."""
    resp = await client.post(
        "/api/projects", json={"title": "空项目"}
    )
    pid = resp.json()["id"]
    resp = await client.post(
        "/api/books",
        json={"project_id": pid, "title": "空书"},
    )
    bid = resp.json()["id"]

    resp = await client.get(
        f"/api/export/markdown?book_id={bid}"
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "# 空书"


@pytest.mark.asyncio
async def test_export_empty_book_txt(client):
    """TXT export of empty book returns title + underline."""
    resp = await client.post(
        "/api/projects", json={"title": "空项目2"}
    )
    pid = resp.json()["id"]
    resp = await client.post(
        "/api/books",
        json={"project_id": pid, "title": "空书"},
    )
    bid = resp.json()["id"]

    resp = await client.get(
        f"/api/export/txt?book_id={bid}"
    )
    assert resp.status_code == 200
    assert "空书" in resp.text
    # CJK underline: "空书" = 2 CJK chars = 4 display width
    assert "====" in resp.text
