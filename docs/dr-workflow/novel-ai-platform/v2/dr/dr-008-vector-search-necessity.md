# DR-008: 向量检索的必要性与成本

## Executive Summary

向量检索在百万字长篇创作中对"伏笔回指"和"氛围相似场景"召回有明确价值，但在 MVP 阶段 KG + Lorebook + 关键词匹配已能覆盖 80%+ 的上下文需求。推荐 MVP 不集成向量库，v1 用 sqlite-vec（SQLite 扩展）作为轻量方案，v2 再考虑 Qdrant/Chroma。

## Research Findings

### 1. 向量检索在长文本创作中的实际价值

**高价值场景**：
- 伏笔回指："第 3 章提到的神秘符号"在第 50 章需要回顾——关键词可能不同（"符号" vs "印记" vs "图案"），语义检索可以找到
- 氛围相似场景："写一个类似第 12 章雨夜追逐的紧张氛围"——纯关键词无法匹配"氛围"
- 未结构化描写："角色 A 在某章有一段内心独白提到故乡"——如果没有入 KG/Lore，只能靠向量召回

**低价值场景（KG/Lore 已覆盖）**：
- 角色关系查询 → KG
- 设定/规则查询 → Bible/Lorebook
- 时间线事件 → KG Event 节点
- 角色状态 → KG 属性

**SillyTavern 向量扩展实践**：
- SillyTavern 提供可选的 Vector Storage 扩展
- 将聊天历史 embedding 后存入向量库
- 生成时检索最相关的历史消息注入上下文
- 社区反馈：对长对话有帮助，但非必须；大多数用户不启用

### 2. 向量库方案对比（本地部署）

| 方案 | 部署方式 | 内存占用 | 查询延迟 | 特点 |
|------|---------|---------|---------|------|
| **sqlite-vec** | SQLite 扩展，零部署 | ~10MB/10K 向量 | <10ms | 与 SQLite 无缝集成；Alex Garcia 维护 |
| **Chroma** | Python 进程内 / Client-Server | ~50MB 基础 + 数据 | <20ms | API 简洁；适合原型 |
| **Qdrant** | Docker 容器 | ~100MB 基础 | <5ms | 性能最好；需 Docker |
| **FAISS** | Python 库 | 取决于数据 | <5ms | Meta 出品；无持久化，需自行管理 |

**推荐**：sqlite-vec 是最佳轻量选择——零额外依赖，直接在现有 SQLite 中加表，与 Lite 模式完美契合。

### 3. Embedding 成本分析

**API Embedding**（如 OpenAI text-embedding-3-small）：
- 百万字长篇 ≈ 50 万 tokens
- 按段落切分（~200 字/段）≈ 5000 段
- 成本：5000 × 200 tokens × $0.00002/token ≈ $0.02（极低）
- 延迟：批量处理 ~10s

**本地 Embedding**（如 BGE-small-zh）：
- 模型大小：~100MB
- CPU 推理：~10ms/段，5000 段 ≈ 50s（可接受）
- 无 API 成本
- 中文效果好（BGE 系列在中文 benchmark 领先）

### 4. 与 KG/Lorebook 的去重策略

**问题**：向量检索可能返回 KG/Lore 已覆盖的信息，导致上下文中出现重复。

**去重方案**：
- **标记去重**：向量库中每个 chunk 标记 `has_kg_fact: true`，检索结果中排除已有 KG 覆盖的 chunk
- **ID 去重**：向量检索结果包含 chapter_id + paragraph_idx，与 KG evidence 的 paragraph_idx 对比去重
- **预算隔离**：向量检索有独立 token 预算（如总上下文的 5%），不与 KG/Lore 预算竞争
- **优先级**：KG 事实 > Lore 条目 > 向量召回（向量结果作为"补充上下文"）

## Impact on Spec

1. §6.3 的"可选"定位是合理的，但需要给出明确的集成时间线
2. 建议新增 sqlite-vec 作为 Lite 模式的向量方案选项
3. §8.2 的 Context Pack 分层需要增加"向量召回"层的预算定义
4. 需要定义向量 chunk 的切分粒度和 embedding 策略

## Recommendations

1. **MVP 不集成向量库**——KG + Lorebook + 关键词已覆盖核心需求
2. **v1 集成 sqlite-vec**：零额外部署，SQLite 扩展直接使用
   - 按段落切分（~200 字/段），chapter 写完后批量 embedding
   - 使用本地 BGE-small-zh 模型（避免 API 依赖）
3. **v2 考虑 Qdrant**：如果需要更高性能或更复杂的过滤查询
4. **向量检索预算**：总上下文的 5%~8%，作为"补充上下文"层
5. **去重策略**：向量结果与 KG evidence 按 paragraph_idx 去重后再注入

## Sources

- [sqlite-vec: SQLite 向量搜索扩展](https://github.com/asg017/sqlite-vec)
- [Chroma: AI-native embedding database](https://www.trychroma.com/)
- [Qdrant: Vector Search Engine](https://qdrant.tech/)
- [BGE 中文 Embedding 模型](https://huggingface.co/BAAI/bge-small-zh-v1.5)
- [SillyTavern Vector Storage Extension](https://docs.sillytavern.app/)
