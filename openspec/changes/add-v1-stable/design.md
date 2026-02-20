# v1 Stable Technical Design

## 1. Workflow Engine

### 1.1 JSON DAG Architecture

**Decision**: Self-built lightweight engine (~500 lines) using JSON DAG + Python decorator registration.

**Rationale** (DR-007):
- Airflow/Prefect overkill for local single-user deployment
- JSON DAG provides version control + UI rendering
- Decorator pattern enables type-safe handler registration

### 1.2 Workflow Definition

```json
{
  "workflow_id": "chapter_completion",
  "nodes": [
    {"id": "summarize", "handler": "generate_summary", "depends_on": []},
    {"id": "extract_kg", "handler": "extract_kg_proposals", "depends_on": ["summarize"]},
    {"id": "check_consistency", "handler": "run_consistency_checks", "depends_on": ["extract_kg"]},
    {"id": "suggest_next", "handler": "suggest_next_chapter", "depends_on": ["check_consistency"]}
  ]
}
```

### 1.3 Handler Registration

```python
from typing import Callable
from pydantic import BaseModel

workflow_handlers: dict[str, Callable] = {}

def workflow_handler(name: str):
    def decorator(func: Callable):
        workflow_handlers[name] = func
        return func
    return decorator

@workflow_handler("generate_summary")
async def generate_summary(ctx: WorkflowContext) -> dict:
    chapter_id = ctx.input["chapter_id"]
    summary = await auto_generate_summary(chapter_id)
    return {"summary_id": summary.id}

@workflow_handler("extract_kg_proposals")
async def extract_kg_proposals(ctx: WorkflowContext) -> dict:
    chapter_id = ctx.input["chapter_id"]
    proposals = await extract_kg(chapter_id)
    return {"proposal_count": len(proposals)}
```

### 1.4 Execution Engine

```python
class WorkflowEngine:
    async def execute(self, workflow_def: dict, input_data: dict):
        run = WorkflowRun(workflow_key=workflow_def["workflow_id"], input_json=input_data)
        await db.add(run)

        completed = set()

        while len(completed) < len(workflow_def["nodes"]):
            for node in workflow_def["nodes"]:
                if node["id"] in completed:
                    continue

                # Check dependencies
                if all(dep in completed for dep in node["depends_on"]):
                    node_run = WorkflowNodeRun(run_id=run.id, node_id=node["id"], status="running")
                    await db.add(node_run)

                    try:
                        handler = workflow_handlers[node["handler"]]
                        ctx = WorkflowContext(input=input_data, run_id=run.id)
                        output = await handler(ctx)

                        node_run.status = "completed"
                        node_run.output_json = output
                        completed.add(node["id"])
                    except Exception as e:
                        node_run.status = "failed"
                        node_run.error_msg = str(e)
                        raise

        run.status = "completed"
        await db.commit()
```

---

## 2. Version Control

### 2.1 Scene Versioning

```python
class SceneTextVersion(BaseModel):
    id: int
    scene_id: int
    version: int  # Auto-increment
    content_md: str
    char_count: int
    created_at: datetime
    created_by: Literal["user", "ai"]
    parent_version: int | None  # For branching

async def save_scene_version(scene_id: int, content: str, created_by: str) -> SceneTextVersion:
    latest = await db.query(SceneTextVersion).filter(
        SceneTextVersion.scene_id == scene_id
    ).order_by(SceneTextVersion.version.desc()).first()

    new_version = SceneTextVersion(
        scene_id=scene_id,
        version=(latest.version + 1) if latest else 1,
        content_md=content,
        char_count=len(content),
        created_by=created_by,
        parent_version=latest.version if latest else None
    )

    await db.add(new_version)
    return new_version
```

### 2.2 Named Checkpoints

