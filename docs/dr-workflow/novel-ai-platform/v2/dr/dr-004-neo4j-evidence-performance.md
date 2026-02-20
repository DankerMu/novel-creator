# DR-004: Neo4j 证据字段(evidence)的存储与查询性能

## Executive Summary

Neo4j 节点/关系属性存储长文本（数百字 quote）在小说 KG 规模下不会造成严重性能问题，但会增大内存占用和降低遍历效率。推荐采用「引用指针 + 外部存储」混合模式：Neo4j 只存 chapter_id + paragraph_index 等轻量引用，完整 quote 存 SQLite，按需 JOIN 查询。

## Research Findings

### 1. Neo4j 属性存储机制

**Neo4j 属性存储特性**：
- 节点/关系的属性存储在独立的 property store 文件中
- 小属性（≤128 bytes）内联存储，大属性存入 dynamic string store
- 长文本属性会被分块存储（block size 默认 120 bytes），通过链表链接
- 查询遍历时**不会自动加载所有属性**——只有在访问属性时才会读取

**性能影响**：
- **遍历性能**：纯图遍历（不访问属性）不受属性大小影响
- **属性读取**：读取长文本属性需要多次磁盘/缓存读取（链表跳转）
- **内存占用**：如果使用 `RETURN n` 返回完整节点，长文本属性会占用大量堆内存
- **索引**：长文本属性无法建普通索引（但可建全文索引）

### 2. 小说 KG 的 evidence 规模评估

假设百万字长篇：
- ~200 章 × 每章抽取 ~20 个事实 = ~4000 个事实
- 每个 evidence quote 平均 100~300 字（约 150~450 bytes UTF-8）
- 总 evidence 数据量：4000 × 300 bytes ≈ 1.2 MB

这个量级对 Neo4j 完全不构成压力。即使全部内联存储也没问题。

### 3. 设计方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| A: 全存 Neo4j 属性 | 简单；查询一步到位 | 遍历返回全节点时内存膨胀；无法对 quote 做高效全文搜索 |
| B: Neo4j 存指针，SQLite 存 quote | 遍历轻量；quote 可用 FTS5 全文搜索 | 需要两步查询（先图后文本） |
| C: Neo4j 存指针，向量库存 embedding | 支持语义搜索 "哪些证据与X相关" | 架构复杂度高；MVP 不需要 |

### 4. "某段落被哪些事实引用" 的查询

这是反向查询需求：给定 chapter_id + paragraph_ref，找出所有引用它的 KG 事实。

**方案 A（Neo4j 纯属性）**：
```cypher
MATCH (n) WHERE n.evidence_chapter_id = $chapter_id
  AND n.evidence_paragraph_ref = $para_ref
RETURN n
```
需要在 `evidence_chapter_id` 上建索引。对于关系上的属性，需要全量扫描（关系属性索引支持有限）。

**方案 B（独立 evidence 表）**：
```sql
SELECT * FROM kg_evidence
WHERE chapter_id = ? AND paragraph_ref = ?
```
SQLite 索引查询，<1ms。然后用返回的 fact_id 去 Neo4j 查节点。

方案 B 明显更适合反向查询场景。

### 5. Neo4j 全文索引能力

Neo4j 内建全文索引（基于 Lucene）：
```cypher
CREATE FULLTEXT INDEX evidence_text FOR (n:Fact) ON EACH [n.quote]
```
可以做全文搜索，但：
- 仅支持节点属性，不支持关系属性
- 更新成本略高（每次写入重建索引）
- 中文分词需要额外配置 CJK Analyzer

## Impact on Spec

1. §6.2 的 evidence 字段设计需要细化：拆分为轻量引用（存 Neo4j）和完整引文（存 SQLite）
2. §7.3 "每条事实附 evidence" 的实现方式需要明确
3. 需要新增 `kg_evidence` SQLite 表或在现有 `kg_proposals` 中增加 evidence 字段

## Recommendations

1. **采用方案 B：指针 + 外部存储**
   - Neo4j 节点/关系属性只存：`evidence_chapter_id`(int)、`evidence_scene_id`(string)、`evidence_paragraph_idx`(int)
   - SQLite 新增 `kg_evidence` 表：`fact_id`, `chapter_id`, `scene_id`, `paragraph_idx`, `quote_text`, `created_at`
2. **反向查询用 SQLite 索引**：`CREATE INDEX idx_evidence_chapter ON kg_evidence(chapter_id, paragraph_idx)`
3. **全文搜索用 SQLite FTS5**（如果需要在 evidence 中搜索关键词）
4. **API 层做透明 JOIN**：`GET /api/kg/facts/{id}` 返回时自动拼接 evidence 详情
5. **MVP 可以先用方案 A**（全存 Neo4j），在性能出现问题时再迁移到方案 B——小说 KG 规模下方案 A 也完全可用

## Sources

- [Neo4j Property Store 架构](https://neo4j.com/docs/operations-manual/current/database-internals/store-formats/)
- [Neo4j Full-text Indexes](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/)
- [Neo4j 性能优化: 属性大小对遍历的影响](https://neo4j.com/developer/guide-performance-tuning/)
