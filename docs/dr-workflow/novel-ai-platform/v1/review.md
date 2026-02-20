# Review v1

## Score: 82/100

| 维度 | 分数 | 说明 |
|------|------|------|
| 技术完整性 (Technical Completeness) | 21/25 | 12 项 DR 调研已覆盖所有关键技术疑点；KG/Lorebook/Context Pack/工作流均有落地方案。扣分项：§6.1 SQLite 表结构缺少 `kg_evidence` 和 `workflow_node_runs` 新增表的定义；KG 抽取 JSON Schema (§10.2) 未新增 `confidence` 字段。 |
| 可行性与证据 (Feasibility & Evidence) | 22/25 | 12 份 DR 报告提供了充分的外部证据（SillyTavern/NovelAI/Instructor/simple-graph 等）。MVP-α/β 拆分合理。扣分项：DR-012 的市场数据偏泛（缺少一手用户访谈或问卷数据）；AI 辅助开发加速系数 1.7x 的假设未经本项目验证。 |
| 架构一致性 (Architecture Coherence) | 20/25 | GraphService 抽象接口、Context Pack 分区预算、流式/非流式端点分离等设计内部一致。扣分项：§5.1 的 AI Orchestrator 职责未更新（未反映 Instructor 集成和流式/非流式路由）；事件总线的具体技术选型未说明（Python 内 asyncio.Queue? Redis Pub/Sub?）。 |
| 实施就绪度 (Implementation Readiness) | 19/25 | MVP-α 范围清晰可执行；工作流 JSON 格式和 handler 注册机制具体可编码。扣分项：前端技术栈仍未锁定（React vs Vue vs Next.js）；§16 前端设计章节未整合 DR 发现（KG 批量审阅 UI、置信度过滤等新交互未体现）；缺少数据库迁移策略（从 MVP-α 到 β 的 schema 变更）。 |

## New Suspicious Items

以下 5 项是本轮 REWRITE 后新发现的待验证点，需要在下一轮迭代中通过 DR 或直接修正：

| # | 类型 | 可疑点 | 研究方向 |
|---|------|--------|----------|
| 1 | data | §6.1 SQLite 表结构未同步更新：缺少 `kg_evidence`、`workflow_node_runs` 表定义，`kg_proposals` 缺少 `confidence` 字段 | 直接修正，无需 DR |
| 2 | architecture | §5.1 AI Orchestrator 职责描述未更新：未反映 Instructor/Pydantic 集成、流式/非流式路由、LLM Provider 抽象层 | 直接修正 |
| 3 | tech | §10.2 KG 抽取 JSON Schema 未新增 `confidence` 和 `approval_status` 字段 | 直接修正 |
| 4 | product | §16 前端设计未整合 DR-009 的批量审阅 UI（置信度过滤、快捷键、diff 视图）和 DR-011 的流式/非流式交互差异 | 需补充前端交互规格 |
| 5 | architecture | 事件总线具体技术选型未说明——本地单机场景下 asyncio.Queue 够用还是需要更重的方案 | 可直接修正，选 asyncio |

## Verdict

**CONTINUE** (score 82 < 90，且有 5 个新可疑项，其中 3 个可直接修正、2 个需补充)

下一轮迭代重点：
1. 直接修正 §6.1、§5.1、§10.2 的结构/字段遗漏（无需 DR）
2. 补充 §16 前端交互规格（DR-009 批量审阅 + DR-011 流式交互）
3. 确认事件总线选型