```python
class Checkpoint(BaseModel):
    id: int
    project_id: int
    name: str  # "Before major revision", "Chapter 10 完成"
    description: str
    snapshot_json: dict  # {"scenes": {...}, "bible": {...}, "kg": {...}}
    created_at: datetime

async def create_checkpoint(project_id: int, name: str) -> Checkpoint:
    snapshot = {
        "scenes": await export_all_scenes(project_id),
        "bible": await export_bible(project_id),
        "kg": await graph_service.export_graph(project_id),
        "lore": await export_lorebook(project_id)
    }

    checkpoint = Checkpoint(
        project_id=project_id,
        name=name,
        description="",
        snapshot_json=snapshot
    )

    await db.add(checkpoint)
    return checkpoint

async def restore_checkpoint(checkpoint_id: int):
    checkpoint = await db.get(Checkpoint, checkpoint_id)

    # Restore scenes
    for scene_data in checkpoint.snapshot_json["scenes"]:
        await restore_scene(scene_data)

    # Restore Bible
    await restore_bible(checkpoint.snapshot_json["bible"])

    # Restore KG
    await graph_service.import_graph(checkpoint.snapshot_json["kg"])
```

---

## 3. Vector Search (sqlite-vec)

### 3.1 Integration

```python
import sqlite_vec

async def init_vector_search(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_paragraphs USING vec0(
            paragraph_id INTEGER PRIMARY KEY,
            embedding FLOAT[384]
        )
    """)

async def index_paragraph(paragraph_id: int, text: str):
    # Use local BGE-small-zh model
    embedding = await embed_text(text, model="BAAI/bge-small-zh-v1.5")

    await db.execute(
        "INSERT INTO vec_paragraphs (paragraph_id, embedding) VALUES (?, ?)",
        (paragraph_id, embedding)
    )

async def search_similar_paragraphs(query: str, limit: int = 5) -> list[int]:
    query_embedding = await embed_text(query)

    results = await db.execute("""
        SELECT paragraph_id, distance
        FROM vec_paragraphs
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT ?
    """, (query_embedding, limit))

    return [row[0] for row in results]
```

### 3.2 Context Pack Integration

```python
async def assemble_context_pack_v1(scene_id: int, total_budget: int) -> ContextPack:
    # ... existing layers ...

    # New: Vector search layer (5-8% of budget)
    vector_budget = int(total_budget * 0.06)

    current_scene = await get_scene(scene_id)
    similar_ids = await search_similar_paragraphs(current_scene.summary, limit=3)
    similar_paragraphs = await db.query(Paragraph).filter(Paragraph.id.in_(similar_ids)).all()

    vector_layer = "\n\n".join([p.text for p in similar_paragraphs])
    vector_tokens = count_tokens(vector_layer)

    if vector_tokens > vector_budget:
        vector_layer = truncate_to_budget(vector_layer, vector_budget)

    # Deduplicate with KG evidence by paragraph_idx
    vector_layer = deduplicate_with_kg(vector_layer, scene_id)

    return ContextPack(
        system_layer=system,
        longterm_layer=longterm,
        structured_layer=structured,
        vector_layer=vector_layer,  # New
        recent_layer=recent
    )
```

---

## 4. Streaming Gate (Strong Word Count Constraint)

### 4.1 Soft Limit (Warning)

```python
async def stream_with_soft_limit(scene_id: int, target_chars: int):
    soft_limit = int(target_chars * 1.1)  # +10%

    async def event_stream():
        accumulated = ""
        warned = False

        stream = await client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            stream=True
        )

        async for chunk in stream:
            text = chunk.choices[0].delta.content
            accumulated += text

            if len(accumulated) >= soft_limit and not warned:
                yield f"data: {{\"type\": \"warning\", \"message\": \"Approaching target length\"}}\n\n"
                warned = True

            yield f"data: {text}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### 4.2 Hard Limit (Sentence Boundary)

```python
async def stream_with_hard_limit(scene_id: int, target_chars: int):
    hard_limit = int(target_chars * 1.2)  # +20%

    async def event_stream():
        accumulated = ""

        stream = await client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            stream=True
        )

        async for chunk in stream:
            text = chunk.choices[0].delta.content
            accumulated += text

            # Check hard limit at sentence boundary
            if len(accumulated) >= hard_limit:
                # Find last Chinese sentence boundary (。！？)
                last_boundary = max(
                    accumulated.rfind("。"),
                    accumulated.rfind("！"),
                    accumulated.rfind("？")
                )

                if last_boundary > 0:
                    final_text = accumulated[:last_boundary + 1]
                    yield f"data: {final_text[len(accumulated) - len(text):]}\n\n"
                    yield f"data: {{\"type\": \"truncated\", \"reason\": \"hard_limit\"}}\n\n"
                    break

            yield f"data: {text}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## 5. LLM Consistency Check

