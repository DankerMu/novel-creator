from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    BookCreate, BookOut, BookUpdate,
    ChapterCreate, ChapterOut, ChapterUpdate,
    ProjectCreate, ProjectOut, ProjectTree, ProjectUpdate,
    SceneCreate, SceneOut, SceneUpdate,
    SceneVersionCreate, SceneVersionOut,
)
from app.core.database import get_db
from app.models import Book, Chapter, Project, Scene, SceneTextVersion

router = APIRouter(prefix="/api", tags=["projects"])


# ── Projects ──────────────────────────────────────────────

@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(**data.model_dump())
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectOut)
async def update_project(project_id: int, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(project, k, v)
    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    await db.delete(project)


@router.get("/projects/{project_id}/tree", response_model=ProjectTree)
async def get_project_tree(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.books)
            .selectinload(Book.chapters)
            .selectinload(Chapter.scenes)
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return project


# ── Books ─────────────────────────────────────────────────

@router.post("/books", response_model=BookOut, status_code=201)
async def create_book(data: BookCreate, db: AsyncSession = Depends(get_db)):
    parent = await db.get(Project, data.project_id)
    if not parent:
        raise HTTPException(404, "Project not found")
    book = Book(**data.model_dump())
    db.add(book)
    await db.flush()
    await db.refresh(book)
    return book


@router.get("/books", response_model=list[BookOut])
async def list_books(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Book).where(Book.project_id == project_id).order_by(Book.sort_order)
    )
    return result.scalars().all()


@router.get("/books/{book_id}", response_model=BookOut)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book


@router.put("/books/{book_id}", response_model=BookOut)
async def update_book(book_id: int, data: BookUpdate, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(book, k, v)
    await db.flush()
    await db.refresh(book)
    return book


@router.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    await db.delete(book)


# ── Chapters ──────────────────────────────────────────────

@router.post("/chapters", response_model=ChapterOut, status_code=201)
async def create_chapter(data: ChapterCreate, db: AsyncSession = Depends(get_db)):
    parent = await db.get(Book, data.book_id)
    if not parent:
        raise HTTPException(404, "Book not found")
    chapter = Chapter(**data.model_dump())
    db.add(chapter)
    await db.flush()
    await db.refresh(chapter)
    return chapter


@router.get("/chapters", response_model=list[ChapterOut])
async def list_chapters(book_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.sort_order)
    )
    return result.scalars().all()


@router.get("/chapters/{chapter_id}", response_model=ChapterOut)
async def get_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    return chapter


@router.put("/chapters/{chapter_id}", response_model=ChapterOut)
async def update_chapter(chapter_id: int, data: ChapterUpdate, db: AsyncSession = Depends(get_db)):
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(chapter, k, v)
    await db.flush()
    await db.refresh(chapter)
    return chapter


@router.delete("/chapters/{chapter_id}", status_code=204)
async def delete_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    await db.delete(chapter)


# ── Scenes ────────────────────────────────────────────────

@router.post("/scenes", response_model=SceneOut, status_code=201)
async def create_scene(data: SceneCreate, db: AsyncSession = Depends(get_db)):
    parent = await db.get(Chapter, data.chapter_id)
    if not parent:
        raise HTTPException(404, "Chapter not found")
    scene = Scene(**data.model_dump())
    db.add(scene)
    await db.flush()
    await db.refresh(scene)
    # Create initial empty version
    v = SceneTextVersion(scene_id=scene.id, version=1, content_md="", char_count=0)
    db.add(v)
    return scene


@router.get("/scenes", response_model=list[SceneOut])
async def list_scenes(chapter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scene).where(Scene.chapter_id == chapter_id).order_by(Scene.sort_order)
    )
    return result.scalars().all()


@router.get("/scenes/{scene_id}", response_model=SceneOut)
async def get_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    scene = await db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    return scene


@router.put("/scenes/{scene_id}", response_model=SceneOut)
async def update_scene(scene_id: int, data: SceneUpdate, db: AsyncSession = Depends(get_db)):
    scene = await db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(scene, k, v)
    await db.flush()
    await db.refresh(scene)
    return scene


@router.delete("/scenes/{scene_id}", status_code=204)
async def delete_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    scene = await db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    await db.delete(scene)


# ── Scene Versions ────────────────────────────────────────

@router.post("/scenes/{scene_id}/versions", response_model=SceneVersionOut, status_code=201)
async def create_scene_version(
    scene_id: int, data: SceneVersionCreate, db: AsyncSession = Depends(get_db)
):
    scene = await db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    # Get latest version number
    result = await db.execute(
        select(SceneTextVersion.version)
        .where(SceneTextVersion.scene_id == scene_id)
        .order_by(SceneTextVersion.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none() or 0

    version = SceneTextVersion(
        scene_id=scene_id,
        version=latest + 1,
        content_md=data.content_md,
        char_count=len(data.content_md),
        created_by=data.created_by,
    )
    db.add(version)
    await db.flush()
    await db.refresh(version)
    return version


@router.get("/scenes/{scene_id}/versions", response_model=list[SceneVersionOut])
async def list_scene_versions(scene_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SceneTextVersion)
        .where(SceneTextVersion.scene_id == scene_id)
        .order_by(SceneTextVersion.version.desc())
    )
    return result.scalars().all()


@router.get("/scenes/{scene_id}/versions/latest", response_model=SceneVersionOut)
async def get_latest_version(scene_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SceneTextVersion)
        .where(SceneTextVersion.scene_id == scene_id)
        .order_by(SceneTextVersion.version.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "No versions found")
    return version
