# Change: Add v1 Stable Creation Features

## Why
MVP-β 提供了基础一致性能力，但创作流程仍需大量手工操作。v1 引入工作流引擎自动化重复流程、版本管理保障回滚安全、向量检索增强语义召回、LLM 语义校验补充规则引擎盲区。

## What Changes
- 新增 JSON DAG 工作流引擎（自建，~500 行）+ 5 个预定义 handler
- 新增版本/快照/命名 checkpoint
- 新增字数强约束（Streaming Gate：soft/hard limit + 句号边界）
- 新增 sqlite-vec 向量检索集成
- 新增 LLM 语义一致性校验（设定矛盾、视角漂移）
- 新增 Prompt Workshop（提示词版本化）

## Impact
- Affected specs: workflow-engine, version-control, streaming-gate, vector-search, llm-consistency, prompt-workshop
- 依赖 MVP-β 完成
- 预估工期：+4~6 周
