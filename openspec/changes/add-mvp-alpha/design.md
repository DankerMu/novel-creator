# MVP-α Technical Design

## 1. Architecture Overview

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (localhost:3100)                │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │  Project Tree  │  │ Scene Editor │  │  Bible Panel    │ │
│  │  (Left Panel)  │  │  (Center)    │  │  (Right Panel)  │ │
│  └────────────────┘  └──────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │ HTTP/SSE
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Project    │  │      AI      │  │     Memory       │  │
│  │   Service    │  │ Orchestrator │  │    Service       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    SQLite     │
                    └───────────────┘

### 1.2 Technology Stack

**Backend (Python)**
- FastAPI 0.115+ (async ASGI, SSE support)
- Instructor 1.7+ (structured LLM outputs with Pydantic)
- Pydantic 2.x (data validation)
- SQLAlchemy 2.x + Alembic (ORM + migrations)
- LiteLLM (unified LLM provider interface)
- asyncio.Queue (event bus for single-process coordination)

**Frontend (TypeScript)**
- Next.js 15+ (React 19, App Router)
- TanStack Query (server state management)
- Zustand (client state)
- Tailwind CSS + shadcn/ui (UI components)
- EventSource API (SSE client)

**Storage**
- SQLite 3.45+ (primary database)
- No Neo4j/Qdrant in MVP-α (deferred to MVP-β/v1)

**Deployment**
- Docker Compose (api + web services)
- uv (Python package manager)
- pnpm (Node package manager)

---

## 2. Key Architectural Decisions

### 2.1 Structured Output Strategy

**Decision**: Use Instructor library for all non-streaming structured outputs.

**Rationale** (from DR-011):
- Instructor wraps OpenAI/Anthropic SDKs and enforces Pydantic schema validation
- Auto-retry with error feedback (up to 3 attempts)
- Type-safe Python models eliminate manual JSON parsing
- Compatible with FastAPI dependency injection

**Implementation Pattern**:
```python
from instructor import from_openai
from pydantic import BaseModel
from openai import AsyncOpenAI

client = from_openai(AsyncOpenAI())

class SceneCard(BaseModel):
    title: str
    location: str
    characters: list[str]
    conflict: str
    target_chars: int

async def generate_scene_card(context: str) -> SceneCard:
    return await client.chat.completions.create(
        model="gpt-4",
        response_model=SceneCard,
        messages=[{"role": "user", "content": context}],
        max_retries=3
    )
```

### 2.2 Streaming Architecture

**Decision**: Use FastAPI SSE for prose generation, bypass Instructor for streaming endpoints.

**Rationale** (from DR-011):
- Instructor does not support streaming (blocks until full response)
- SSE provides native browser support (EventSource API)
- Validation happens post-stream (char_count, presence checks)

**Implementation Pattern**:
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

router = APIRouter()
client = AsyncOpenAI()

