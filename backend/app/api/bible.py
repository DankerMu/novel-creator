from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import BibleFieldOut, BibleFieldUpdate
from app.core.database import get_db
from app.models import BibleField, Project

router = APIRouter(prefix="/api", tags=["bible"])

DEFAULT_BIBLE_KEYS = [
    "Genre", "Style", "POV", "Tense", "Synopsis",
    "Characters", "World Rules", "Outline", "Scenes",
]


@router.get("/bible", response_model=list[BibleFieldOut])
async def list_bible_fields(
    project_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BibleField)
        .where(BibleField.project_id == project_id)
        .order_by(BibleField.id)
    )
    fields = result.scalars().all()

    # Auto-create default fields if none exist
    if not fields:
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        for key in DEFAULT_BIBLE_KEYS:
            field = BibleField(
                project_id=project_id, key=key, value_md="", locked=False
            )
            db.add(field)
        await db.flush()
        result = await db.execute(
            select(BibleField)
            .where(BibleField.project_id == project_id)
            .order_by(BibleField.id)
        )
        fields = result.scalars().all()

    return fields


@router.get("/bible/locked", response_model=list[BibleFieldOut])
async def get_locked_fields(
    project_id: int, db: AsyncSession = Depends(get_db)
):
    """Get only locked Bible fields (used for Context Pack injection)."""
    result = await db.execute(
        select(BibleField)
        .where(
            BibleField.project_id == project_id,
            BibleField.locked.is_(True),
        )
        .order_by(BibleField.id)
    )
    return result.scalars().all()


@router.put("/bible/{field_id}", response_model=BibleFieldOut)
async def update_bible_field(
    field_id: int,
    data: BibleFieldUpdate,
    db: AsyncSession = Depends(get_db),
):
    field = await db.get(BibleField, field_id)
    if not field:
        raise HTTPException(404, "Bible field not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(field, k, v)
    await db.flush()
    await db.refresh(field)
    return field
