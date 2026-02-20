# Change: Add MVP-β Consistency Features

## Why
MVP-α 提供了基本写作能力，但长篇创作的核心痛点——一致性——尚未解决。MVP-β 引入 Lorebook 触发注入、KG 抽取入库、Context Pack 分区预算和规则引擎校验，让作者"写得一致"。

## What Changes
- 新增 Lorebook 条目管理 + 关键词触发注入 + 预算截断
- 新增 KG 抽取（Schema-first）+ 置信度分级自动入库 + 批量审阅 UI
- 增强 Context Pack（分区预算：System/Long-term/KG+Lore/Recent）
- 新增规则引擎一致性校验（4 类结构化检查 + n-gram 重复检测）
- 新增字数中约束（场景预算 + 扩写/压缩）

## Impact
- Affected specs: lorebook, knowledge-graph, context-pack, consistency-check, word-count-control
- Affected code: 新增 Lorebook/KG/QA services + Context Pack 重构 + 前端新面板
- 依赖 MVP-α 完成
- 预估工期：+2~3 周
