# 中文长篇小说 AI 写作平台（本地拉起 Web 版）设计与规格 v0.1

> 文档目的：把“中文长篇小说 AI 写作平台”的产品设计与工程规格落到可执行的 Markdown 规格书，便于后续研发、拆分任务、溯源参考。
>
> 运行形态：**本地拉起（Local-first）**，浏览器访问（例如 `http://localhost:3100`），数据默认保存在本机（SQLite/文件），可选本机 Neo4j/Qdrant 等扩展服务。
>
> 更新日期：2026-02-20

---

## 0. 参考实现与设计溯源

本规格书的若干关键机制，借鉴并融合了以下开源实现与写作工具设计（按与本项目相关度排序）：

- **NovelForge**：Schema-first 卡片化创作、`@DSL` 精准上下文引用、Neo4j 知识图谱一致性、字段粒度流式生成、代码式工作流系统与 Workflow Agent  
  - Repo：<https://github.com/RhythmicWave/NovelForge>  
  - 工程规则：<https://raw.githubusercontent.com/RhythmicWave/NovelForge/main/rules/novelforge-engineering-rule.md>  
  - 后续规划（含“选项式回复”“章节字数约束”思路）：<https://raw.githubusercontent.com/RhythmicWave/NovelForge/main/%E5%90%8E%E7%BB%AD%E8%A7%84%E5%88%92.md>  
- **Aventuras**：长篇记忆系统（章节自动总结、token 阈值、检索注入）、Lorebook（关键词/相关度注入、别名、隐藏信息）、动态状态追踪、命名 checkpoint/回滚、OpenAI 兼容自定义端点  
  - Repo：<https://github.com/AventurasTeam/Aventuras>  
  - 项目特性页：<https://aventuras.ai/pages/features>  
  - DeepWiki（记忆/检索分层设计）：<https://deepwiki.com/aleph23/Aventuras/3.6-memory-and-chapter-system>、<https://deepwiki.com/aleph23/Aventuras/5.4-memory-and-retrieval-systems>  
- **gemini-writer**：自主写作 agent 的“恢复模式（Recovery）”“上下文压缩（Context Compression）”“工具调用式工作循环（agentic loop）”  
  - Repo：<https://github.com/Doriandarko/gemini-writer>  

另外，平台的“写作组织形态/规划方法论/资料注入机制”参考了以下产品/文档：

- **Sudowrite Story Bible**：把项目设定集中为“持久化的故事圣经（Bible）”，并明确各字段会影响后续生成（例如 Prose Generation 受 Style/Characters/Scenes 影响）  
  - 文档：<https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/what-is-story-bible/jmWepHcQdJetNrE991fjJC>  
  - Tips（强调一致性对生成质量的影响）：<https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/tips--tricks/eBjBne7foMi8uYFxWEPCai>  
- **SillyTavern World Info（Lorebook）**：把世界信息做成“动态词典”，按关键词触发注入 prompt；并提供预算/逻辑等更复杂机制  
  - 官方文档：<https://docs.sillytavern.app/usage/core-concepts/worldinfo/>  
  - 文档仓库说明（动态词典比喻）：<https://github.com/SillyTavern/SillyTavern-Docs/blob/main/Usage/worldinfo.md>  
  - DeepWiki（预算/激活逻辑等）：<https://deepwiki.com/SillyTavern/SillyTavern/6.1-world-info-system>  
- **NovelAI Lorebook**：支持更复杂的 key 触发逻辑（例如 `&` 表示多个 key 同时出现才触发）  
  - 文档：<https://docs.novelai.net/en/text/lorebook>  
- **Plottr 时间线/场景卡**：Timeline 作为“可视化枢纽”，按章节/场景卡组织剧情并可过滤角色/地点/标签  
  - Timeline Overview：<https://docs.plottr.com/article/54-timeline-overview>  
  - Series View：<https://docs.plottr.com/article/65-timeline-series-view>  
- **yWriter**：强调“以场景为基本单位”并支持拖拽重排、字数统计  
  - yWriter5 Guide（场景/章节管理）：<https://www.spacejock.com/files/yWriter5Guide.pdf>  
  - yWriter7 网站（为什么以场景为核心）：<https://www.spacejock.com/yWriter7.html>  
- **Scrivener Corkboard**：索引卡式组织、自由拖拽重排，适合作为“场景卡 UI”参考  
  - Literature & Latte 博客：<https://www.literatureandlatte.com/blog/how-to-use-scriveners-freeform-corkboard>  
- **Manuskript**：雪花写作法（Snowflake Method）+ 人物/地点/事件笔记追踪  
  - 官网：<https://www.theologeek.ch/manuskript/>  

---

## 1. 产品定位与目标

### 1.1 产品定位

一个面向中文长篇小说的 **”AI 写作 IDE（本地 Web 版）”** [DR-012: “百万字长篇”实际用户需求验证](dr/dr-012-million-word-demand-validation.md)：

- 写作主线：**章 → 场景（Scene）→ 段落（Paragraph）** 的可控生成与编辑
- 一致性主线：**故事圣经（Bible）+ Lorebook + 知识图谱（KG）+ 摘要/检索记忆** 的多层记忆体系
- 工程主线：**Schema-first 结构化生成 + 可回溯审阅 + 工作流自动化 + 版本/分支**，把“写作”当作可迭代工程系统

