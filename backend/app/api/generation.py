"""AI generation endpoints: scene card + streaming draft."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai_schemas import (
    RewriteRequest,
    SceneCard,
    SceneCardRequest,
    SceneDraftRequest,
    WordCountCheck,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.llm import call_llm_stream, instructor_client
from app.models import Chapter, Scene
from app.services.context_pack import (
    assemble_context_pack,
    get_scene_project_id,
)

router = APIRouter(prefix="/api/generate", tags=["generation"])


@router.post("/scene-card", response_model=SceneCard)
async def generate_scene_card(
    req: SceneCardRequest, db: AsyncSession = Depends(get_db)
):
    """Generate a structured scene card via Instructor."""
    scene = await db.get(Scene, req.scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    chapter = await db.get(Chapter, req.chapter_id)
    if not chapter:
        raise HTTPException(404, "Chapter not found")

    project_id = await get_scene_project_id(db, req.scene_id)
    if not project_id:
        raise HTTPException(404, "Project not found")

    context = await assemble_context_pack(
        db, req.scene_id, req.chapter_id, project_id
    )

    prompt = f"""\
你是一位专业的小说编辑。根据以下上下文，为场景「{scene.title}」\
（所属章节：{chapter.title}）生成一张场景卡。

{context}

用户补充说明：{req.hints or '无'}

请生成包含标题、地点、时间、出场人物、核心冲突、转折点、揭示和目标字数的场景卡。"""

    result = await instructor_client.chat.completions.create(
        model=settings.LLM_MODEL,
        response_model=SceneCard,
        messages=[{"role": "user", "content": prompt}],
        max_retries=settings.LLM_MAX_RETRIES,
    )
    return result


@router.post("/scene-draft")
async def stream_scene_draft(
    req: SceneDraftRequest, db: AsyncSession = Depends(get_db)
):
    """Stream scene prose via SSE."""
    scene = await db.get(Scene, req.scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    chapter_id = scene.chapter_id
    project_id = await get_scene_project_id(db, req.scene_id)
    if not project_id:
        raise HTTPException(404, "Project not found")

    context = await assemble_context_pack(
        db, req.scene_id, chapter_id, project_id
    )

    card_json = req.scene_card.model_dump_json(
        indent=2, ensure_ascii=False
    )
    prompt = f"""\
你是一位专业的中文小说作家。根据以下场景卡和上下文，\
撰写场景正文。

## 场景卡
{card_json}

## 上下文
{context}

请直接输出场景正文（纯中文小说文本），不要输出任何标记或说明。\
目标字数约 {req.scene_card.target_chars} 字。"""

    async def event_stream():
        total_text = ""
        async for chunk in call_llm_stream(
            messages=[{"role": "user", "content": prompt}]
        ):
            total_text += chunk
            yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

        # Final event with stats
        done_data = {
            "done": True,
            "char_count": len(total_text),
            "characters_present": [
                c for c in req.scene_card.characters
                if c in total_text
            ],
        }
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(), media_type="text/event-stream"
    )


@router.post("/word-count-check", response_model=WordCountCheck)
async def word_count_check(req: RewriteRequest):
    """Check if scene text fits within the target char budget."""
    from app.services.word_count import check_word_budget

    return check_word_budget(req.text, req.target_chars)


@router.post("/rewrite")
async def rewrite_scene(
    req: RewriteRequest, db: AsyncSession = Depends(get_db)
):
    """Expand or compress scene text to fit target char budget via SSE."""
    scene = await db.get(Scene, req.scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    from app.services.word_count import build_rewrite_prompt, check_word_budget

    budget = check_word_budget(req.text, req.target_chars)
    if budget["status"] == "within":
        raise HTTPException(
            400,
            f"Text already within budget "
            f"(deviation={budget['deviation']:.1%})",
        )

    prompt = build_rewrite_prompt(
        req.text, req.target_chars, req.mode
    )

    async def event_stream():
        total_text = ""
        async for chunk in call_llm_stream(
            messages=[{"role": "user", "content": prompt}]
        ):
            total_text += chunk
            payload = json.dumps(
                {"text": chunk}, ensure_ascii=False
            )
            yield f"data: {payload}\n\n"

        result = check_word_budget(total_text, req.target_chars)
        done_data = {
            "done": True,
            "char_count": len(total_text),
            "budget": result,
        }
        payload = json.dumps(done_data, ensure_ascii=False)
        yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_stream(), media_type="text/event-stream"
    )
