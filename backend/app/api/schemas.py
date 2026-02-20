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