> 注：之所以强调“IDE”，是因为仅有“生成器”不足以支撑百万字长篇的迭代、返工、改设定、回溯、复用与一致性治理。

### 1.2 北极星指标（North Star）

- **连续创作效率**：作者在“下一章/下一场景”上卡住的次数下降
- **一致性缺陷率**：穿帮/设定冲突/时间线冲突在生成后被自动发现并可快速定位修复
- **可控性**：单章目标字数误差可稳定在阈值内（例如 ±10%）
- **可回溯性**：任何图谱事实、Lore 条目、摘要更新均可追溯来源（证据段落、时间、变更者）

### 1.3 非目标（v0～v1）

- 不做联网账号体系/云同步（可后续扩展）
- 不做复杂多人协作（可以“本地多用户/共享只读”作为后续）
- 不把 AI 结果当“最终稿”：平台目标是“可控生成 + 可编辑 + 可治理”

---

## 2. 核心设计原则

1) **资产化**：设定、角色、地点、线索、事件、场景都必须可结构化沉淀、可引用、可检索。  
2) **多层记忆**：文本层（正文）+ 摘要层（章摘要/主线摘要）+ 结构层（KG/Lore）共同保证一致性（Aventuras 的章节总结/检索注入、Lorebook 设计可直接借鉴）。  
3) **Schema-first**：对 AI 输出建立“结构约束 + 校验闭环”，避免“看起来像”但难落地（NovelForge 的 Schema-first 卡片创作与字段粒度生成是关键参考）。  
4) **可回溯/可撤销**：图谱抽取、摘要更新、风格指纹更新等都必须有证据与版本，支持回滚（Aventuras 的命名 checkpoint + retry 很值得借鉴）。  
5) **事件驱动 + 插件化**：跨模块联动用事件总线；工作流节点/处理器采用装饰器注册（参考 NovelForge Engineering Rule）。  
6) **本地优先**：项目数据默认本地落盘；对外部 LLM 调用尽量支持 OpenAI-compatible 自定义端点，便于接入本地模型或第三方（Aventuras 明确支持自定义 OpenAI-compatible 端点）。  

---

## 3. 用户旅程（User Journey）

### 3.1 从 0 到 1：建项目 → 生成骨架 → 开写

1. 创建项目（选择题材模板 / 空白）
2. 生成/填写 Story Bible：
   - 题材、叙事视角、时态、文风、主线梗概、人物表、世界观规则

3. 生成大纲：
   - 书级梗概 → 卷/章级梗概 → 场景列表（每场景字数预算）
   - 新出场人物画像
   - 故事线大纲
4. 写作主线：
   - 从“场景卡”逐个生成正文，并可局部润色/扩写/重写
5. 每章完成自动触发：
   - 章节摘要 → 线索更新 → 图谱抽取（审阅后入库）→ 下一章建议/大纲
   - 一致性校验

### 3.2 中期常见需求：改设定 → 全书一致性修复

- 作者修改 Bible/Lore/KG（例如人物背景、关系变更）
- 系统提供：
  - 影响分析（哪些章/场景受影响）
  - 一致性巡检（找冲突点）
  - 半自动修复建议（定位段落 + 建议改写）

### 3.3 后期需求：导出发布

- 导出 Markdown / DOCX / TXT
- 生成章节标题、简介、宣传文案
- 导出“世界观设定集”（Bible + Lore + KG 摘要）

---

## 4. 信息架构与核心概念

### 4.1 项目层级

- **Series**（系列，可选）  
- **Book**（一本书/一部）  
- **Volume**（卷，可选）  
- **Chapter**（章）  
- **Scene**（场景，建议为最小写作单元，参考 yWriter/Scrivener/Plottr 的卡片式管理）  
- **Card**（卡片：可扩展的结构化资产单位，继承 NovelForge 的“模块化卡片”理念）

### 4.2 资产类型（Asset Types）

- Story Bible（故事圣经，持久化设定中心；参考 Sudowrite Story Bible）
- Lorebook Entry（世界条目：人/地/组织/物/概念/事件/规则；参考 Aventuras & SillyTavern）
- Knowledge Graph（知识图谱：实体与关系，带证据与版本；参考 NovelForge 的 Neo4j 一致性）
- Plot Thread（线索/悬念/任务/伏笔：状态 open/partial/resolved）
- Timeline Event（时间线事件：用于防穿帮与 Plottr 类可视化）

### 4.3 “真相源（Source of Truth）”优先级

> 解决“到底听 Bible 还是听正文？”的常见冲突。

1) **显式作者设定**（Bible/Lore 的“作者锁定字段”）  
2) **经作者确认入库的 KG 事实**（有 evidence + approved）  
3) **正文内容（最新版本）**  
4) **AI 推断/抽取但未确认的事实**（仅作为建议）

---

## 5. 系统架构（本地拉起 Web）

### 5.1 组件图（逻辑）

