# 里程碑分解（Module-level Decomposition）

> 基于 v0.2 规格书的迭代路线（§20），按模块拆解为可执行的里程碑。
> 团队假设：1 人全栈 + AI 辅助开发。技术栈：FastAPI(Python) + React/Next.js(TypeScript) + SQLite。

---

## Phase 1: MVP-α（3~4 周，核心可用："能写出来"）

### M1.1 项目骨架 + CRUD
- **涉及章节**：§4, §6.1, §15.1
- **工作内容**：
  - FastAPI 项目初始化 + SQLite 数据库 + Alembic 迁移
  - Project / Book / Chapter / Scene CRUD API
  - 前端项目初始化（React + shadcn/ui）
  - 左侧项目树 + 中间编辑器骨架
- **估算**：后端 2d + 前端 3d = 5d
- **验收**：能创建项目、添加章节/场景、编辑保存正文

### M1.2 Story Bible
- **涉及章节**：§7.1, §15.2
- **工作内容**：
  - Bible 核心字段 CRUD（Genre/Style/POV/Tense/Synopsis/Characters/World Rules/Outline）
  - `locked` 开关（锁定后作为硬约束注入 prompt）
  - 右侧 Bible 标签面板
- **估算**：后端 1d + 前端 2d = 3d
- **验收**：能手写/编辑 Bible 字段；锁定字段在生成时注入

### M1.3 AI 场景生成（流式）
- **涉及章节**：§9.1 阶段 1-2, §15.3, §11.2
- **工作内容**：
  - LLM Provider 抽象层（OpenAI-compatible endpoint）
  - 场景卡生成（Instructor + Pydantic，非流式）
  - 场景正文生成（FastAPI SSE，流式）
  - 基础 Context Pack（Bible + 最近文本，固定模板）
- **估算**：后端 3d + 前端 2d = 5d
- **关键依赖**：M1.1（Scene 数据）、M1.2（Bible 注入）
- **验收**：能从场景卡生成正文，流式显示在编辑器中

### M1.4 章节摘要（自动）
- **涉及章节**：§7.4, §15.4
- **工作内容**：
  - `chapter_mark_done` 触发摘要生成
  - Chapter Summary 存入 `chapter_summaries` 表
  - 摘要纳入后续章节的 Context Pack
- **估算**：后端 2d + 前端 1d = 3d
- **验收**：章节标记完成后自动生成摘要；摘要在下一章生成时注入

### M1.5 导出
- **涉及章节**：§3.3
- **工作内容**：
  - 导出 Markdown / TXT（全书/单章）
  - 前端导出按钮
- **估算**：后端 1d + 前端 1d = 2d
- **验收**：能导出完整书稿为 .md/.txt 文件

**MVP-α 总计：~18 工作日（含缓冲 ≈ 3~4 周）**

---

## Phase 2: MVP-β（+2~3 周，特色能力："写得一致"）

### M2.1 Lorebook（关键词触发注入）
- **涉及章节**：§7.2, §15.2
- **工作内容**：
  - Lore 条目 CRUD（type/title/aliases/content/secrets/triggers/priority）
  - 关键词 OR 匹配 + aliases 扩展
  - Scan Depth 配置（扫描当前场景 + 前一场景）
  - 预算截断逻辑（priority DESC + Bottom trim to sentence）
  - 右侧 Lorebook 标签面板
  - 导入/导出（SillyTavern JSON 格式兼容）
- **估算**：后端 3d + 前端 3d = 6d
- **关键依赖**：M1.3（Context Pack 集成）
- **验收**：关键词出现时自动注入条目；预算超出时按 priority 截断

### M2.2 KG 抽取 + 置信度分级自动入库
- **涉及章节**：§7.3, §6.1, §6.2, §10.2, §15.4
- **工作内容**：
  - KG 抽取 prompt（Schema-first，输出含 confidence）
  - SQLite 双表 KG（Lite 模式：`kg_nodes` + `kg_edges`）
  - `kg_proposals` + `kg_evidence` 表
  - 置信度分级入库（High 自动 / Medium 待确认 / Low 排队）
  - GraphService 抽象接口（SQLiteGraphAdapter）
- **估算**：后端 3d + 前端 1d = 4d
- **关键依赖**：M1.4（章节完成触发）
- **验收**：章完成后自动抽取 KG 事实；高置信度事实自动入库

### M2.3 KG 批量审阅 UI
- **涉及章节**：§16.4
- **工作内容**：
  - 审阅面板（分类视图、置信度过滤滑块、批量确认/拒绝）
  - 快捷键支持（A/R/→）
  - diff 视图（本章增量）
  - evidence 悬停高亮
