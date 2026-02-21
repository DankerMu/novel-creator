"""Quality Assurance API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ConsistencyResult
from app.core.database import get_db
from app.models.tables import Project
from app.services.consistency import run_consistency_check

router = APIRouter(prefix="/api", tags=["qa"])


class ConsistencyCheckRequest(BaseModel):
    project_id: int
    ngram_n: int = Field(default=4, ge=2, le=10)
    ngram_threshold: int = Field(default=3, ge=2, le=20)


@router.post("/qa/check", response_model=list[ConsistencyResult])
async def check_consistency(
    body: ConsistencyCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run rule-based consistency checks on a project."""
    project = await db.get(Project, body.project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return await run_consistency_check(
        db,
        body.project_id,
        ngram_n=body.ngram_n,
        ngram_threshold=body.ngram_threshold,
    )