- Web 前端（SPA）：编辑器 + 卡片面板 + 图谱/时间线面板 + AI 控制台
- 后端 API（FastAPI/Node 任一实现均可；本规格以 FastAPI 举例）：
  - Project Service（项目/文本/版本）
  - AI Orchestrator（模型路由、流式输出、结构化校验）
  - Memory Service（摘要、检索、上下文拼装）
  - Lorebook Service（条目管理、触发注入）
  - Graph Service（抽取、审阅、入图、查询）
  - Workflow Engine（事件驱动工作流，含运行记录）
  - QA Service（一致性巡检、风格偏离）
- 存储：
  - SQLite（必选）
  - Neo4j（可选但推荐；用于 KG 与关系查询/可视化）
  - 向量库（可选：Qdrant/Chroma；用于语义检索召回）

### 5.2 本地部署形态

建议提供两种 profile：

**Lite（轻依赖，最快跑起来）**
- 前端 + 后端 + SQLite
- KG 用 SQLite 的图表（edges/nodes）实现最小可用 [DR-001: SQLite 图表实现 KG 可行性](dr/dr-001-sqlite-graph-feasibility.md)
- 不启用向量库

**Full（推荐）**
- 前端 + 后端 + SQLite + Neo4j（Docker）
- 可选 Qdrant（Docker）
- 支持更强的检索、关系查询与可视化

---

## 6. 数据设计

### 6.1 SQLite（关系数据）核心表

> 命名仅示意，可按团队规范调整。

- `projects`
  - `id`, `name`, `language`, `created_at`, `updated_at`
- `books`
  - `id`, `project_id`, `title`, `genre`, `status`
- `chapters`
  - `id`, `book_id`, `index`, `title`, `target_chars`, `status`, `created_at`, `updated_at`
- `scenes`
  - `id`, `chapter_id`, `index`, `title`, `summary`, `target_chars`, `status`
- `scene_text_versions`
  - `id`, `scene_id`, `version`, `content_md`, `char_count`, `created_at`, `created_by`
- `bible_fields`
  - `id`, `project_id`, `key`, `value_md`, `locked`(bool), `updated_at`
- `lore_entries`
  - `id`, `project_id`, `type`, `title`, `aliases_json`, `content_md`, `secrets_md`, `triggers_json`, `priority`, `locked`
- `plot_threads`
  - `id`, `project_id`, `title`, `status`, `first_seen_chapter`, `last_update_chapter`, `notes_md`
- `chapter_summaries`
  - `chapter_id`, `summary_md`, `keywords_json`, `entities_json`, `plot_threads_json`, `in_story_time_json`, `created_at`
- `kg_proposals`（抽取候选，待审阅）
  - `id`, `chapter_id`, `payload_json`, `status`(pending/approved/rejected), `created_at`
- `workflow_runs`
  - `id`, `project_id`, `workflow_key`, `status`, `input_json`, `output_json`, `logs_md`, `created_at`, `updated_at`
- `prompts`
  - `id`, `project_id`, `group`, `key`, `template_md`, `version`, `enabled`

### 6.2 知识图谱（Neo4j 推荐 schema）

参考 NovelForge “知识图谱一致性”理念（Neo4j + 动态信息），并结合长篇小说领域需求。

**节点（Nodes）**
- `Character`：人物（含别名）
- `Location`：地点
- `Organization`：组织/势力
- `Item`：物品/道具
- `Event`：事件（剧情发生）
- `PlotThread`：线索（open/closed）
- `Chapter` / `Scene`（作为证据锚点，建议至少保留 `Chapter`）

**关系（Edges）**
- `APPEARS_IN`（Character→Chapter/Scene）
- `LOCATED_IN`（Event→Location）
- `PARTICIPATES_IN`（Character→Event）
- `OWNS`（Character→Item）
- `RELATIONSHIP`（Character↔Character，可用 `type` 属性描述 ally/enemy/love/hate 等）
- `CAUSES` / `LEADS_TO`（Event→Event 因果）
- `FORESHADOWS` / `RESOLVES`（PlotThread↔Event）

**关键属性（强制）**
- `first_seen_chapter`, `last_updated_chapter`
- `confidence`（抽取置信）
- `evidence`（证据：`chapter_id` + `quote`/`paragraph_ref`）
- `status`（例如角色 alive/dead；线索 open/resolved）
- `source`（system_extraction / user_edit）

> 为什么必须 `evidence`：没有证据，图谱会因抽取误差逐渐污染，且无法回溯修正。
>
> [DR-004: Neo4j evidence 存储性能](dr/dr-004-neo4j-evidence-performance.md)：小说 KG 规模下性能问题不大，但建议 Neo4j 只存轻量引用指针，完整 quote 存 SQLite，支持反向查询。

### 6.3 向量检索（可选） [DR-008: 向量检索的必要性与成本](dr/dr-008-vector-search-necessity.md)

借鉴 SillyTavern 的“向量存储 + 世界信息 + Personas”并行增强上下文的思路（SillyTavern DeepWiki 总览）。  
- 向量库主要用于：召回“相似场景”“伏笔回指”“过去提过但没结构化入图的描写”。  
- 图谱负责“事实/关系”，向量负责“语义/氛围/隐含线索”。

---

## 7. 核心能力规格

### 7.1 Story Bible（故事圣经）

