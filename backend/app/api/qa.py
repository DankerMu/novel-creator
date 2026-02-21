"""Quality Assurance API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ConsistencyResult
from app.core.database import get_db
from app.services.consistency import run_consistency_check

router = APIRouter(prefix="/api", tags=["qa"])


class ConsistencyCheckRequest(BaseModel):
    project_id: int
    ngram_n: int = 4
    ngram_threshold: int = 3


@router.post("/qa/check", response_model=list[ConsistencyResult])
async def check_consistency(
    body: ConsistencyCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run rule-based consistency checks on a project."""
    return await run_consistency_check(
        db,
        body.project_id,
        ngram_n=body.ngram_n,
        ngram_threshold=body.ngram_threshold,
    )
