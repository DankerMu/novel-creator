# Change: Add v2 Advanced Differentiated Features

## Why
v1 实现了稳定创作体验，v2 引入差异化高级能力——可视化时间线、风格指纹分析、分支试写、用户自定义工作流和 Lore 自动维护 Agent——形成竞争壁垒。

## What Changes
- 新增可视化时间线（Plottr 风格）+ 线索管理器
- 新增风格指纹与偏离报告
- 新增分支试写与合并
- 新增用户自定义工作流（Python DSL + RestrictedPython 沙箱）
- 新增 Lore 自动维护 Agent
- 可选升级 Qdrant 替代 sqlite-vec

## Impact
- Affected specs: timeline-viz, style-analysis, branch-writing, custom-workflow, lore-agent
- 依赖 v1 完成
- 预估工期：+6~8 周
