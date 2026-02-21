from datetime import datetime

from pydantic import BaseModel


# --- Project ---
class ProjectCreate(BaseModel):
    title: str
    description: str = ""

class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None

class ProjectOut(BaseModel):
    id: int
    title: str
    description: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# --- Book ---
class BookCreate(BaseModel):
    project_id: int
    title: str
    sort_order: int = 0

class BookUpdate(BaseModel):
    title: str | None = None
    sort_order: int | None = None

class BookOut(BaseModel):
    id: int
    project_id: int
    title: str
    sort_order: int
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Chapter ---
class ChapterCreate(BaseModel):
    book_id: int
    title: str
    sort_order: int = 0

class ChapterUpdate(BaseModel):
    title: str | None = None
    sort_order: int | None = None
    status: str | None = None

class ChapterOut(BaseModel):
    id: int
    book_id: int
    title: str
    sort_order: int
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


# --- Scene ---
class SceneCreate(BaseModel):
    chapter_id: int
    title: str
    sort_order: int = 0

class SceneUpdate(BaseModel):
    title: str | None = None
    sort_order: int | None = None

class SceneOut(BaseModel):
    id: int
    chapter_id: int
    title: str
    sort_order: int
    created_at: datetime
    model_config = {"from_attributes": True}


# --- SceneTextVersion ---
class SceneVersionCreate(BaseModel):
    content_md: str
    created_by: str = "user"

class SceneVersionOut(BaseModel):
    id: int
    scene_id: int
    version: int
    content_md: str
    char_count: int
    created_at: datetime
    created_by: str
    model_config = {"from_attributes": True}


# --- Project Tree ---
class SceneTreeNode(BaseModel):
    id: int
    title: str
    sort_order: int
    model_config = {"from_attributes": True}

class ChapterTreeNode(BaseModel):
    id: int
    title: str
    sort_order: int
    status: str
    scenes: list[SceneTreeNode]
    model_config = {"from_attributes": True}

class BookTreeNode(BaseModel):
    id: int
    title: str
    sort_order: int
    chapters: list[ChapterTreeNode]
    model_config = {"from_attributes": True}

class ProjectTree(BaseModel):
    id: int
    title: str
    books: list[BookTreeNode]
    model_config = {"from_attributes": True}


# --- ChapterSummary ---
class ChapterSummaryUpdate(BaseModel):
    summary_md: str | None = None
    key_events: list[str] | None = None
    keywords: list[str] | None = None
    entities: list[str] | None = None
    plot_threads: list[str] | None = None

class ChapterSummaryOut(BaseModel):
    id: int
    chapter_id: int
    summary_md: str
    key_events: list[str]
    keywords: list[str]
    entities: list[str]
    plot_threads: list[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# --- BibleField ---
class BibleFieldUpdate(BaseModel):
    value_md: str | None = None
    locked: bool | None = None

class BibleFieldOut(BaseModel):
    id: int
    project_id: int
    key: str
    value_md: str
    locked: bool
    updated_at: datetime
    model_config = {"from_attributes": True}


# --- LoreEntry ---
class LoreEntryCreate(BaseModel):
    project_id: int
    type: str = "Concept"
    title: str
    aliases: list[str] = []
    content_md: str = ""
    secrets_md: str = ""
    triggers: dict = {"keywords": [], "and_keywords": []}
    priority: int = 5
    locked: bool = False

class LoreEntryUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    aliases: list[str] | None = None
    content_md: str | None = None
    secrets_md: str | None = None
    triggers: dict | None = None
    priority: int | None = None
    locked: bool | None = None

class LoreEntryOut(BaseModel):
    id: int
    project_id: int
    type: str
    title: str
    aliases: list[str]
    content_md: str
    secrets_md: str
    triggers: dict
    priority: int
    locked: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# --- Consistency Check ---

class ConsistencyResult(BaseModel):
    type: str
    severity: str
    confidence: float
    source: str
    message: str
    evidence: list[str]
    evidence_locations: list[str]
    suggest_fix: str


# --- KG ---

class KGNodeOut(BaseModel):
    id: int
    project_id: int
    label: str
    name: str
    properties: dict
    created_at: datetime
    model_config = {"from_attributes": True}


class KGEdgeOut(BaseModel):
    id: int
    project_id: int
    source_node_id: int
    target_node_id: int
    relation: str
    properties: dict
    created_at: datetime
    model_config = {"from_attributes": True}


class KGProposalOut(BaseModel):
    id: int
    project_id: int
    chapter_id: int
    category: str
    data: dict
    confidence: float
    status: str
    evidence_text: str
    evidence_location: str
    reviewed_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}
