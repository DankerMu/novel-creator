"""Tests for word count budget check and rewrite endpoint."""

import pytest

from app.services.word_count import build_rewrite_prompt, check_word_budget

# ---------- Helpers ----------

async def _setup_project(client) -> int:
    resp = await client.post("/api/projects", json={"title": "WC Test"})
    return resp.json()["id"]


async def _setup_book(client, project_id: int) -> int:
    resp = await client.post(
        "/api/books", json={"project_id": project_id, "title": "Book 1"}
    )
    return resp.json()["id"]


async def _setup_chapter(client, book_id: int) -> int:
    resp = await client.post(
        "/api/chapters",
        json={"book_id": book_id, "title": "Chapter 1", "sort_order": 0},
    )
    return resp.json()["id"]


async def _setup_scene(client, chapter_id: int) -> int:
    resp = await client.post(
        "/api/scenes",
        json={"chapter_id": chapter_id, "title": "Scene 1"},
    )
    return resp.json()["id"]


# ---------- Unit tests: check_word_budget ----------

def test_within_budget():
    """Text within ±15% tolerance returns 'within'."""
    text = "a" * 1000
    result = check_word_budget(text, target_chars=1000)
    assert result["status"] == "within"
    assert result["actual_chars"] == 1000
    assert result["delta"] == 0
    assert result["deviation"] == 0.0
    assert result["suggestion"] is None


def test_within_budget_at_tolerance_boundary():
    """Text at exactly 15% over is still 'within'."""
    text = "a" * 1150  # 15% over 1000
    result = check_word_budget(text, target_chars=1000, tolerance=0.15)
    assert result["status"] == "within"
    assert result["suggestion"] is None


def test_over_budget():
    """Text exceeding tolerance suggests compression."""
    text = "a" * 1200  # 20% over 1000
    result = check_word_budget(text, target_chars=1000)
    assert result["status"] == "over"
    assert result["delta"] == 200
    assert result["suggestion"] == "compress"


def test_under_budget():
    """Text below tolerance suggests expansion."""
    text = "a" * 700  # 30% under 1000
    result = check_word_budget(text, target_chars=1000)
    assert result["status"] == "under"
    assert result["delta"] == -300
    assert result["suggestion"] == "expand"


def test_custom_tolerance():
    """Custom tolerance changes the threshold."""
    text = "a" * 900  # 10% under
    # Default tolerance 15% → within
    assert check_word_budget(text, 1000)["status"] == "within"
    # Strict tolerance 5% → under
    assert check_word_budget(text, 1000, tolerance=0.05)["status"] == "under"


def test_zero_target():
    """Zero target_chars doesn't crash."""
    result = check_word_budget("hello", target_chars=0)
    assert result["status"] == "over"
    assert result["actual_chars"] == 5


def test_empty_text():
    """Empty text is under budget."""
    result = check_word_budget("", target_chars=1000)
    assert result["status"] == "under"
    assert result["actual_chars"] == 0
    assert result["suggestion"] == "expand"


def test_deviation_precision():
    """Deviation is rounded to 3 decimal places."""
    text = "a" * 1234
    result = check_word_budget(text, target_chars=1000)
    assert isinstance(result["deviation"], float)
    assert result["deviation"] == 0.234


# ---------- Unit tests: build_rewrite_prompt ----------

def test_expand_prompt_contains_key_info():
    """Expand prompt includes actual chars, target, and the text."""
    prompt = build_rewrite_prompt("Some text.", 2000, "expand")
    assert "10 字" in prompt
    assert "2000 字" in prompt
    assert "Some text." in prompt
    assert "扩写" in prompt


def test_compress_prompt_contains_key_info():
    """Compress prompt includes actual chars, target, and the text."""
    prompt = build_rewrite_prompt("Some long text.", 500, "compress")
    assert "15 字" in prompt
    assert "500 字" in prompt
    assert "Some long text." in prompt
    assert "精简" in prompt


# ---------- API tests ----------

@pytest.mark.asyncio
async def test_word_count_check_endpoint(client):
    """POST /api/generate/word-count-check returns budget status."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    cid = await _setup_chapter(client, bid)
    sid = await _setup_scene(client, cid)

    resp = await client.post(
        "/api/generate/word-count-check",
        json={
            "scene_id": sid,
            "text": "a" * 1200,
            "target_chars": 1000,
            "mode": "compress",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "over"
    assert data["actual_chars"] == 1200
    assert data["suggestion"] == "compress"


@pytest.mark.asyncio
async def test_word_count_check_within(client):
    """Within-budget text returns status='within'."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    cid = await _setup_chapter(client, bid)
    sid = await _setup_scene(client, cid)

    resp = await client.post(
        "/api/generate/word-count-check",
        json={
            "scene_id": sid,
            "text": "a" * 1000,
            "target_chars": 1000,
            "mode": "expand",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "within"


@pytest.mark.asyncio
async def test_rewrite_rejects_within_budget(client):
    """Rewrite returns 400 if text is already within budget."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    cid = await _setup_chapter(client, bid)
    sid = await _setup_scene(client, cid)

    resp = await client.post(
        "/api/generate/rewrite",
        json={
            "scene_id": sid,
            "text": "a" * 1000,
            "target_chars": 1000,
            "mode": "compress",
        },
    )
    assert resp.status_code == 400
    assert "within budget" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_rewrite_invalid_scene(client):
    """Rewrite returns 404 for non-existent scene."""
    resp = await client.post(
        "/api/generate/rewrite",
        json={
            "scene_id": 999999,
            "text": "a" * 2000,
            "target_chars": 1000,
            "mode": "compress",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rewrite_invalid_mode(client):
    """Rewrite returns 422 for invalid mode."""
    resp = await client.post(
        "/api/generate/rewrite",
        json={
            "scene_id": 1,
            "text": "some text",
            "target_chars": 1000,
            "mode": "invalid",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rewrite_target_chars_validation(client):
    """target_chars must be between 100 and 50000."""
    resp = await client.post(
        "/api/generate/word-count-check",
        json={
            "scene_id": 1,
            "text": "some text",
            "target_chars": 50,
            "mode": "expand",
        },
    )
    assert resp.status_code == 422
