"""Tests for consistency check service and API."""

import json

import pytest

from app.models.tables import KGEdge, KGNode
from app.services.consistency import run_consistency_check

# ---------- Helpers ----------

async def _setup_project(client) -> int:
    resp = await client.post("/api/projects", json={"title": "Consistency Test"})
    return resp.json()["id"]


async def _setup_book(client, project_id: int) -> int:
    resp = await client.post(
        "/api/books", json={"project_id": project_id, "title": "Book 1"}
    )
    return resp.json()["id"]


async def _setup_chapter(client, book_id: int, sort_order: int = 0) -> int:
    resp = await client.post(
        "/api/chapters",
        json={"book_id": book_id, "title": f"Chapter {sort_order}", "sort_order": sort_order},
    )
    return resp.json()["id"]


async def _setup_scene_with_text(client, chapter_id: int, text: str) -> int:
    resp = await client.post(
        "/api/scenes", json={"chapter_id": chapter_id, "title": "Scene"}
    )
    sid = resp.json()["id"]
    await client.post(
        f"/api/scenes/{sid}/versions",
        json={"content_md": text, "created_by": "user"},
    )
    return sid


def _make_node(
    project_id: int,
    label: str,
    name: str,
    properties: dict,
) -> KGNode:
    return KGNode(
        project_id=project_id,
        label=label,
        name=name,
        properties_json=json.dumps(properties, ensure_ascii=False),
    )


def _make_edge(
    project_id: int,
    source_node_id: int,
    target_node_id: int,
    relation: str,
    properties: dict | None = None,
) -> KGEdge:
    return KGEdge(
        project_id=project_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation=relation,
        properties_json=json.dumps(properties or {}, ensure_ascii=False),
    )


# ---------- Test: character_status ----------

@pytest.mark.asyncio
async def test_character_status_conflict(client, db_session):
    """Dead character appearing in later scene text is flagged."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)

    ch1 = await _setup_chapter(client, bid, sort_order=0)
    await _setup_scene_with_text(client, ch1, "The hero Lin Yuan died in battle.")

    ch2 = await _setup_chapter(client, bid, sort_order=1)
    await _setup_scene_with_text(client, ch2, "Lin Yuan arrived at the castle.")

    node = _make_node(pid, "Character", "Lin Yuan", {"status": "dead"})
    db_session.add(node)
    await db_session.flush()

    results = await run_consistency_check(db_session, pid)

    char_conflicts = [r for r in results if r["type"] == "character_status"]
    assert len(char_conflicts) >= 1
    conflict = char_conflicts[0]
    assert conflict["severity"] == "high"
    assert conflict["confidence"] == 1.0
    assert conflict["source"] == "rule"
    assert "Lin Yuan" in conflict["message"]
    assert len(conflict["evidence"]) >= 1
    assert len(conflict["evidence_locations"]) >= 1
    assert conflict["suggest_fix"]


@pytest.mark.asyncio
async def test_character_status_no_conflict(client, db_session):
    """Dead character not mentioned in any scene text produces no conflict."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    ch1 = await _setup_chapter(client, bid, sort_order=0)
    # Scene text does not mention the dead character by name
    await _setup_scene_with_text(client, ch1, "A brave warrior perished in battle.")

    node = _make_node(pid, "Character", "Lin Yuan", {"status": "dead"})
    db_session.add(node)
    await db_session.flush()

    results = await run_consistency_check(db_session, pid)
    char_conflicts = [r for r in results if r["type"] == "character_status"]
    assert char_conflicts == []


# ---------- Test: possession ----------

@pytest.mark.asyncio
async def test_possession_conflict(client, db_session):
    """Same item owned by two characters is flagged."""
    pid = await _setup_project(client)

    char_a = _make_node(pid, "Character", "Alice", {})
    char_b = _make_node(pid, "Character", "Bob", {})
    item = _make_node(pid, "Item", "Magic Sword", {})
    db_session.add_all([char_a, char_b, item])
    await db_session.flush()

    edge_a = _make_edge(pid, char_a.id, item.id, "owns")
    edge_b = _make_edge(pid, char_b.id, item.id, "owns")
    db_session.add_all([edge_a, edge_b])
    await db_session.flush()

    results = await run_consistency_check(db_session, pid)
    poss_conflicts = [r for r in results if r["type"] == "possession"]
    assert len(poss_conflicts) >= 1
    c = poss_conflicts[0]
    assert c["severity"] == "medium"
    assert "Magic Sword" in c["message"]
    assert "Alice" in c["message"] or "Bob" in c["message"]
    assert c["suggest_fix"]


@pytest.mark.asyncio
async def test_possession_no_conflict_single_owner(client, db_session):
    """Item with only one owner produces no possession conflict."""
    pid = await _setup_project(client)

    char_a = _make_node(pid, "Character", "Alice", {})
    item = _make_node(pid, "Item", "Shield", {})
    db_session.add_all([char_a, item])
    await db_session.flush()

    edge = _make_edge(pid, char_a.id, item.id, "owns")
    db_session.add(edge)
    await db_session.flush()

    results = await run_consistency_check(db_session, pid)
    poss_conflicts = [r for r in results if r["type"] == "possession"]
    assert poss_conflicts == []


# ---------- Test: repetition ----------

