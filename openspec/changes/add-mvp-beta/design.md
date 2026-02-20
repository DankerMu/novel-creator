# MVP-β Technical Design

## 1. Architecture Additions

### 1.1 New Services

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Lorebook   │  │     Graph    │  │       QA         │  │
│  │   Service    │  │   Service    │  │    Service       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ SQLite + Neo4j│
                    │   (optional)  │
                    └───────────────┘
```

### 1.2 Key Decisions

**Decision 1**: SQLite dual-table KG for Lite mode, Neo4j for Full mode, unified GraphService interface.

**Rationale** (DR-001):
- SQLite `kg_nodes` + `kg_edges` tables support <2000 nodes with acceptable performance
- GraphService abstraction allows runtime switching (SQLiteGraphAdapter vs Neo4jAdapter)
- Frontend uses D3.js/Cytoscape.js for visualization (no Neo4j Browser dependency)

**Decision 2**: Confidence-based auto-approval for KG proposals.

**Rationale** (DR-009):
- High confidence (≥0.9): auto-approve, skip review queue
- Medium (0.6-0.9): auto-pending, batch review UI
- Low (<0.6): reject or flag for manual review
- Reduces review burden by 70%+

**Decision 3**: Keyword + alias Lorebook triggering (defer semantic matching to v2).

**Rationale** (DR-005):
- Keyword OR matching + aliases covers 90%+ use cases
- Scan depth: current scene + previous scene (SillyTavern pattern)
- Priority-based truncation when budget exceeded

---

## 2. Lorebook Implementation

### 2.1 Entry Schema

```python
class LoreEntry(BaseModel):
    id: int
    project_id: int
    type: Literal["Character", "Location", "Item", "Concept", "Rule", "Organization", "Event"]
    title: str
    aliases: list[str]  # ["李明", "小李", "李公子"]
    content_md: str  # Injected into prompt
    secrets_md: str  # Author-only notes
    triggers: dict  # {"keywords": [...], "and_keywords": [...]}
    priority: int  # 1-10, higher = more important
    locked: bool  # If true, always inject regardless of triggers
```

### 2.2 Injection Algorithm

```python
async def inject_lorebook(scene_id: int, budget_tokens: int) -> str:
    # 1. Scan current + previous scene text
    scan_text = await get_scan_window(scene_id, depth=2)

    # 2. Match entries by keywords + aliases
    triggered = []
    for entry in await db.query(LoreEntry).all():
        if entry.locked or matches_triggers(entry, scan_text):
            triggered.append(entry)

    # 3. Sort by priority (high → low)
    triggered.sort(key=lambda e: e.priority, reverse=True)

    # 4. Truncate to budget
    result = []
    used_tokens = 0
    for entry in triggered:
        tokens = count_tokens(entry.content_md)
        if used_tokens + tokens <= budget_tokens:
            result.append(entry.content_md)
            used_tokens += tokens
        else:
            break  # Budget exhausted

    return "\n\n".join(result)
```

---

## 3. Knowledge Graph Implementation

### 3.1 Extraction with Confidence

```python
class KGProposal(BaseModel):
    entity_type: Literal["Character", "Location", "Organization", "Item", "Event"]
    entity_name: str
    relation_type: str  # "APPEARS_IN", "OWNS", "LOCATED_IN"
    target_entity: str
    confidence: float  # 0.0-1.0
    evidence_quote: str
    evidence_chapter_id: int
    evidence_scene_id: str
    evidence_paragraph_idx: int

async def extract_kg_proposals(chapter_id: int) -> list[KGProposal]:
    chapter_text = await get_chapter_text(chapter_id)

    proposals = await client.chat.completions.create(
        model="gpt-4",
        response_model=list[KGProposal],
        messages=[{
            "role": "user",
            "content": f"Extract entities and relations:\n\n{chapter_text}"
        }]
    )

    # Auto-approve/reject based on confidence
    for p in proposals:
        if p.confidence >= 0.9:
            p.status = "auto_approved"
            await graph_service.add_fact(p)
        elif p.confidence >= 0.6:
            p.status = "auto_pending"
        else:
            p.status = "rejected"

    await db.add_all(proposals)
    return proposals
```

### 3.2 GraphService Abstraction

```python
class GraphService(ABC):
    @abstractmethod
    async def add_node(self, node_type: str, properties: dict): ...

    @abstractmethod
    async def add_edge(self, from_id: str, to_id: str, rel_type: str): ...

    @abstractmethod
    async def get_neighbors(self, node_id: str, depth: int = 1): ...

class SQLiteGraphAdapter(GraphService):
    async def add_node(self, node_type: str, properties: dict):
        await db.execute(
            "INSERT INTO kg_nodes (type, properties_json) VALUES (?, ?)",
            (node_type, json.dumps(properties))
        )

class Neo4jAdapter(GraphService):
    async def add_node(self, node_type: str, properties: dict):
        await self.driver.execute_query(
            f"CREATE (n:{node_type} $props)",
            props=properties
        )
```

---

## 4. Context Pack Enhancement

### 4.1 4-Layer Budget System

```python
class ContextPack(BaseModel):
    system_layer: str  # Bible locked fields (P0)
    longterm_layer: str  # Chapter summaries (P1)
    structured_layer: str  # KG + Lorebook (P2)
    recent_layer: str  # Last N paragraphs (P3)

