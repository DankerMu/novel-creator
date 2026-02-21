"""AI generation endpoints: scene card + streaming draft."""

import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai_schemas import (
    RewriteRequest,
    SceneCard,
    SceneCardRequest,
    SceneDraftRequest,
    WordCountCheck,
    WordCountCheckRequest,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.llm import call_llm, call_llm_stream
from app.models import Chapter, Scene
from app.services.context_pack import (
    assemble_context_pack,
    get_scene_project_id,
)
from app.services.word_count import build_rewrite_prompt, check_word_budget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generation"])

_SCENE_CARD_SYSTEM = """\
你是一位专业的小说编辑。根据上下文为场景生成一张场景卡。
返回一个 JSON 对象，包含以下字段：

{
  "title": "场景标题",
  "location": "场景地点",
  "time": "时间",
  "characters": ["人物1", "人物2"],
  "conflict": "核心冲突",
  "turning_point": "转折点",
  "reveal": "揭示/悬念",
  "target_chars": 1500
}

规则：
- 只输出合法 JSON，不要 markdown 围栏
- target_chars 为整数，建议 1000-2000
"""


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
场景「{scene.title}」（所属章节：{chapter.title}）

上下文：
{context}

用户补充说明：{req.hints or '无'}"""

    messages = [
        {"role": "system", "content": _SCENE_CARD_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    response = await call_llm(
        messages, response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content or ""
    data = _parse_scene_card_json(raw)
    return SceneCard(**data)


def _parse_scene_card_json(raw: str) -> dict:
    """Parse scene card JSON from LLM output with fence/quote repair."""
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    else:
        idx = raw.find("{")
        if idx > 0:
            raw = raw[idx:]
    raw = re.sub(
        r'(?<=[\u4e00-\u9fff\u3400-\u4dbf])"(?=[\u4e00-\u9fff\u3400-\u4dbf])',
        r'\\"',
        raw,
    )
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse scene card JSON: %s", raw[:200])
        return {
            "title": "", "location": "", "time": "",
            "characters": [], "conflict": "",
        }


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
async def word_count_check(req: WordCountCheckRequest):
    """Check if scene text fits within the target char budget."""
    return check_word_budget(req.text, req.target_chars)


@router.post("/rewrite")
async def rewrite_scene(
    req: RewriteRequest, db: AsyncSession = Depends(get_db)
):
    """Expand or compress scene text to fit target char budget via SSE."""
    scene = await db.get(Scene, req.scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    budget = check_word_budget(req.text, req.target_chars)
    if budget["status"] == "within":
        raise HTTPException(
            400,
            f"Text already within budget "
            f"(deviation={budget['deviation']:.1%})",
        )

    expected_mode = budget["suggestion"]
    if req.mode != expected_mode:
        raise HTTPException(
            400,
            f"Mode '{req.mode}' conflicts with budget status "
            f"'{budget['status']}': expected '{expected_mode}'",
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
