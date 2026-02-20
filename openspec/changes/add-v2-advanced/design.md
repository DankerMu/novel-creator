# v2 Advanced Technical Design

## 1. Timeline Visualization

### 1.1 Data Model

```python
class TimelineEvent(BaseModel):
    id: int
    project_id: int
    event_type: Literal["scene", "plot_point", "character_intro", "location_change"]
    title: str
    description: str
    in_story_timestamp: datetime  # In-universe time
    chapter_id: int
    scene_id: int
    characters: list[str]
    locations: list[str]
    plot_threads: list[int]
    tags: list[str]

async def extract_timeline_events(chapter_id: int) -> list[TimelineEvent]:
    chapter_text = await get_chapter_text(chapter_id)

    events = await client.chat.completions.create(
        model="gpt-4",
        response_model=list[TimelineEvent],
        messages=[{
            "role": "user",
            "content": f"Extract timeline events with in-story timestamps:\n\n{chapter_text}"
        }]
    )

    await db.add_all(events)
    return events
```

### 1.2 Frontend Visualization (D3.js)

```typescript
interface TimelineNode {
  id: string
  title: string
  timestamp: Date
  characters: string[]
  locations: string[]
  plotThreads: number[]
}

const renderTimeline = (events: TimelineNode[], filters: TimelineFilters) => {
  const svg = d3.select("#timeline-svg")
  const width = 1200
  const height = 600

  // Filter by character/location/thread
  const filtered = events.filter(e =>
    (!filters.character || e.characters.includes(filters.character)) &&
    (!filters.location || e.locations.includes(filters.location)) &&
    (!filters.thread || e.plotThreads.includes(filters.thread))
  )

  // X-axis: in-story time
  const xScale = d3.scaleTime()
    .domain([d3.min(filtered, d => d.timestamp), d3.max(filtered, d => d.timestamp)])
    .range([50, width - 50])

  // Y-axis: chapter order
  const yScale = d3.scaleLinear()
    .domain([0, filtered.length])
    .range([50, height - 50])

  // Render nodes
  svg.selectAll("circle")
    .data(filtered)
    .enter()
    .append("circle")
    .attr("cx", d => xScale(d.timestamp))
    .attr("cy", (d, i) => yScale(i))
    .attr("r", 8)
    .attr("fill", d => getColorByType(d))
    .on("click", d => showEventDetail(d))
}
```

---

## 2. Style Analysis

### 2.1 Style Fingerprint Extraction

```python
class StyleFingerprint(BaseModel):
    project_id: int
    avg_sentence_length: float
    avg_paragraph_length: float
    lexical_diversity: float  # unique_words / total_words
    dialogue_ratio: float  # dialogue_chars / total_chars
    pov_consistency: float  # 0-1
    common_phrases: list[tuple[str, int]]  # (phrase, count)
    tone_keywords: dict[str, int]  # {"dark": 15, "hopeful": 8}

async def extract_style_fingerprint(project_id: int) -> StyleFingerprint:
    all_text = await get_all_project_text(project_id)

    sentences = split_sentences(all_text)
    paragraphs = split_paragraphs(all_text)
    words = tokenize(all_text)

    dialogue_chars = count_dialogue_chars(all_text)

    return StyleFingerprint(
        project_id=project_id,
        avg_sentence_length=sum(len(s) for s in sentences) / len(sentences),
        avg_paragraph_length=sum(len(p) for p in paragraphs) / len(paragraphs),
        lexical_diversity=len(set(words)) / len(words),
        dialogue_ratio=dialogue_chars / len(all_text),
        pov_consistency=detect_pov_consistency(all_text),
        common_phrases=extract_ngrams(all_text, n=3, top_k=20),
        tone_keywords=extract_tone_keywords(all_text)
    )
```

### 2.2 Deviation Detection