参考 Sudowrite：Story Bible 是持久化的“项目设定中心”，不同字段会影响后续生成。  
建议 Bible 最小字段（MVP）：

- `Genre`（题材/风格流派）
- `Style`（文风与禁忌）
- `POV`（视角：第一/第三/多视角；是否允许切换）
- `Tense`（时态：过去/现在）
- `Synopsis`（主线梗概）
- `Characters`（主角/重要配角概要）
- `World Rules`（世界规则：魔法/科技/社会规则等）
- `Outline`（书级/卷级大纲）
- `Scenes`（当前章/场景列表，作为生成输入）

> 关键产品点：每个字段要支持 “手写 / AI 生成 / 指令重写”，并有 `locked` 开关，锁定后作为硬约束注入 prompt。

一致性提醒：Sudowrite 文档明确提到：Prose Generation 会看 Style/Characters/Scenes，若这些字段不一致会导致生成困惑，需要维护一致性。  
（详见 Sudowrite Tips & Tricks）

### 7.2 Lorebook（世界条目库）

参考 Aventuras：统一条目系统（人物/地点/物品/派系/概念/事件）、别名、隐藏信息、关键词与相关度注入、导入导出。  
参考 SillyTavern：World Info 像“动态词典”，只在关键词出现时注入条目内容；标题/关键词不直接入 prompt，因此条目内容要自洽完整。  
参考 NovelAI：更复杂 key 规则（`&` 等）。

**条目字段建议**
- `type`：Character/Location/Item/Concept/Rule/Organization/Event
- `title`
- `aliases[]`
- `content_md`（可注入 prompt 的主体内容）
- `secrets_md`（作者私密，不注入；或在某些模式下注入）
- `triggers`：
  - `keywords[]`（简单触发）
  - `and_keywords[]`（满足多个关键词才触发，参考 NovelAI `&`）
  - `regex[]`（高级，非 MVP）
- `priority`（当预算不足时的排序权重）
- `cooldown/sticky`（可选：参考 SillyTavern 的时间效果/预算逻辑）

**注入策略（必做）**
- 预算：Lorebook 注入有 token/字符预算（例如总上下文的 10%～20%），超出则按 `priority`、相关度排序截断 [DR-005: Lorebook 触发注入的预算截断策略](dr/dr-005-lorebook-budget-strategy.md)
- 触发：关键词命中（正文/大纲/当前输入）→ 候选条目集合
- 合并：对同一实体的多个条目做 merge 或选择“最新且锁定的版本”

### 7.3 知识图谱（KG）

**写完一章/场景 → 抽取 → 审阅 → 入图 → 下次生成引用**  
参考 NovelForge“写完入图、后续生成靠图谱保持一致性”的核心理念。

**抽取输出格式必须结构化（Schema-first）**
- 角色实体（含别名）
- 事件（含时间、地点、参与者、结果）
- 关系变化（角色关系、持有物、线索状态）
- 每条事实都要附 evidence（引用原文段落/句子）

**审阅与回滚（必做）**
- 系统先产出 `kg_proposals`（pending）
- UI 展示差异（diff）：新增/更新/删除
- 用户确认后才 `approved → upsert Neo4j` [DR-009: KG 抽取审阅流程与用户负担](dr/dr-009-kg-review-ux-burden.md)：建议改为置信度分级自动入库 + 事后修正，降低用户审阅负担。
- 支持“一键撤销本次入图”（回滚到上一版 KG）

### 7.4 章节记忆系统（Summaries + Retrieval）

参考 Aventuras：
- 自动章节总结（管理上下文窗口）
- token 阈值与 chapter buffer（决定保留多少原文、多少摘要）
- AI 检索相关 past events（生成时检索注入）
- 章节元数据跟踪（关键词、角色、地点、线索）
- 叙事时间跟踪（years/days/hours/minutes）

本平台建议实现：

- `Chapter Summary`：每章完成后生成 1～2 段摘要 + 关键事件列表
- `Rolling Summary`：全书滚动摘要（每写 3～5 章刷新一次）
- `Open Threads List`：未解线索清单（状态机）
- `Entity Changes`：本章新增/变化的角色状态、关系变化（用于 KG 与一致性校验）
- `Retrieval`：写下一章/场景时，从 KG + Lore + 摘要 +（可选向量库）检索**仅相关**信息注入

---

## 8. 上下文拼装（Context Pack Builder）

### 8.1 目标

在不爆 token 的情况下，提供“足够一致性约束 + 足够短期上下文”，让模型写得连贯。

### 8.2 Context Pack 分层（推荐默认顺序）

[DR-002: 上下文 token 预算分配策略](dr/dr-002-context-token-budget.md)：参考 SillyTavern/NovelAI 的成熟分区预算系统，建议系统约束 5~10%、长期记忆 10~15%、KG+Lore 15~25%、短期上下文 ≥50%。

1) **系统约束（固定）**  
- 写作语言：中文
- 风格卡（Style）
- POV/时态
- 禁忌列表（不用词、避免的叙事方式等）

2) **长期记忆（压缩）**  
- Rolling Summary（主线滚动摘要）
- 当前阶段目标（本章要推进什么）
- 未解线索 Top-K

