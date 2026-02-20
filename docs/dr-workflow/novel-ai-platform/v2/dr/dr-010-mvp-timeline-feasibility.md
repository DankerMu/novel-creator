# DR-010: MVP 4~6 周时间表的可行性

## Executive Summary

MVP 包含 7 大模块（场景卡编辑器、Bible、Lorebook、KG 抽取审阅、章节摘要、字数控制、导出），含前后端开发，4~6 周对单人全栈开发者极其紧张（高风险），对 2~3 人小团队可行但需严格裁剪范围。推荐按「核心可用 → 逐步增强」拆分为 2 个子 MVP，首个子 MVP 控制在 3~4 周。

## Research Findings

### 1. 参考项目开发周期

**NovelForge**（GitHub 分析）：
- 主要开发者：1~2 人
- 首个可用版本：约 8~12 周（含 Schema 系统、工作流引擎、KG 集成）
- 技术栈：Python 后端 + Vue 前端 + Neo4j
- 复杂度高于本项目 MVP（包含 DSL 工作流引擎）

**Aventuras**（GitHub 分析）：
- 主要开发者：2~3 人
- 技术栈：Tauri + SvelteKit + Rust
- 首个可用版本：约 6~8 周
- 包含记忆系统、Lorebook、Checkpoint 等

**gemini-writer**：
- 单人开发，CLI 工具
- 首个可用版本：约 2~3 周
- 但功能远少于本项目 MVP

### 2. 模块工作量估算（单人全栈）

| 模块 | 后端 | 前端 | 合计 | 备注 |
|------|------|------|------|------|
| 项目/Book/Chapter/Scene CRUD | 2d | 3d | 5d | 基础骨架 |
| 场景卡编辑器 | 1d | 4d | 5d | 前端重 |
| Story Bible | 1d | 2d | 3d | CRUD + 锁定 |
| Lorebook（关键词触发注入） | 3d | 3d | 6d | 触发逻辑复杂 |
| AI 生成（场景生成 + 流式输出） | 3d | 2d | 5d | SSE + 结构化校验 |
| 上下文拼装（Context Pack） | 3d | 0d | 3d | 核心算法 |
| 章节摘要（自动） | 2d | 1d | 3d | LLM 调用 + 存储 |
| KG 抽取 + 审阅（Lite: SQLite） | 3d | 3d | 6d | 抽取 + diff 审阅 UI |
| 字数控制（中约束） | 1d | 1d | 2d | 场景预算 + 测字数 |
| 导出 Markdown/TXT | 1d | 1d | 2d | 相对简单 |
| **合计** | **20d** | **20d** | **40d** | |

40 工作日 = 8 周（单人），考虑调试/集成/返工系数 1.3x ≈ **10~11 周**。

**结论**：单人 4~6 周完成全部 7 模块不现实。

### 3. AI 辅助开发的加速效果

使用 Claude/Copilot 辅助编码可提升效率：
- CRUD + API 脚手架：提速 2~3x
- 前端组件：提速 1.5~2x
- 复杂业务逻辑（Context Pack、KG 抽取）：提速 1.2~1.5x
- 综合提速系数：约 1.5~2x

考虑 AI 辅助后：40d / 1.7 ≈ **24d ≈ 5 周**（单人，最乐观估计）。

### 4. 推荐拆分：两阶段 MVP

**MVP-α（3~4 周，核心可用）**：
- 项目/Chapter/Scene CRUD + 简单编辑器
- Story Bible（核心字段 CRUD）
- AI 场景生成（流式输出）
- 基础 Context Pack（Bible + 最近文本）
- 章节摘要（自动）
- 导出 Markdown
- **不含**：Lorebook 触发注入、KG 抽取、字数控制

**MVP-β（+2~3 周，特色能力）**：
- Lorebook（关键词触发注入）
- KG 抽取 + 审阅（Lite SQLite 模式）
- 字数控制（中约束：场景预算）
- Context Pack 增强（+ Lorebook + KG）

### 5. 团队规模影响

| 团队规模 | MVP 全量（7 模块） | MVP-α | MVP-α + β |
|---------|------------------|-------|------------|
| 1 人（AI 辅助） | 5~6 周（极紧张） | 3~4 周 | 5~7 周 |
| 2 人（前后端分工） | 3~4 周 | 2~3 周 | 4~5 周 |
| 3 人 | 2~3 周 | 1.5~2 周 | 3~4 周 |

## Impact on Spec

1. §20 的 "MVP 4~6 周" 时间线需要补充团队规模假设
2. 建议将 MVP 拆为 α/β 两阶段，降低交付风险
3. 技术栈选择直接影响时间线——FastAPI + React/Vue 是最主流组合，开发效率最高

## Recommendations

1. **拆分为 MVP-α（3~4 周）和 MVP-β（+2~3 周）**，降低交付风险
2. **明确团队假设**：规格书标注 "1 人全栈 + AI 辅助" 或 "2~3 人小团队"
3. **技术栈锁定**：FastAPI(Python) + React/Next.js(TypeScript) + SQLite，减少技术选型时间
4. **前端用 shadcn/ui 或 Ant Design** 加速 UI 开发
5. **MVP-α 聚焦"能写出来"**，MVP-β 聚焦"写得一致"（Lorebook + KG 是一致性的核心）
6. **AI 辅助开发策略**：脚手架/CRUD/测试用 AI 生成，核心算法（Context Pack、KG 抽取）人工把控

## Sources

- [NovelForge GitHub: 开发历史](https://github.com/RhythmicWave/NovelForge)
- [Aventuras GitHub: 开发历史](https://github.com/AventurasTeam/Aventuras)
- [gemini-writer GitHub](https://github.com/Doriandarko/gemini-writer)
- [AI-assisted Development Productivity Survey (GitHub 2024)](https://github.blog/news-insights/research/survey-ai-wave-of-developer-productivity/)