```python
class StyleDeviation(BaseModel):
    chapter_id: int
    metric: str  # "sentence_length", "lexical_diversity", etc.
    baseline_value: float
    actual_value: float
    deviation_percent: float
    severity: Literal["minor", "moderate", "major"]

async def detect_style_deviations(chapter_id: int) -> list[StyleDeviation]:
    project_id = await get_project_id(chapter_id)
    baseline = await get_style_fingerprint(project_id)
    chapter_text = await get_chapter_text(chapter_id)

    chapter_fingerprint = extract_style_fingerprint_from_text(chapter_text)

    deviations = []

    # Check sentence length
    if abs(chapter_fingerprint.avg_sentence_length - baseline.avg_sentence_length) / baseline.avg_sentence_length > 0.3:
        deviations.append(StyleDeviation(
            chapter_id=chapter_id,
            metric="sentence_length",
            baseline_value=baseline.avg_sentence_length,
            actual_value=chapter_fingerprint.avg_sentence_length,
            deviation_percent=abs(chapter_fingerprint.avg_sentence_length - baseline.avg_sentence_length) / baseline.avg_sentence_length * 100,
            severity="moderate" if deviation_percent < 50 else "major"
        ))

    # Check lexical diversity
    # ... similar checks for other metrics

    return deviations
```

---

## 3. Branch Writing

### 3.1 Branch Creation

```python
class SceneBranch(BaseModel):
    id: int
    scene_id: int
    branch_name: str  # "尝试A：主角拒绝", "尝试B：主角接受"
    parent_version: int  # Base version to branch from
    content_md: str
    char_count: int
    created_at: datetime
    merged: bool

async def create_scene_branch(
    scene_id: int,
    branch_name: str,
    parent_version: int
) -> SceneBranch:
    parent = await db.get(SceneTextVersion, parent_version)

    branch = SceneBranch(
        scene_id=scene_id,
        branch_name=branch_name,
        parent_version=parent_version,
        content_md=parent.content_md,  # Start with parent content
        char_count=parent.char_count,
        merged=False
    )

    await db.add(branch)
    return branch
```

### 3.2 Branch Merge

```python
async def merge_scene_branch(branch_id: int) -> SceneTextVersion:
    branch = await db.get(SceneBranch, branch_id)

    # Create new version from branch content
    new_version = SceneTextVersion(
        scene_id=branch.scene_id,
        version=await get_next_version(branch.scene_id),
        content_md=branch.content_md,
        char_count=branch.char_count,
        created_by="user",
        parent_version=branch.parent_version
    )

    branch.merged = True

    await db.add(new_version)
    return new_version
```

### 3.3 Frontend Branch UI

```typescript
interface BranchNode {
  id: number
  name: string
  parentVersion: number
  content: string
  merged: boolean
}

const BranchVisualization = ({ branches }: { branches: BranchNode[] }) => {
  return (
    <div className="branch-tree">
      {branches.map(branch => (
        <div key={branch.id} className="branch-node">
          <div className="branch-label">{branch.name}</div>
          <button onClick={() => viewBranch(branch.id)}>查看</button>
          <button onClick={() => editBranch(branch.id)}>编辑</button>
          {!branch.merged && (
            <button onClick={() => mergeBranch(branch.id)}>合并</button>
          )}
        </div>
      ))}
    </div>
  )
}
```

---

## 4. Custom Workflow (Python DSL)

### 4.1 RestrictedPython Sandbox

```python
from RestrictedPython import compile_restricted, safe_globals

class CustomWorkflowEngine:
    def __init__(self):
        self.safe_builtins = {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "range": range,
            "enumerate": enumerate,
        }

    async def execute_custom_workflow(self, code: str, context: dict) -> dict:
        # Compile with RestrictedPython
        byte_code = compile_restricted(code, '<string>', 'exec')

        # Prepare safe globals
        safe_env = {
            **safe_globals,
            **self.safe_builtins,
            "context": context,
            "call_llm": self.safe_call_llm,
            "get_scene": self.safe_get_scene,
            "save_scene": self.safe_save_scene,
        }

        # Execute
        exec(byte_code, safe_env)

        return safe_env.get("result", {})

    async def safe_call_llm(self, prompt: str, model: str = "gpt-4") -> str:
        # Rate-limited LLM call
        return await call_llm(prompt, model)

    async def safe_get_scene(self, scene_id: int) -> dict:
        scene = await db.get(Scene, scene_id)
        return {"id": scene.id, "content": scene.latest_version.content_md}

    async def safe_save_scene(self, scene_id: int, content: str):
        await save_scene_version(scene_id, content, created_by="custom_workflow")
```

### 4.2 User Workflow Example