@pytest.mark.asyncio
async def test_repetition_detected(client, db_session):
    """Scene with a repeated n-gram is flagged."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    ch1 = await _setup_chapter(client, bid, sort_order=0)
    # Repeat the phrase 4 times so 4-gram appears >= 3 times in char ngrams
    repeated = "the quick brown fox " * 5
    await _setup_scene_with_text(client, ch1, repeated.strip())

    results = await run_consistency_check(db_session, pid, ngram_n=4, ngram_threshold=3)
    rep_conflicts = [r for r in results if r["type"] == "repetition"]
    assert len(rep_conflicts) >= 1
    c = rep_conflicts[0]
    assert c["severity"] == "low"
    assert c["confidence"] == 1.0
    assert c["suggest_fix"]


@pytest.mark.asyncio
async def test_repetition_configurable_threshold(client, db_session):
    """Higher threshold suppresses detection; lower threshold catches more."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    ch1 = await _setup_chapter(client, bid, sort_order=0)
    repeated = "alpha beta gamma delta " * 4
    await _setup_scene_with_text(client, ch1, repeated.strip())

    # High threshold: no conflicts
    results_high = await run_consistency_check(db_session, pid, ngram_n=4, ngram_threshold=10)
    rep_high = [r for r in results_high if r["type"] == "repetition"]
    assert rep_high == []

    # Low threshold: conflicts detected
    results_low = await run_consistency_check(db_session, pid, ngram_n=4, ngram_threshold=2)
    rep_low = [r for r in results_low if r["type"] == "repetition"]
    assert len(rep_low) >= 1


@pytest.mark.asyncio
async def test_repetition_no_false_positive(client, db_session):
    """Unique text produces no repetition conflict."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    ch1 = await _setup_chapter(client, bid, sort_order=0)
    await _setup_scene_with_text(
        client, ch1, "The sun rose over the distant mountains casting long shadows."
    )

    results = await run_consistency_check(db_session, pid, ngram_n=4, ngram_threshold=3)
    rep_conflicts = [r for r in results if r["type"] == "repetition"]
    assert rep_conflicts == []


# ---------- Test: clean data = empty results ----------

@pytest.mark.asyncio
async def test_clean_project_no_conflicts(client, db_session):
    """A project with no KG data and clean text returns no conflicts."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    ch1 = await _setup_chapter(client, bid, sort_order=0)
    await _setup_scene_with_text(client, ch1, "Once upon a time in a land far away.")

    results = await run_consistency_check(db_session, pid)
    assert results == []


# ---------- Test: API endpoint ----------

@pytest.mark.asyncio
async def test_api_endpoint_returns_list(client, db_session):
    """POST /api/qa/check returns a list (possibly empty)."""
    pid = await _setup_project(client)

    resp = await client.post("/api/qa/check", json={"project_id": pid})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_api_endpoint_conflict_format(client, db_session):
    """API response items match ConsistencyResult schema fields."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    ch1 = await _setup_chapter(client, bid, sort_order=0)
    repeated = "the quick brown fox " * 5
    await _setup_scene_with_text(client, ch1, repeated.strip())

    resp = await client.post(
        "/api/qa/check",
        json={"project_id": pid, "ngram_n": 4, "ngram_threshold": 3},
    )
    assert resp.status_code == 200
    results = resp.json()
    rep = [r for r in results if r["type"] == "repetition"]
    assert len(rep) >= 1

    required_fields = {
        "type", "severity", "confidence", "source",
        "message", "evidence", "evidence_locations", "suggest_fix",
    }
    for field in required_fields:
        assert field in rep[0], f"Missing field: {field}"


@pytest.mark.asyncio
async def test_api_endpoint_custom_ngram_params(client, db_session):
    """Configurable ngram_n and ngram_threshold forwarded correctly."""
    pid = await _setup_project(client)
    bid = await _setup_book(client, pid)
    ch1 = await _setup_chapter(client, bid, sort_order=0)
    repeated = "hello world foo bar " * 4
    await _setup_scene_with_text(client, ch1, repeated.strip())

    # Very high threshold: no repetition flagged
    resp = await client.post(
        "/api/qa/check",
        json={"project_id": pid, "ngram_n": 4, "ngram_threshold": 100},
    )
    assert resp.status_code == 200
    assert all(r["type"] != "repetition" for r in resp.json())


@pytest.mark.asyncio
async def test_api_possession_conflict_via_endpoint(client, db_session):
    """Possession conflict detected through the API endpoint."""
    pid = await _setup_project(client)

    char_a = _make_node(pid, "Character", "Eve", {})
    char_b = _make_node(pid, "Character", "Mallory", {})
    item = _make_node(pid, "Item", "Golden Key", {})
    db_session.add_all([char_a, char_b, item])
    await db_session.flush()

    edge_a = _make_edge(pid, char_a.id, item.id, "possesses")
    edge_b = _make_edge(pid, char_b.id, item.id, "possesses")
    db_session.add_all([edge_a, edge_b])
    await db_session.flush()

    resp = await client.post("/api/qa/check", json={"project_id": pid})
    assert resp.status_code == 200
    poss = [r for r in resp.json() if r["type"] == "possession"]
    assert len(poss) >= 1
    assert "Golden Key" in poss[0]["message"]
