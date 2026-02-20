# DR-011: FastAPI 流式输出与结构化校验的兼容性

## Executive Summary

流式输出和结构化校验并非不兼容，但需要区分场景：**结构化数据（场景卡 JSON）用非流式 + 完整校验，正文生成用流式 + 后置校验**。Python 生态中 Instructor 库和 PydanticAI 已提供成熟的流式结构化输出方案（partial streaming），可直接采用。

## Research Findings

### 1. 问题本质：两种输出类型需要不同策略

**结构化输出**（JSON Schema 校验）：
- 场景卡生成 → 返回完整 JSON 对象
- KG 抽取 → 返回完整 JSON 数组
- 章节摘要 → 返回结构化对象
- **特点**：用户不需要看到逐 token 生成过程，只需要最终结果

**正文生成**（流式输出）：
- 场景正文 → 逐段/逐句流式返回
- 润色/扩写 → 流式返回
- **特点**：用户需要实时看到生成进度，减少等待焦虑

**关键洞察**：这两类输出不需要用同一个机制。

### 2. 结构化输出方案（非流式）

**OpenAI Structured Outputs**：
- `response_format: {type: "json_schema", json_schema: {...}}`
- 模型被约束只输出符合 schema 的 JSON
- 保证 100% schema 合规（模型内部做 constrained decoding）

**Anthropic Tool Use**：
- 通过 tool_use 机制返回结构化数据
- 模型输出 JSON 参数，API 保证格式正确

**Instructor 库**（Python，11k+ stars）：
- 封装 OpenAI/Anthropic/Gemini 等多个 provider
- 输入 Pydantic model → 输出校验后的 Python 对象
- 自动重试：如果校验失败，自动回喂错误信息让模型修正
- 支持 `create_partial` 做流式结构化输出

**FastAPI 集成**：
```python
import instructor
from pydantic import BaseModel

client = instructor.from_provider("openai/gpt-4o", async_client=True)

class SceneCard(BaseModel):
    title: str
    location: str
    characters: list[str]
    conflict: str
    target_chars: int

@app.post("/api/generate/scene-card", response_model=SceneCard)
async def generate_scene_card(request: SceneRequest):
    return await client.chat.completions.create(
        model="gpt-4o",
        response_model=SceneCard,
        messages=[...]
    )
```

### 3. 流式正文 + 后置校验方案

**FastAPI SSE 实现**：
```python
from fastapi.responses import StreamingResponse

@app.post("/api/generate/scene-draft")
async def generate_draft(request: DraftRequest):
    async def stream():
        full_text = ""
        async for chunk in llm_stream(request):
            full_text += chunk
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        # 流式结束后做后置校验
        validation = validate_draft(full_text, request.scene_card)
        yield f"data: {json.dumps({'validation': validation})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")
```

**后置校验内容**：
- 字数是否在场景预算范围内
- 是否包含必要的角色出场
- 是否存在视角偏离
- 校验结果在流式最后一个 event 中返回

### 4. 流式结构化输出（Partial Streaming）

**Instructor `create_partial`**：
- 流式返回 Pydantic 模型的部分填充版本
- 所有字段标记为 Optional，随着生成逐步填充
- 使用 `jiter`（快速 JSON 解析器）解析不完整 JSON

```python
from instructor import create_partial

PartialSceneCard = create_partial(SceneCard)

async for partial in client.chat.completions.create_partial(
    model="gpt-4o",
    response_model=SceneCard,
    messages=[...],
    stream=True
):
    # partial.title 可能已有值，partial.conflict 可能还是 None
    yield partial
```

**PydanticAI + FastAPI SSE**（2025 新方案）：
- PydanticAI 是 Pydantic 团队的官方 agent runtime
- 内建流式结构化输出支持
- 与 FastAPI SSE 原生集成

### 5. 推荐架构决策

| API 端点 | 输出类型 | 方案 |
|---------|---------|------|
| `POST /api/generate/scene-card` | 结构化 JSON | 非流式 + Instructor + Pydantic 校验 |
| `POST /api/generate/scene-draft` | 流式正文 | SSE 流式 + 后置字数/基础校验 |
| `POST /api/generate/rewrite` | 流式正文 | SSE 流式 |
| `POST /api/extract/kg` | 结构化 JSON | 非流式 + Instructor + Schema 校验 |
| `POST /api/extract/chapter-summary` | 结构化 JSON | 非流式 + Pydantic 校验 |
| `POST /api/generate/plan-next` | 结构化 JSON | 非流式或 Partial Streaming |

## Impact on Spec

1. §10 的 Schema-first 策略完全可行，但需要区分流式和非流式端点
2. §15.3 的 API 端点需要标注哪些是流式、哪些是非流式
3. 建议引入 Instructor 库作为结构化输出的标准方案
4. §5.1 的 AI Orchestrator 需要说明流式/非流式的路由逻辑

## Recommendations

1. **结构化输出用 Instructor + Pydantic**：场景卡、KG 抽取、摘要等非流式端点
2. **正文生成用 FastAPI SSE**：流式返回 + 后置校验
3. **不需要"先完整生成再流式返回"**——正文直接流式，结构化数据直接非流式
4. **Instructor 的自动重试**解决 schema 不合规问题（最多重试 3 次）
5. **API 端点明确标注** `stream: true/false`，前端按此选择 SSE 或普通 JSON 请求
6. **MVP 依赖**：`pip install instructor fastapi[all] pydantic`

## Sources

- [Instructor: Structured LLM Outputs](https://python.useinstructor.com/)
- [Instructor: Streaming Partial Responses](https://python.useinstructor.com/concepts/partial)
- [Instructor: FastAPI Integration](https://python.useinstructor.com/concepts/fastapi/)
- [FastAPI + Structured Outputs (Medium)](https://medium.com/@hjparmar1944/fastapi-structured-outputs-turning-llm-tool-calls-into-reliable-backend-apis-8e9bcdbe2ac4)
- [How to Stream Structured JSON with FastAPI & PydanticAI](https://python.plainenglish.io/how-to-stream-structured-json-output-from-llms-using-fastapi-and-pydanticai-c1dacae66ca6)
- [PydanticAI: Agent Runtime](https://ai.pydantic.dev/)