async def assemble_context_pack(
    project_id: int,
    scene_id: int,
    total_budget: int = 32000
) -> ContextPack:
    budgets = {
        "system": {"reserved": 1024, "max": 2048},
        "longterm": {"reserved": 2048, "max": 4096},
        "structured": {"reserved": 0, "max": 6144},
        "recent": {"reserved": 0, "max": total_budget}
    }

    # Layer 1: System (Bible locked fields)
    system = await get_locked_bible_fields(project_id)
    system_tokens = count_tokens(system)

    # Layer 2: Long-term (summaries)
    longterm = await get_chapter_summaries(project_id, limit=3)
    longterm_tokens = count_tokens(longterm)

    # Layer 3: Structured (KG + Lorebook)
    kg_budget = budgets["structured"]["max"] // 2
    lore_budget = budgets["structured"]["max"] // 2

    kg_facts = await graph_service.get_relevant_facts(scene_id, kg_budget)
    lore_entries = await inject_lorebook(scene_id, lore_budget)
    structured = kg_facts + "\n\n" + lore_entries
    structured_tokens = count_tokens(structured)

    # Layer 4: Recent (overflow handling)
    used = system_tokens + longterm_tokens + structured_tokens
    recent_budget = total_budget - used
    recent = await get_recent_paragraphs(scene_id, recent_budget)

    return ContextPack(
        system_layer=system,
        longterm_layer=longterm,
        structured_layer=structured,
        recent_layer=recent
    )
```

---

## 5. Consistency Check (Rule Engine)

### 5.1 4 Check Types

```python
class ConsistencyCheck(BaseModel):
    check_type: Literal["timeline", "character_state", "setting", "repetition"]
    severity: Literal["error", "warning", "info"]
    location: str  # "chapter_3:scene_2:paragraph_5"
    message: str
    evidence: list[str]

async def run_consistency_checks(chapter_id: int) -> list[ConsistencyCheck]:
    checks = []

    # 1. Timeline conflicts
    events = await get_chapter_events(chapter_id)
    for e1, e2 in combinations(events, 2):
        if e1.timestamp > e2.timestamp and e1.index < e2.index:
            checks.append(ConsistencyCheck(
                check_type="timeline",
                severity="error",
                location=f"chapter_{chapter_id}",
                message=f"Event '{e1.name}' happens after '{e2.name}' but appears earlier",
                evidence=[e1.quote, e2.quote]
            ))

    # 2. Character state conflicts
    char_states = await graph_service.get_character_states(chapter_id)
    for char, states in char_states.items():
        if "alive" in states and "dead" in states:
            checks.append(ConsistencyCheck(
                check_type="character_state",
                severity="error",
                location=f"chapter_{chapter_id}",
                message=f"Character '{char}' is both alive and dead",
                evidence=states
            ))

    # 3. Setting conflicts (Bible vs text)
    bible = await get_bible_fields(chapter_id)
    text_settings = await extract_settings(chapter_id)
    for key, bible_val in bible.items():
        if key in text_settings and text_settings[key] != bible_val:
            checks.append(ConsistencyCheck(
                check_type="setting",
                severity="warning",
                location=f"chapter_{chapter_id}",
                message=f"Setting '{key}' conflicts with Bible",
                evidence=[bible_val, text_settings[key]]
            ))

    # 4. N-gram repetition
    paragraphs = await get_chapter_paragraphs(chapter_id)
    ngrams = extract_ngrams(paragraphs, n=5)
    for ngram, count in ngrams.items():
        if count >= 3:
            checks.append(ConsistencyCheck(
                check_type="repetition",
                severity="info",
                location=f"chapter_{chapter_id}",
                message=f"Phrase '{ngram}' repeated {count} times",
                evidence=[]
            ))

    return checks
```

---

## 6. Word Count Control (Medium Constraint)

```python
async def enforce_scene_budget(
    scene_id: int,
    target_chars: int,
    tolerance: float = 0.1
) -> str:
    draft = await generate_scene_draft(scene_id)
    actual_chars = len(draft)

    lower = target_chars * (1 - tolerance)
    upper = target_chars * (1 + tolerance)

    if lower <= actual_chars <= upper:
        return draft  # Within tolerance

    elif actual_chars < lower:
        # Expand
        expand_prompt = f"Expand this scene to ~{target_chars} chars:\n\n{draft}"
        return await call_llm(expand_prompt)

    else:
        # Compress
        compress_prompt = f"Compress this scene to ~{target_chars} chars:\n\n{draft}"
        return await call_llm(compress_prompt)
```

---

## 7. Migration from MVP-α

**Database migrations**:
```bash
alembic revision --autogenerate -m "Add Lorebook and KG tables"
alembic upgrade head
```

**New tables**:
- `lore_entries` (already defined in MVP-α schema, now populated)
- `kg_proposals` (already defined, now used)
- `kg_evidence` (already defined, now used)
- `kg_nodes` (Lite mode only)
- `kg_edges` (Lite mode only)

**Frontend changes**:
- Enable Lorebook panel (right sidebar tab)
- Enable KG batch review UI (modal)
- Add consistency check results panel
