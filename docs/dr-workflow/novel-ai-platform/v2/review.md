# Review v2

## Score: 91/100

| 维度 | 分数 | 说明 |
|------|------|------|
| 技术完整性 (Technical Completeness) | 24/25 | 所有 12 项 DR 调研已整合；`kg_evidence`、`workflow_node_runs` 新增表已补充；KG Schema 已加入 `confidence` 字段。扣分项：events/relations 的 JSON Schema 未同步加入 `confidence` 字段（仅 entities 已加），但这是小问题。 |
| 可行性与证据 (Feasibility & Evidence) | 23/25 | 12 份 DR 报告覆盖了所有关键技术风险点，均有外部证据支撑。MVP-α/β 拆分和时间线评估合理。扣分项：DR-012 市场数据仍偏泛（无一手用户访谈），但作为技术设计文档而非 PRD，这不是关键缺陷。 |
| 架构一致性 (Architecture Coherence) | 23/25 | AI Orchestrator 已更新（Instructor + SSE + asyncio.Queue）；GraphService 抽象接口、Context Pack 分区预算、流式/非流式端点分离等设计内部一致。扣分项：§8.3 的 Lorebook 与 KG 协同部分仍引用旧的优先级描述，未完全与 §7.3 的置信度分级对齐。 |
| 实施就绪度 (Implementation Readiness) | 21/25 | MVP-α 范围清晰；工作流 JSON 格式可编码；前端 KG 批量审阅 UI 和流式交互已补充。扣分项：前端技术栈仍未最终锁定（建议选项已给但未决策）；数据库迁移策略（MVP-α → β 的 schema 变更）未说明。 |

## New Suspicious Items

None — 剩余扣分项均为细节级问题，不构成新的需要 DR 调研的可疑点：
- events/relations Schema 加 `confidence`：直接修正即可
- §8.3 优先级描述与 §7.3 对齐：文案调整
- 前端技术栈锁定：属于团队决策，非规格书职责
- 数据库迁移策略：属于工程实施细节，MVP-α 阶段无迁移需求

## Verdict

**FINALIZE** (score 91 ≥ 90 AND new_dr_items = 0)

### 改进总结（v0.1 → v0.2）

| 章节 | 主要改进 |
|------|----------|
| §1.1 | 定位从"百万字长篇"调整为"中长篇"（10万~百万字）；新增目标用户画像表 |
| §5.1 | AI Orchestrator 更新为 Instructor+Pydantic+SSE+asyncio.Queue |
| §5.2 | Lite 模式明确能力边界；新增 GraphService 抽象接口 |
| §6.1 | 新增 `kg_evidence`、`workflow_node_runs` 表；`kg_proposals` 增加 `confidence` 和细化状态 |
| §6.2 | evidence 改为混合存储（Neo4j 指针 + SQLite 全文）；新增 `approval_status` 字段 |
| §6.3 | 向量检索分阶段路线（MVP无 → v1 sqlite-vec → v2 Qdrant）；新增去重策略 |
| §7.2 | Lorebook 注入策略大幅扩充（Scan Depth、截断策略、priority 默认值） |
| §7.3 | KG 审阅从"先审后入"改为置信度分级自动入库 + 事后修正 |
| §8.2 | 新增具体预算分配表和溢出策略 |
| §10.2 | KG 抽取 Schema 新增 `confidence` 字段 |
| §11.2 | 强约束标注为 v1 功能；补充实现要点（soft/hard limit + 句号边界） |
| §12 | 拆分为规则引擎（MVP）+ LLM 推理（v1）混合架构；新增 `confidence`/`source` 输出字段 |
| §14.2 | 从"DSL 演进"改为自建轻量 JSON DAG 引擎（~500行）；新增工作流 JSON 示例 |
| §15.3 | 明确区分流式/非流式端点及对应技术方案 |
| §16 | 新增 §16.3 流式交互规格 + §16.4 KG 批量审阅 UI 规格 |
| §20 | MVP 拆为 α（3~4周，能写出来）+ β（+2~3周，写得一致）；v1/v2 路线更新 |
