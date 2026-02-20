# DR-007: 工作流 DSL 的解析与执行引擎

## Executive Summary

MVP 不需要自定义 DSL——用 Python 原生 async 函数 + JSON 配置即可实现全部所需工作流能力。引入 Prefect/Temporal 等重型引擎对本地单机项目过于复杂。推荐自建轻量级工作流引擎：JSON 定义节点 DAG + Python 执行器 + SQLite 状态持久化，总代码量约 500~800 行。

## Research Findings

### 1. 主流工作流引擎对比

| 引擎 | 类型 | 部署复杂度 | 适合场景 | 本项目适用性 |
|------|------|-----------|---------|-------------|
| Airflow | 重型 DAG | 需 Postgres + Redis + Worker | 大规模数据管线 | ❌ 过于重型 |
| Prefect | 中型 DAG | 可本地运行，但推荐 Prefect Cloud | 数据工程 | ⚠️ 可用但 overkill |
| Temporal | 重型状态机 | 需独立服务 | 微服务编排 | ❌ 过于重型 |
| Dramatiq | 任务队列 | 需 Redis/RabbitMQ | 异步任务 | ⚠️ 不是 DAG 引擎 |
| 自建轻量 | JSON DAG + Python | 零依赖 | 本地应用内嵌 | ✅ 最佳选择 |

### 2. 自建轻量工作流引擎设计

**JSON 工作流定义**：
```json
{
  "id": "chapter_complete_pipeline",
  "trigger": "chapter_mark_done",
  "nodes": [
    {"id": "summarize", "handler": "chapter_summary", "inputs": ["chapter_id"]},
    {"id": "extract_kg", "handler": "kg_extraction", "inputs": ["chapter_id"], "depends_on": ["summarize"]},
    {"id": "update_lore", "handler": "lore_suggestion", "inputs": ["chapter_id"], "depends_on": ["summarize"]},
    {"id": "qa_check", "handler": "consistency_check", "depends_on": ["extract_kg", "update_lore"]}
  ]
}
```

**执行引擎核心**（~300 行 Python）：
```python
class WorkflowEngine:
    def __init__(self, db: Database):
        self.registry: dict[str, Callable] = {}  # handler name → async function
        self.db = db

    def register(self, name: str):
        """装饰器注册节点处理器"""
        def decorator(fn):
            self.registry[name] = fn
            return fn
        return decorator

    async def run(self, workflow_def: dict, context: dict):
        """拓扑排序 → 按层并行执行 → 持久化状态"""
        run_id = create_run_record(self.db, workflow_def)
        for layer in topological_layers(workflow_def["nodes"]):
            tasks = [self._execute_node(node, context, run_id) for node in layer]
            await asyncio.gather(*tasks)
        update_run_status(self.db, run_id, "completed")
```

**状态持久化**：复用 §6.1 的 `workflow_runs` 表 + 新增 `workflow_node_runs` 表：
- `node_id`, `run_id`, `status`(pending/running/completed/failed), `started_at`, `completed_at`, `output_json`, `error_msg`

### 3. 安全性考量（防代码注入）

**JSON/YAML 配置模式**（MVP 推荐）：
- 工作流定义只是声明式 JSON，不包含可执行代码
- handler 名称映射到预注册的 Python 函数（白名单机制）
- 用户无法注入任意代码——只能组合已注册的节点
- 安全性等同于 REST API 路由

**Python DSL 模式**（v2 考虑）：
- 若后续要支持用户自定义 Python DSL，需要沙箱：
  - `RestrictedPython`：限制 AST，禁止 import/exec/eval
  - `ast.parse` + 白名单检查：只允许特定函数调用
  - Docker 沙箱：极端方案，隔离执行环境
- **建议 v2 才考虑**，MVP 的 JSON 配置已足够

### 4. 节点级进度上报

**实现方式**：
- 每个节点执行前后更新 `workflow_node_runs` 状态
- 前端通过 SSE 或 WebSocket 订阅 run_id 的状态变更
- 后端在节点 handler 中支持 `progress_callback(percent, message)` 回调
- UI 显示 DAG 图 + 每个节点的状态色标（灰/蓝/绿/红）

### 5. 中断恢复

**实现方式**：
- 每个节点完成后将 output 持久化到 `workflow_node_runs.output_json`
- 恢复时读取 `workflow_runs`，找到最后一个 completed 节点，从下一个 pending 节点继续
- 失败节点支持单节点重试（不重跑整个 workflow）
- `workflow_runs` 增加 `resume_from_node` 字段

## Impact on Spec

1. §14.2 建议删除"后续演进到 Python 风格 DSL"的措辞——JSON 配置 + 装饰器注册已覆盖 MVP 和 v1 需求
2. §14.3 的工程规则可直接落地为上述架构
3. §6.1 需要新增 `workflow_node_runs` 表
4. §15.5 的工作流 API 需要增加 `GET /api/workflows/runs/{id}/nodes` 接口

## Recommendations

1. **MVP 用 JSON 定义 + Python 装饰器注册**，不引入任何外部工作流引擎
2. **自建引擎核心约 500~800 行**：DAG 解析 + 拓扑排序 + 异步并行执行 + SQLite 状态机
3. **预定义 5 个核心 handler**：`chapter_summary`, `kg_extraction`, `lore_suggestion`, `consistency_check`, `export_chapter`
4. **支持单节点重试和断点恢复**
5. **前端用 SSE 推送节点级进度**
6. **Python DSL 排到 v2**，且必须用 `RestrictedPython` 或 AST 白名单做沙箱

## Sources

- [Prefect: Modern Workflow Orchestration](https://www.prefect.io/)
- [Temporal: Durable Execution Platform](https://temporal.io/)
- [RestrictedPython: Python 沙箱](https://restrictedpython.readthedocs.io/)
- [NovelForge Engineering Rule: 事件驱动 + 装饰器注册](https://github.com/RhythmicWave/NovelForge)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