- **估算**：前端 3d
- **关键依赖**：M2.2（KG 数据）
- **验收**：能按类型/置信度筛选并批量审阅 KG 事实

### M2.4 Context Pack 增强 + 规则引擎校验
- **涉及章节**：§8.2, §12.1
- **工作内容**：
  - Context Pack 分区预算（System 5~10% / Long-term 10~15% / KG+Lore 15~25% / Recent ≥50%）
  - 溢出回流策略
  - 4 类规则引擎校验（角色状态/时间线/持有物/线索状态）
  - n-gram 重复检测
  - 校验结果展示（severity + evidence 定位）
- **估算**：后端 3d + 前端 2d = 5d
- **关键依赖**：M2.2（KG 数据）
- **验收**：能检测已死亡角色出场、时间线矛盾等；校验结果含 evidence 定位

### M2.5 字数控制（中约束）
- **涉及章节**：§11.2
- **工作内容**：
  - 场景预算分配（场景卡 target_chars）
  - 生成后字数检测 + 扩写/压缩 API
- **估算**：后端 1d + 前端 1d = 2d
- **验收**：单章字数误差 ≤±15%

**MVP-β 总计：~21 工作日（含缓冲 ≈ 2~3 周）**

---

## Phase 3: v1（稳定创作）

### M3.1 LLM 语义一致性校验
- **涉及章节**：§12.2
- **内容**：设定矛盾 + 视角漂移的 LLM 检测；校验输出含 confidence/source

### M3.2 工作流引擎
- **涉及章节**：§14
- **内容**：JSON DAG 解析 + 拓扑排序 + asyncio 并行执行 + SQLite 状态机；5 个预定义 handler

### M3.3 版本/快照/Checkpoint
- **涉及章节**：§13
- **内容**：场景版本管理；章节快照；命名 checkpoint

### M3.4 字数强约束（Streaming Gate）
- **涉及章节**：§11.2
- **内容**：soft/hard limit + 句号边界检测 + 多轮续写状态机

### M3.5 sqlite-vec 向量检索
- **涉及章节**：§6.3
- **内容**：按段落切分 embedding（BGE-small-zh）；检索注入 Context Pack

### M3.6 Prompt Workshop
- **涉及章节**：§6.1 prompts 表
- **内容**：提示词模板版本化管理

---

## Phase 4: v2（差异化能力）

### M4.1 可视化时间线 + 线索管理器
### M4.2 风格指纹与偏离报告
### M4.3 Qdrant 高性能向量检索
### M4.4 分支试写与合并
### M4.5 用户自定义工作流（Python DSL + 沙箱）
### M4.6 Lore 自动维护 Agent

---

## 对齐检查

| 规格书章节 | 覆盖里程碑 | 状态 |
|-----------|-----------|------|
| §1 产品定位 | 全局 | ✅ 用户画像已明确 |
| §2 设计原则 | 全局 | ✅ 贯穿所有模块 |
| §3 用户旅程 | M1.1~M2.5 | ✅ MVP 覆盖核心旅程 |
| §4 信息架构 | M1.1 | ✅ |
| §5 系统架构 | M1.1, M1.3 | ✅ |
| §6 数据设计 | M1.1, M2.2, M3.5 | ✅ |
| §7.1 Bible | M1.2 | ✅ |
| §7.2 Lorebook | M2.1 | ✅ |
| §7.3 KG | M2.2, M2.3 | ✅ |
| §7.4 记忆系统 | M1.4 | ✅ |
| §8 Context Pack | M1.3, M2.4 | ✅ |
| §9 写作流水线 | M1.3, M2.4, M3.2 | ✅ |
| §10 Schema-first | M1.3, M2.2 | ✅ |
| §11 字数/风格 | M2.5, M3.4, M4.2 | ✅ |
| §12 一致性校验 | M2.4, M3.1 | ✅ |
| §13 版本/快照 | M3.3 | ✅ |
| §14 工作流引擎 | M3.2 | ✅ |
| §15 API 规格 | M1.1~M2.5 | ✅ |
| §16 前端设计 | M1.1~M2.3 | ✅ |
| §17 部署 | M1.1 | ✅ |
| §18 安全隐私 | 全局 | ✅ |
| §19 许可合规 | 全局 | ✅ |
| §20 迭代路线 | Phase 1~4 | ✅ |

**对齐结果：规格书所有章节均有对应里程碑覆盖。**