@router.post("/generate/scene-draft")
async def stream_scene_draft(request: SceneDraftRequest):
    async def event_stream():
        stream = await client.chat.completions.create(
            model="gpt-4",
            messages=request.messages,
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield f"data: {chunk.choices[0].delta.content}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### 2.3 Context Pack Assembly

**Decision**: Implement 4-layer token budget system with overflow degradation.

**Rationale** (from DR-002):
- SillyTavern/NovelAI proven pattern: reserved + max_budget per layer
- Unused budget flows to short-term context (Recent Text)
- Prevents context starvation in long novels

**Budget Allocation (32K context example)**:

| Layer | Reserved | Max Budget | Priority |
|-------|----------|------------|----------|
| System (Bible locked fields) | 1024 | 2048 | P0 (never truncate) |
| Long-term (chapter summaries) | 2048 | 4096 | P1 (compress if needed) |
| Structured (KG + Lore) | 0 | 6144 | P2 (truncate low-priority entries) |
| Recent Text | remaining | remaining | P3 (last resort truncation) |

**Overflow Strategy**:
1. Truncate low-priority Lore entries (priority < 5)
2. Compress chapter summaries (keep only key events)
3. Reduce Recent Text window (minimum 2 paragraphs)

### 2.4 Event-Driven Workflow

**Decision**: Use asyncio.Queue for event bus, decorator-based handler registration.

**Rationale**:
- Single-process deployment (no Redis needed)
- Type-safe event payloads with Pydantic
- Decouples services (Project → Memory → AI)

**Implementation Pattern**:
```python
from asyncio import Queue
from typing import Callable
from pydantic import BaseModel

class ChapterMarkDoneEvent(BaseModel):
    chapter_id: int
    project_id: int

event_bus = Queue()
handlers: dict[type, list[Callable]] = {}

def on_event(event_type: type):
    def decorator(func: Callable):
        handlers.setdefault(event_type, []).append(func)
        return func
    return decorator

@on_event(ChapterMarkDoneEvent)
async def generate_chapter_summary(event: ChapterMarkDoneEvent):
    # Auto-trigger summary generation
    pass
```

### 2.5 Database Schema Design

**Decision**: SQLite-first with explicit version tracking for all text content.

**Key Tables**:
- `scene_text_versions`: Immutable version history (version, content_md, char_count, created_at)
- `bible_fields`: Key-value with locked flag (locked=true → inject as hard constraint)
- `chapter_summaries`: Auto-generated on chapter_mark_done (summary_md, keywords_json, entities_json)

**Rationale**:
- Version history enables undo/redo without complex diffing
- Locked Bible fields provide explicit user control over AI constraints
- JSON columns (keywords_json, entities_json) defer schema rigidity to v1

---

## 3. Critical Implementation Patterns

### 3.1 LLM Provider Abstraction

**Pattern**: Unified interface via LiteLLM for OpenAI-compatible endpoints.

```python
from litellm import acompletion

async def call_llm(messages: list[dict], model: str = "gpt-4") -> str:
    response = await acompletion(
        model=model,
        messages=messages,
        api_base=settings.LLM_API_BASE,  # User-configurable
        api_key=settings.LLM_API_KEY
    )
    return response.choices[0].message.content
```

**Benefits**:
- Swap providers without code changes (OpenAI → Anthropic → local Ollama)
- Consistent error handling across providers
- Cost tracking via LiteLLM callbacks

### 3.2 Frontend Streaming Display

**Pattern**: EventSource API with progressive text accumulation.

```typescript
const streamSceneDraft = async (sceneId: string) => {
  const eventSource = new EventSource(`/api/generate/scene-draft?scene_id=${sceneId}`)

  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      eventSource.close()
      return
    }
    setEditorContent(prev => prev + event.data)
  }

  eventSource.onerror = () => {
    eventSource.close()
    toast.error('Generation failed')
  }
}
```

### 3.3 Bible Field Injection

**Pattern**: Locked fields automatically included in system prompt layer.

```python
async def assemble_context_pack(project_id: int, scene_id: int) -> str:
    # Layer 1: System constraints (locked Bible fields)
    bible_fields = await db.query(BibleField).filter(
        BibleField.project_id == project_id,
        BibleField.locked == True
    ).all()

    system_prompt = "# Story Constraints\n"
    for field in bible_fields:
        system_prompt += f"## {field.key}\n{field.value_md}\n\n"

    # Layer 2: Long-term memory (chapter summaries)
    summaries = await get_recent_summaries(project_id, limit=3)

    # Layer 3: Recent text (last N paragraphs)
    recent_text = await get_scene_context(scene_id, paragraph_count=5)

    return system_prompt + summaries + recent_text
```

### 3.4 Chapter Summary Auto-Generation

**Pattern**: Event-triggered background task with structured extraction.

```python
@on_event(ChapterMarkDoneEvent)
async def auto_generate_summary(event: ChapterMarkDoneEvent):
    chapter = await db.get(Chapter, event.chapter_id)
    scenes = await db.query(Scene).filter(Scene.chapter_id == chapter.id).all()

    full_text = "\n\n".join([s.latest_version.content_md for s in scenes])

    summary = await client.chat.completions.create(
        model="gpt-4",
        response_model=ChapterSummary,
        messages=[{
            "role": "user",
            "content": f"Summarize this chapter:\n\n{full_text}"
        }]
    )

    await db.add(ChapterSummaryRecord(
        chapter_id=chapter.id,
        summary_md=summary.narrative,
        keywords_json=summary.keywords,
        entities_json=summary.entities
    ))
```

---

## 4. Data Flow Diagrams

### 4.1 Scene Generation Flow

```
User clicks "Generate Scene"
    ↓
Frontend: POST /api/generate/scene-card
    ↓
Backend: Assemble Context Pack
    ├─ Query locked Bible fields (SQLite)
    ├─ Query chapter summaries (SQLite)
    └─ Query recent scene text (SQLite)
    ↓
Backend: Call LLM via Instructor
    ├─ Validate SceneCard schema (Pydantic)
    └─ Auto-retry on validation failure (max 3x)
    ↓
Backend: Return SceneCard JSON
    ↓
Frontend: Display scene card in UI
    ↓
User clicks "Generate Draft"
    ↓
Frontend: EventSource /api/generate/scene-draft
    ↓
Backend: Stream prose via SSE
    ├─ Inject SceneCard + Context Pack
    └─ Yield text chunks as they arrive
    ↓
Frontend: Append chunks to editor in real-time
    ↓
Backend: Send [DONE] event with char_count
    ↓
Frontend: Close EventSource, enable editing
```

### 4.2 Chapter Completion Flow

```
User clicks "Mark Chapter Done"
    ↓
Frontend: POST /api/chapters/{id}/mark-done
    ↓
Backend: Update chapter.status = "done"
    ↓
Backend: Emit ChapterMarkDoneEvent to event bus
    ↓
Event Handler: auto_generate_summary()
    ├─ Fetch all scenes in chapter
    ├─ Concatenate scene text
    ├─ Call LLM with SummaryExtraction model
    └─ Save to chapter_summaries table
    ↓
Frontend: Poll /api/chapters/{id}/summary
    ↓
Frontend: Display summary in right panel
```

---

## 5. Testing Strategy

### 5.1 Unit Tests (pytest)

**Coverage targets**:
- Context Pack assembly logic (budget allocation, overflow)
- Event bus handler registration and dispatch
- Pydantic model validation (SceneCard, ChapterSummary)
- SQLite CRUD operations (projects, scenes, bible_fields)

**Key test cases**:
```python
def test_context_pack_budget_overflow():
    # Given: Bible fields + summaries exceed 6KB
    # When: assemble_context_pack() is called
    # Then: Low-priority content is truncated, Recent Text preserved

def test_scene_card_validation_retry():
    # Given: LLM returns invalid JSON (missing required field)
    # When: generate_scene_card() is called
    # Then: Instructor retries with error feedback, succeeds on 2nd attempt
```

### 5.2 Integration Tests

**Scope**:
- End-to-end scene generation (Context Pack → LLM → SSE stream)
- Chapter mark done → summary auto-generation
- Bible field lock → injection in next generation

**Mock strategy**:
- Mock LLM calls with deterministic responses (avoid API costs)
- Use in-memory SQLite for test isolation

### 5.3 Manual Testing Checklist

- [ ] Create project → book → chapter → scene (full CRUD)
- [ ] Edit Bible field, toggle locked, verify injection in generation
- [ ] Generate scene card, verify all required fields present
- [ ] Stream scene draft, verify progressive display in editor
- [ ] Mark chapter done, verify summary appears in right panel
- [ ] Export book as Markdown, verify heading hierarchy
- [ ] Export chapter as TXT, verify scene breaks

---

## 6. Deployment Architecture

### 6.1 Docker Compose Setup

```yaml
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:////data/novel.db
      - LLM_API_BASE=${LLM_API_BASE}
      - LLM_API_KEY=${LLM_API_KEY}
    volumes:
      - ./data:/data

  web:
    build: ./frontend
    ports:
      - "3100:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api
```

### 6.2 Local Development

**Backend**:
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend
pnpm install
pnpm dev  # Runs on localhost:3000
```

---

## 7. Migration Path to MVP-β

**Deferred to MVP-β**:
- Lorebook (keyword-triggered injection)
- Knowledge Graph (entity extraction + approval workflow)
- Consistency Check (rule engine)
- Word Count Control (scene budget enforcement)

**Data model compatibility**:
- `lore_entries` table schema already defined (empty in MVP-α)
- `kg_proposals` table schema already defined (empty in MVP-α)
- Context Pack assembly has reserved slots for KG/Lore layers (unused in MVP-α)

**Upgrade path**:
- Run Alembic migration to add `lore_entries`, `kg_proposals`, `kg_evidence` tables
- Enable Lorebook UI panel (hidden in MVP-α)
- Enable KG extraction on chapter_mark_done event