3) **结构化事实（精准注入）**  
- 本章涉及角色：身份/动机/关系网（KG 1～2 跳邻居）
- 相关地点/组织/关键规则：从 Lorebook 注入
- 相关事件回顾：从章摘要/向量库召回（只取相关）

4) **短期上下文（原文）**  
- 上一场景末尾 N 段
- 当前场景已写内容（用于续写）

### 8.3 Lorebook 与 KG 的协同

- KG 输出“事实”（关系、持有物、状态变化）
- Lorebook 输出“描述性设定”（外貌、口癖、文化、禁忌、氛围）
- 同一实体优先级：Bible 锁定 > KG approved > Lore locked > 正文抽取

---

## 9. 写作流水线（章节/场景工作流）

### 9.1 标准工作流（Chapter Pipeline）

> 借鉴 NovelForge 的“工作流系统（代码式工作流 + Agent）”形态，把创作过程自动化并可复用。

**阶段 0：规划输入（手工/AI）**
- 输入：本章目标、线索推进、出场角色、字数目标
- 输出：场景卡列表（含字数预算）

**阶段 1：生成场景卡（结构化）**
- 输出字段：`location`, `time`, `characters`, `conflict`, `turning_point`, `reveal`, `target_chars`

**阶段 2：分场景生成正文（流式）**
- 每场景独立生成，生成后立即测字数
- 允许“多候选 A/B/C”（参考 NovelForge 规划中的“选项式回复”）

**阶段 3：章节整合与润色**
- 合并场景 → 统一语气/衔接/节奏
- 自动检测视角漂移、重复句式（可参考 Aventuras 的风格重复分析）

**阶段 4：字数校正**
- 轻约束：提示词引导
- 中约束：按场景预算扩写/压缩
- 强约束：流式接收时分段计数、达到阈值中断再续写（NovelForge 后续规划给出了类似思路）

**阶段 5：抽取与入库**
- 章节摘要
- Lore 更新建议（可选：自动生成候选条目）
- KG 抽取 → 审阅 → 入库

**阶段 6：一致性校验**
- 用“校验 agent”对照 Bible/Lore/KG 检查冲突
- 输出：冲突列表（带证据定位 + 修复建议）
- 用户修复后可重跑阶段 5～6

### 9.2 工作流触发器（Triggers）

- `scene_saved` → 更新短期检索索引
- `chapter_mark_done` → 触发（摘要 → 抽取 → 入库 → 校验）
- `bible_updated`/`lore_updated`/`kg_updated` → 触发一致性巡检（可选手动）

---

## 10. Schema-first：结构化输出规范 [DR-011: FastAPI 流式输出与结构化校验兼容性](dr/dr-011-fastapi-sse-json-validation.md)

### 10.1 场景卡 JSON Schema（示例）

> 实际工程中建议把 Schema 作为“动态输出模型”存储（参考 NovelForge 的动态输出模型理念），并可在 UI 中编辑/版本化。

```json
{
  "$id": "scene_card_v1",
  "type": "object",
  "required": ["title", "location", "time", "characters", "conflict", "turning_point", "target_chars"],
  "properties": {
    "title": {"type": "string"},
    "location": {"type": "string"},
    "time": {"type": "string", "description": "叙事内时间，如'第三天傍晚'"},
    "characters": {"type": "array", "items": {"type": "string"}},
    "conflict": {"type": "string"},
    "turning_point": {"type": "string"},
    "reveal": {"type": "string"},
    "target_chars": {"type": "integer", "minimum": 200, "maximum": 5000}
  }
}
```

### 10.2 KG 抽取 JSON Schema（示例）

```json
{
  "$id": "kg_extraction_v1",
  "type": "object",
  "required": ["chapter_id", "entities", "relations", "events"],
  "properties": {
    "chapter_id": {"type": "string"},
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "name", "aliases", "evidence"],
        "properties": {
          "type": {"type": "string", "enum": ["Character", "Location", "Organization", "Item", "PlotThread"]},
          "name": {"type": "string"},
          "aliases": {"type": "array", "items": {"type": "string"}},
          "evidence": {
            "type": "object",
            "required": ["quote", "scene_id"],
            "properties": {
              "quote": {"type": "string"},
              "scene_id": {"type": "string"}
            }
          }
        }
      }
    },
    "events": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "time", "location", "participants", "result", "evidence"],
        "properties": {
          "name": {"type": "string"},
          "time": {"type": "string"},
          "location": {"type": "string"},
          "participants": {"type": "array", "items": {"type": "string"}},
          "result": {"type": "string"},
          "evidence": {"type": "object", "properties": {"quote": {"type": "string"}, "scene_id": {"type": "string"}}}
        }
      }
    },
    "relations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["from", "to", "relation_type", "delta", "evidence"],
        "properties": {
          "from": {"type": "string"},
          "to": {"type": "string"},
          "relation_type": {"type": "string"},
          "delta": {"type": "string", "description": "新增/变化/删除/状态改变"},
          "evidence": {"type": "object", "properties": {"quote": {"type": "string"}, "scene_id": {"type": "string"}}}
        }
      }
    }
  }
}
```

---

## 11. 字数与风格控制（实现策略）