### 5.1 Setting Contradiction Detection

```python
class SettingContradiction(BaseModel):
    field: str
    bible_value: str
    text_value: str
    evidence_location: str
    confidence: float

async def detect_setting_contradictions(chapter_id: int) -> list[SettingContradiction]:
    bible = await get_bible_fields(chapter_id)
    chapter_text = await get_chapter_text(chapter_id)

    contradictions = await client.chat.completions.create(
        model="gpt-4",
        response_model=list[SettingContradiction],
        messages=[{
            "role": "user",
            "content": f"""
            Bible settings:
            {json.dumps(bible, ensure_ascii=False)}

            Chapter text:
            {chapter_text}

            Find contradictions between Bible and text.
            """
        }]
    )

    return [c for c in contradictions if c.confidence >= 0.7]
```

### 5.2 POV Drift Detection

```python
class POVDrift(BaseModel):
    paragraph_idx: int
    expected_pov: str  # "第一人称", "第三人称"
    detected_pov: str
    evidence: str
    confidence: float

async def detect_pov_drift(chapter_id: int) -> list[POVDrift]:
    bible = await get_bible_fields(chapter_id)
    expected_pov = bible.get("POV", "第三人称")

    paragraphs = await get_chapter_paragraphs(chapter_id)

    drifts = []
    for idx, para in enumerate(paragraphs):
        result = await client.chat.completions.create(
            model="gpt-4",
            response_model=POVDrift,
            messages=[{
                "role": "user",
                "content": f"""
                Expected POV: {expected_pov}
                Paragraph: {para.text}

                Detect POV drift.
                """
            }]
        )

        if result.detected_pov != expected_pov and result.confidence >= 0.8:
            drifts.append(result)

    return drifts
```

---

## 6. Prompt Workshop

### 6.1 Template Versioning

```python
class PromptTemplate(BaseModel):
    id: int
    project_id: int
    group: str  # "scene_generation", "summary", "kg_extraction"
    key: str  # "scene_card", "scene_draft"
    template_md: str
    version: int
    enabled: bool
    created_at: datetime

async def get_active_prompt(project_id: int, group: str, key: str) -> str:
    template = await db.query(PromptTemplate).filter(
        PromptTemplate.project_id == project_id,
        PromptTemplate.group == group,
        PromptTemplate.key == key,
        PromptTemplate.enabled == True
    ).order_by(PromptTemplate.version.desc()).first()

    return template.template_md if template else get_default_prompt(group, key)

async def create_prompt_version(
    project_id: int,
    group: str,
    key: str,
    template: str
) -> PromptTemplate:
    latest = await db.query(PromptTemplate).filter(
        PromptTemplate.project_id == project_id,
        PromptTemplate.group == group,
        PromptTemplate.key == key
    ).order_by(PromptTemplate.version.desc()).first()

    new_version = PromptTemplate(
        project_id=project_id,
        group=group,
        key=key,
        template_md=template,
        version=(latest.version + 1) if latest else 1,
        enabled=True
    )

    # Disable previous version
    if latest:
        latest.enabled = False

    await db.add(new_version)
    return new_version
```

---

## 7. Migration from MVP-β

**New dependencies**:
```toml
[tool.uv.dependencies]
sqlite-vec = "^0.1.0"
sentence-transformers = "^2.2.0"  # For BGE-small-zh
```

**Database migrations**:
```bash
alembic revision -m "Add workflow and version control tables"
alembic upgrade head
```

**New tables**:
- `workflow_runs`
- `workflow_node_runs`
- `checkpoints`
- `vec_paragraphs` (virtual table)
- `prompts`
