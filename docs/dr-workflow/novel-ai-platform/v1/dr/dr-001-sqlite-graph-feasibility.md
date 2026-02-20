# DR-001: SQLite 图表实现 KG 的可行性

## Executive Summary

SQLite 通过 nodes/edges 表 + 递归 CTE 可以实现"最小可用"知识图谱，对于小说级别的图规模（数千节点、数万边）性能完全可接受。开源库 simple-graph（1.5k stars）已验证该模式可行。但多跳查询（≥3跳）性能显著下降，且缺乏原生图可视化和路径算法支持，需要明确"Lite 模式"的能力边界。

## Research Findings

### 1. SQLite 图数据库实现方案

**simple-graph**（GitHub 1.5k stars，MIT 协议）是最成熟的 SQLite 图数据库实现：
- 数据模型：`nodes` 表（id + JSON body）+ `edges` 表（source, target, properties JSON）
- 查询方式：Python API 封装 SQL 查询，支持基本遍历
- 限制：遍历逻辑在 Python 层实现（非纯 SQL），每个节点一次查询，深度遍历较慢

**递归 CTE 方案**（纯 SQL）：
```sql
WITH RECURSIVE graph_walk AS (
  SELECT target AS node, 1 AS depth
  FROM edges WHERE source = :start_node
  UNION ALL
  SELECT e.target, gw.depth + 1
  FROM edges e JOIN graph_walk gw ON e.source = gw.node
  WHERE gw.depth < :max_depth
)
SELECT DISTINCT node FROM graph_walk;
```
- SQLite 递归 CTE 对 1-2 跳邻居查询性能良好（<10ms，千级节点）
- 3 跳以上性能急剧下降（组合爆炸），需要加 `LIMIT` 或 `depth` 约束
- 不支持最短路径、PageRank 等图算法

### 2. 性能对比：SQLite vs Neo4j

| 操作 | SQLite (递归 CTE) | Neo4j (Cypher) |
|------|------------------|----------------|
| 1 跳邻居 | <5ms | <2ms |
| 2 跳邻居 | <20ms | <5ms |
| 3 跳邻居 | 100ms~1s | <10ms |
| 最短路径 | 需自行实现，慢 | 原生 `shortestPath()`，快 |
| 模式匹配 | 多表 JOIN，复杂 | Cypher 原生支持 |
| 聚合统计 | SQL 擅长 | 同等水平 |
| 全文搜索 | FTS5 扩展 | 内建全文索引 |

关键发现：在 Stack Overflow 和 HN 讨论中，多位开发者指出关系型数据库（包括 PostgreSQL）在某些图任务上可以超越 Neo4j，尤其是聚合查询和简单遍历。但在深度遍历和复杂模式匹配上，图数据库优势明显。

### 3. 小说 KG 的实际规模评估

一部百万字长篇的 KG 规模估算：
- 角色：50~200 个
- 地点：30~100 个
- 事件：200~1000 个
- 关系：500~5000 条
- 总节点：<2000，总边：<5000

这个量级对 SQLite 完全没有压力。即使 3 跳查询也在可接受范围内（<500ms）。

### 4. Lite 模式的能力边界

**可做到**：
- 实体 CRUD（节点增删改查）
- 关系管理（边的增删改查）
- 1-2 跳邻居查询（角色关系网）
- 基本冲突检测（WHERE 子句匹配）
- 按章节筛选事实
- JSON 属性存储（SQLite JSON1 扩展）

**做不到或勉强**：
- 复杂图可视化（需前端自行用 D3/Cytoscape 渲染，数据从 API 拉取）
- 路径分析（因果链、伏笔追踪跨 3+ 跳）
- 实时图算法（中心性、社区检测）
- 大规模模式匹配（如"找出所有三角关系"）

## Impact on Spec

1. 规格书 §5.2 的 Lite 模式描述过于简略，需要明确能力边界
2. §6.2 的 Neo4j schema 在 Lite 模式下需要给出 SQLite 对等的表结构
3. 图可视化不依赖存储层——即使 Lite 模式，前端也可以用 D3/Cytoscape 渲染从 API 拉取的图数据

## Recommendations

1. **Lite 模式采用双表设计**：`kg_nodes`（id, type, name, aliases_json, properties_json, chapter_id）+ `kg_edges`（id, source_id, target_id, relation_type, properties_json, chapter_id），与 Neo4j schema 保持字段对齐
2. **限制 Lite 模式查询深度为 2 跳**，UI 标注"深度关系分析需要 Full 模式"
3. **抽象 GraphService 接口**，Lite 用 SQLiteGraphAdapter，Full 用 Neo4jAdapter，确保上层代码不感知存储差异
4. **图可视化由前端统一处理**（D3.js/Cytoscape.js），不依赖 Neo4j Browser
5. **MVP 阶段从 Lite 模式起步**即可满足核心需求（角色关系、事实存证、冲突检测），Neo4j 作为性能/高级功能升级路径

## Sources

- [simple-graph: SQLite 图数据库](https://github.com/dpapathanasiou/simple-graph)（1.5k stars，MIT）
- [SQLite Recursive CTE 图遍历指南](https://runebook.dev/en/articles/sqlite/lang_with/rcex3)
- [SQL vs Neo4j 图查询性能对比研究](https://github.com/mitrjain/NeoSqlPerformanceContraster)
- [HN 讨论: simple-graph vs Neo4j 性能](https://news.ycombinator.com/item?id=25545029)
- [Stack Overflow: Graph DB vs RDBMS CTE 性能对比](https://stackoverflow.com/questions/63112168)