### 11.1 字数口径

- 默认统计：**中文字符数（含中文标点）**  
- 可配置：是否计入空格、英文、数字、标点

### 11.2 字数控制的三档模式

参考 NovelForge 后续规划对“章节正文字数约束”的两种思路（工具调用计数 vs 流式中断计数），落地为三档：

1) **轻约束（Prompt-only）**  
- 在 prompt 中声明目标字数  
- 优点：实现最简单  
- 缺点：不稳定

2) **中约束（Scene Budget）**（推荐默认）  
- 先生成场景列表并分配字数预算（如 6 场景，每场景 700～900）  
- 场景生成后自动测字数：超出则压缩/不足则扩写  
- 优点：体验好、成本可控、可解释

3) **强约束（Streaming Gate）**（高级） [DR-003: 字数控制强约束的工程复杂度](dr/dr-003-streaming-gate-complexity.md)  
- 流式输出时分段计数，达到阈值就中断并把“已写字数/剩余字数”回喂继续生成  
- 优点：最精确  
- 缺点：工程复杂，需要稳健状态机与中断恢复

### 11.3 风格一致性

借鉴 Sudowrite 的“Style 影响 Prose”与 Aventuras 的“重复词/短语风格分析”。

建议实现：

- **风格卡（Style Card）**（作者可编辑、可锁定）
  - 叙事人称、语气、句长倾向、对话比例、禁用词、常用修辞等
- **风格指纹（Style Fingerprint）**（系统自动）
  - 从已写章节统计：句长分布、口癖词、连接词偏好、标点密度等
- **风格偏离报告**
  - 每章生成后给出偏离项（例如“本章平均句长显著变短”“第一人称突然切到第三人称”）

---

## 12. 一致性校验（QA） [DR-006: 一致性校验的自动化程度](dr/dr-006-consistency-check-automation.md)

### 12.1 校验项清单（MVP）

- **设定冲突**：正文与 Bible/Lore/KG approved 冲突  
- **时间线冲突**：同一事件顺序、日期推进矛盾（参考 Aventuras 的 in-story time tracking）  
- **角色状态冲突**：已死亡角色出场、持有物不一致  
- **线索状态冲突**：已 resolved 的线索又以“未知”形式出现  
- **视角漂移**：POV 未允许切换却出现切换  
- **重复表达/口癖失控**：连续重复词/句式（参考 Aventuras 的 style analysis）

### 12.2 校验输出（规范）

- 每条问题必须包含：
  - `type`（冲突类型）
  - `severity`（high/medium/low）
  - `evidence`（引用段落）
  - `expected`（应符合的设定/事实）
  - `suggest_fix`（改写建议）

---

## 13. 版本、快照与分支试写

参考 Aventuras 的 “Named checkpoints + retry system”。

建议实现：

- **场景版本**：每次生成/大改动生成一个 version
- **章节快照**：章完成时自动打 snapshot（可回滚）
- **命名 checkpoint**：作者手动保存“关键节点”（如第 50 章完成）
- **分支试写**：
  - 对某个场景/章节生成多分支（A/B 结局）
  - 可合并回主线（选择某个分支为主）

---

## 14. 工作流系统（Workflow Engine）

### 14.1 为什么必须有工作流

长篇写作不是“生成一次就结束”，而是大量固定流程（总结、抽取、入库、校验、导出）反复执行。  
NovelForge 已验证“工作流系统 + Workflow Agent”对创作自动化价值巨大。

### 14.2 工作流 DSL（建议） [DR-007: 工作流 DSL 的解析与执行引擎](dr/dr-007-workflow-dsl-engine.md)

可参考 NovelForge 的“代码式工作流”方向（Python 风格语句 + 特殊标记），但本项目可先用 JSON/YAML 编排，后续再演进到 DSL。

工作流必须支持：
- 触发器（事件驱动）
- 后台运行可见性（全局状态栏/进度）
- 节点级进度
- 暂停/恢复
- 运行日志与产物可回放

### 14.3 工程规则（强约束）

直接借鉴 NovelForge Engineering Rule 的关键条款：
- 事件驱动优先（跨域联动禁止硬调用链）
- 插件化注册（装饰器注册节点/处理器）
- 配置集中管理（禁硬编码）
- 工作流代码修改必须走 parse/validate 闭环后才能应用

---

## 15. API 规格（概要）

> 本地单机为主，默认不做复杂鉴权；若支持局域网共享，可加简单 token。

### 15.1 项目与内容

- `POST /api/projects`
- `GET /api/projects/{id}`
- `POST /api/books`
- `POST /api/chapters`
- `POST /api/scenes`
- `POST /api/scenes/{id}/versions`（保存版本）

### 15.2 Bible / Lore

- `GET /api/bible`
- `PUT /api/bible/{key}`
- `GET /api/lore`
- `POST /api/lore`
- `PUT /api/lore/{id}`
- `POST /api/lore/import`（支持 SillyTavern/JSON/YAML，参考 Aventuras 的导入导出能力）

### 15.3 AI 生成与流式 [DR-011: FastAPI 流式输出与结构化校验兼容性](dr/dr-011-fastapi-sse-json-validation.md)