```python
# User-defined workflow: "双视角生成"
# 为同一场景生成主角和反派两个视角的描写

scene_id = context["scene_id"]
scene = get_scene(scene_id)

# 生成主角视角
protagonist_prompt = f"从主角视角重写这个场景：\n\n{scene['content']}"
protagonist_version = call_llm(protagonist_prompt)

# 生成反派视角
villain_prompt = f"从反派视角重写这个场景：\n\n{scene['content']}"
villain_version = call_llm(villain_prompt)

# 保存为分支
save_scene(scene_id + "_protagonist", protagonist_version)
save_scene(scene_id + "_villain", villain_version)

result = {
    "protagonist_version": protagonist_version,
    "villain_version": villain_version
}
```

---

## 5. Lore Agent (Autonomous Maintenance)

### 5.1 Agent Loop

```python
class LoreAgent:
    async def run(self, project_id: int):
        while True:
            # 1. Scan recent chapters for new entities
            new_entities = await self.scan_new_entities(project_id)

            # 2. Check if entities already in Lorebook
            missing = await self.filter_missing_entities(new_entities)

            # 3. Generate Lore entries for missing entities
            for entity in missing:
                entry = await self.generate_lore_entry(entity)
                await db.add(entry)

            # 4. Update existing entries if contradictions found
            contradictions = await self.detect_lore_contradictions(project_id)
            for c in contradictions:
                await self.resolve_contradiction(c)

            # Sleep until next chapter completion
            await asyncio.sleep(3600)

    async def scan_new_entities(self, project_id: int) -> list[str]:
        recent_chapters = await get_recent_chapters(project_id, limit=1)
        text = await get_chapter_text(recent_chapters[0].id)

        entities = await client.chat.completions.create(
            model="gpt-4",
            response_model=list[str],
            messages=[{
                "role": "user",
                "content": f"Extract all named entities (characters, locations, items):\n\n{text}"
            }]
        )

        return entities

    async def generate_lore_entry(self, entity_name: str) -> LoreEntry:
        # Query KG for entity info
        kg_info = await graph_service.get_entity_info(entity_name)

        # Generate Lore content
        content = await client.chat.completions.create(
            model="gpt-4",
            response_model=str,
            messages=[{
                "role": "user",
                "content": f"Generate Lorebook entry for '{entity_name}':\n\n{kg_info}"
            }]
        )

        return LoreEntry(
            project_id=kg_info["project_id"],
            type="Character",  # Infer from KG
            title=entity_name,
            aliases=[],
            content_md=content,
            triggers={"keywords": [entity_name]},
            priority=5,
            locked=False
        )

    async def detect_lore_contradictions(self, project_id: int) -> list[dict]:
        lore_entries = await db.query(LoreEntry).filter(LoreEntry.project_id == project_id).all()
        kg_facts = await graph_service.get_all_facts(project_id)

        contradictions = []

        for entry in lore_entries:
            for fact in kg_facts:
                if fact.entity_name == entry.title:
                    # Check if Lore content contradicts KG fact
                    is_contradiction = await check_contradiction(entry.content_md, fact.description)
                    if is_contradiction:
                        contradictions.append({
                            "lore_entry_id": entry.id,
                            "kg_fact_id": fact.id,
                            "lore_content": entry.content_md,
                            "kg_fact": fact.description
                        })

        return contradictions
```

---

## 6. Qdrant Migration (Optional)

### 6.1 Upgrade from sqlite-vec

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantVectorService:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)

    async def init_collection(self, collection_name: str = "paragraphs"):
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

    async def index_paragraph(self, paragraph_id: int, text: str):
        embedding = await embed_text(text, model="BAAI/bge-small-zh-v1.5")

        self.client.upsert(
            collection_name="paragraphs",
            points=[
                PointStruct(
                    id=paragraph_id,
                    vector=embedding,
                    payload={"text": text}
                )
            ]
        )

    async def search_similar(self, query: str, limit: int = 5) -> list[dict]:
        query_embedding = await embed_text(query)

        results = self.client.search(
            collection_name="paragraphs",
            query_vector=query_embedding,
            limit=limit
        )

        return [{"id": r.id, "text": r.payload["text"], "score": r.score} for r in results]
```

---

## 7. Migration from v1

**New dependencies**:
```toml
[tool.uv.dependencies]
RestrictedPython = "^6.0"
qdrant-client = "^1.7.0"  # Optional
```

**Database migrations**:
```bash
alembic revision -m "Add timeline and branch tables"
alembic upgrade head
```

**New tables**:
- `timeline_events`
- `scene_branches`
- `style_fingerprints`
- `custom_workflows`

**Docker Compose (optional Qdrant)**:
```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_data:/qdrant/storage
```