- `POST /api/generate/scene-card`（返回结构化 JSON）
- `POST /api/generate/scene-draft`（SSE/WebSocket 流式输出）
- `POST /api/generate/rewrite`（润色/扩写/缩写）
- `POST /api/generate/plan-next`（下一章建议/大纲）

### 15.4 抽取/校验/入图

- `POST /api/extract/chapter-summary`
- `POST /api/extract/kg` → `kg_proposals`
- `POST /api/kg/proposals/{id}/approve`
- `POST /api/kg/proposals/{id}/reject`
- `POST /api/qa/check`（一致性巡检）

### 15.5 工作流

- `GET /api/workflows`
- `POST /api/workflows/run`
- `GET /api/workflows/runs/{id}`
- `POST /api/workflows/runs/{id}/stop`
- `POST /api/workflows/runs/{id}/resume`

---

## 16. 前端设计（本地 Web IDE）

### 16.1 布局（建议）

- 左侧：项目树（Book → Chapter → Scene → Cards）
- 中间：编辑器（场景正文 / 章节整合）
- 右侧：多标签面板
  - Bible
  - Lorebook
  - 图谱（关系网）
  - 时间线（Plottr 风格）
  - 线索（Plot Threads）
  - AI 控制台（对话/提示词/工作流运行）

> 场景卡 UI 可参考 Scrivener Corkboard 与 Plottr Timeline 的“卡片+拖拽重排”体验。

### 16.2 关键交互

- 场景卡拖拽排序（以场景为主单位，参考 yWriter “scene-first” 理念）
- 右键选中文本 → “润色/扩写/缩写/换风格”（局部编辑）
- 生成候选 A/B/C → 一键选择作为当前版本（参考 NovelForge 规划“选项式回复”）
- KG 入库前差异审阅（diff）+ evidence 展示

---

## 17. 本地部署与运行（建议提供 Docker Compose）

### 17.1 docker-compose（示例骨架）

> 实际端口/镜像按实现调整；此处是给研发/运维一个可讨论的起点。

```yaml
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DB_URL=sqlite:////data/app.db
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=neo4j_password
      - VECTOR_ENABLED=true
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./data:/data
    depends_on:
      - neo4j
      - qdrant

  web:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - api

  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/neo4j_password
    volumes:
      - ./data/neo4j:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - ./data/qdrant:/qdrant/storage
```

### 17.2 LLM Provider 配置

- 支持 OpenAI-compatible endpoint（参考 Aventuras 的 “Custom API endpoints” 能力）
- 本地密钥存储建议：
  - `.env` + 本机 keyring（可选）
  - 前端不落明文 key（由后端代理调用）

---

## 18. 安全与隐私（本地优先）

- 默认不上传正文/设定（除非调用外部 LLM）
- 提供“脱敏模式”（可选）：把专有名词替换为占位符再发给外部模型（高级）
- 运行日志不包含 API key
- 导出时允许“一键打包项目”（含 db + assets + 配置但不含 key）

---

## 19. 许可与合规提醒

你提供的三个参考仓库中：
- NovelForge 与 Aventuras 均为 **AGPL-3.0**（网络服务/修改分发需注意义务；具体以其 LICENSE 为准）
- gemini-writer 为 **MIT + Attribution Requirement**（商用需署名，具体以其 LICENSE 为准）

若你计划闭源商用，建议“借鉴设计与机制，不直接复制 AGPL 代码”，或与作者协商商业授权。

---

## 20. 迭代路线（建议）

### MVP（4～6 周可用目标） [DR-010: MVP 时间表可行性](dr/dr-010-mvp-timeline-feasibility.md)
- 场景卡 + 章节/场景编辑器
- 风格卡 + 字数目标（中约束：场景预算）
- Story Bible（核心字段）
- 章节摘要（自动）
- Lorebook（关键词触发注入）
- KG 抽取候选 + 审阅入库（Lite：SQLite 图；Full：Neo4j）
- 导出 Markdown/TXT

### v1（稳定创作）
- 一致性校验（设定/时间线/角色状态）
- 工作流引擎（章完成自动跑流水线）
- 版本/快照/命名 checkpoint
- Prompt Workshop（提示词版本化）

### v2（差异化能力）
- 可视化时间线（Plottr 风格）+ 线索管理器
- 风格指纹与偏离报告
- 语义检索（向量库）
- 分支试写与合并
- Lore 自动维护 agent（参考 Aventuras 的 autonomous lore agent）

---

## 21. 附录：引用链接汇总

> 便于统一溯源与快速打开。

- NovelForge：<https://github.com/RhythmicWave/NovelForge>  
- NovelForge Engineering Rule：<https://raw.githubusercontent.com/RhythmicWave/NovelForge/main/rules/novelforge-engineering-rule.md>  
- NovelForge 后续规划：<https://raw.githubusercontent.com/RhythmicWave/NovelForge/main/%E5%90%8E%E7%BB%AD%E8%A7%84%E5%88%92.md>  
- Aventuras：<https://github.com/AventurasTeam/Aventuras>  
- Aventuras Features：<https://aventuras.ai/pages/features>  
- Aventuras DeepWiki（Memory/Chapter）：<https://deepwiki.com/aleph23/Aventuras/3.6-memory-and-chapter-system>  
- Aventuras DeepWiki（Retrieval）：<https://deepwiki.com/aleph23/Aventuras/5.4-memory-and-retrieval-systems>  
- gemini-writer：<https://github.com/Doriandarko/gemini-writer>  
- Sudowrite Story Bible：<https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/what-is-story-bible/jmWepHcQdJetNrE991fjJC>  
- Sudowrite Tips & Tricks（一致性影响生成）：<https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/tips--tricks/eBjBne7foMi8uYFxWEPCai>  
- SillyTavern World Info 文档：<https://docs.sillytavern.app/usage/core-concepts/worldinfo/>  
- SillyTavern-Docs（World Info 说明）：<https://github.com/SillyTavern/SillyTavern-Docs/blob/main/Usage/worldinfo.md>  
- SillyTavern DeepWiki（World Info System）：<https://deepwiki.com/SillyTavern/SillyTavern/6.1-world-info-system>  
- NovelAI Lorebook 文档：<https://docs.novelai.net/en/text/lorebook>  
- Plottr Timeline Overview：<https://docs.plottr.com/article/54-timeline-overview>  
- Plottr Series View：<https://docs.plottr.com/article/65-timeline-series-view>  
- yWriter5 Guide（PDF）：<https://www.spacejock.com/files/yWriter5Guide.pdf>  
- yWriter7（scene-first 理念）：<https://www.spacejock.com/yWriter7.html>  
- Scrivener Corkboard（官方博客）：<https://www.literatureandlatte.com/blog/how-to-use-scriveners-freeform-corkboard>  
- Manuskript（雪花写作法 + 追踪）：<https://www.theologeek.ch/manuskript/>  

---

> 结束语：这份规格书是”可开工的第一版”。下一步如果你希望继续落地到更工程化的层面，我建议按模块再拆 4 份子规格：
> 1) 数据模型与迁移；2) Context Pack Builder 详细算法；3) 工作流 DSL/节点库；4) 前端 UI/交互稿（页面级）。

---

## 附录 B：深度调研索引（DR Index）

| DR# | 主题 | 类型 | 关联章节 | 核心结论 |
|-----|------|------|---------|----------|
| [DR-001](dr/dr-001-sqlite-graph-feasibility.md) | SQLite 图表实现 KG 可行性 | tech | §5.2 | 双表设计 + 递归 CTE 可覆盖小说 KG 规模；限制 2 跳查询；抽象 GraphService 接口 |
| [DR-002](dr/dr-002-context-token-budget.md) | 上下文 token 预算分配策略 | architecture | §8.2 | 系统约束 5~10%、长期记忆 10~15%、KG+Lore 15~25%、短期上下文 ≥50%；固定基线+弹性溢出 |
| [DR-003](dr/dr-003-streaming-gate-complexity.md) | 字数控制强约束工程复杂度 | tech | §11.2 | MVP 用中约束（场景预算）；强约束排 v1，用 soft/hard limit + 句号边界检测 |
| [DR-004](dr/dr-004-neo4j-evidence-performance.md) | Neo4j evidence 存储性能 | data | §6.2 | 小说 KG 规模下性能无压力；建议 Neo4j 存指针、SQLite 存完整 quote |
| [DR-005](dr/dr-005-lorebook-budget-strategy.md) | Lorebook 触发注入预算截断策略 | architecture | §7.2 | 关键词+别名覆盖 90%+ 触发需求；按 priority DESC 截断，从 Bottom trim |
| [DR-006](dr/dr-006-consistency-check-automation.md) | 一致性校验自动化程度 | tech | §12 | 规则引擎（MVP 4 类结构化检查）+ LLM 推理（v1 语义校验），混合架构 |
| [DR-007](dr/dr-007-workflow-dsl-engine.md) | 工作流 DSL 解析引擎 | architecture | §14.2 | 自建轻量引擎（JSON DAG + Python 装饰器，~500 行），不引入外部引擎 |
| [DR-008](dr/dr-008-vector-search-necessity.md) | 向量检索必要性与成本 | feasibility | §6.3 | MVP 不集成；v1 用 sqlite-vec（零部署）；v2 考虑 Qdrant |
| [DR-009](dr/dr-009-kg-review-ux-burden.md) | KG 抽取审阅 UX 负担 | product | §7.3 | 置信度分级自动入库（High 自动、Medium 待确认、Low 排队），非逐条审阅 |
| [DR-010](dr/dr-010-mvp-timeline-feasibility.md) | MVP 4~6 周时间表可行性 | feasibility | §20 | 单人全量 7 模块需 10~11 周；建议拆 MVP-α（3~4 周）+ MVP-β（+2~3 周） |
| [DR-011](dr/dr-011-fastapi-sse-json-validation.md) | FastAPI 流式输出与结构化校验 | tech | §10, §15.3 | 结构化数据用 Instructor+Pydantic 非流式；正文用 SSE 流式+后置校验 |
| [DR-012](dr/dr-012-million-word-demand-validation.md) | 百万字长篇需求验证 | market | §1.1 | 真实需求但需精准定位；主要面向精品长篇作者，非日更网文作者 |

