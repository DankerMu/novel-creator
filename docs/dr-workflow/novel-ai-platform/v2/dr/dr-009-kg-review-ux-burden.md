# DR-009: KG 抽取的审阅流程与用户负担

## Executive Summary

逐条审阅 KG 事实对作者负担过重（每章 20~40 条事实），会严重影响创作心流。推荐采用「置信度分级自动入库 + 事后修正」模式：高置信度事实自动入库，低置信度事实待审阅，用户可在任意时间点批量审阅或回滚。

## Research Findings

### 1. 用户负担量化评估

假设一章 5000 字：
- 抽取实体：5~15 个（角色出场、新地点、新物品）
- 抽取事件：3~8 个
- 抽取关系变化：5~15 条
- 总计：13~38 条事实

如果逐条审阅：
- 每条阅读 + 判断 ≈ 10~15 秒
- 38 条 × 12 秒 ≈ 7~8 分钟/章
- 200 章 × 7.5 分钟 = 25 小时纯审阅时间

这对作者是不可接受的。创作者希望"写完一章 → 快速确认 → 继续下一章"，不愿在审阅 KG 上花太多时间。

### 2. 审阅模式对比

| 模式 | 优点 | 缺点 |
|------|------|------|
| A: 全部先审后入 | 图谱最干净 | 用户负担最重；打断创作心流 |
| B: 全部自动入库 + 事后修正 | 零负担 | 可能引入错误事实；校验依赖脏数据 |
| C: 置信度分级（推荐） | 平衡精度和负担 | 需要实现置信度评估 |
| D: 批量审阅 + 快捷操作 | 减少逐条成本 | 仍需用户主动审阅 |

### 3. 推荐方案：置信度分级自动入库

**置信度定义**：
- **High (≥0.9)**：明确的实体出场、已知角色关系、地点提及
  - 策略：**自动入库**，标记 `source: auto_approved`
  - 例子："李明走进了书房" → Character:李明 APPEARS_IN Scene:X（置信度 0.95）

- **Medium (0.6~0.9)**：推断性关系、模糊事件、状态变化
  - 策略：**自动入库但标记待确认**，标记 `source: auto_pending`
  - 例子："她看向窗外，想起了母亲" → Character:她 RELATIONSHIP Character:母亲 type:family（置信度 0.7）

- **Low (<0.6)**：不确定的推断、可能的误抽取
  - 策略：**不入库，进 pending queue**
  - 例子："那个人影一闪而过" → Character:未知人物?（置信度 0.3）

**置信度来源**：
- LLM 自评分（要求模型在抽取时为每条事实打分 0~1）
- 规则校验：实体是否在 Lorebook 中已有对应条目（已有 → 高置信）
- 重复出现：同一事实在多处被抽取到 → 置信度叠加

### 4. "跳过审阅直接写下一章" 的处理

**当前设计的问题**：§7.3 要求"用户确认后才 approved → upsert Neo4j"，但如果用户跳过审阅，所有事实都是 pending 状态，下一章生成时 KG 查询只能获取到旧数据。

**解决方案**：
- High 置信度事实自动入库，即使用户不审阅也有基本数据
- 生成时同时查询 `approved` + `auto_approved` 状态的事实
- 待确认事实（`auto_pending`）以「虚线」或「浅色」在 UI 展示，区分已确认事实
- 用户可在任意时间点进入"审阅模式"批量处理积压的 pending 事实

### 5. 批量审阅 UI 设计

参考 Label Studio / Prodigy 的高效标注模式：

- **分类视图**：按类型分组（新角色 / 关系变化 / 事件 / 状态更新），而非逐条平铺
- **批量操作**：
  - "全部确认"：一键确认某章所有 auto_pending
  - "按类型确认"："确认所有角色出场""确认所有地点提及"
  - "快捷键"：`A` = approve, `R` = reject, `→` = next
- **diff 视图**：只展示与上一章 KG 的增量变化（新增/修改/删除）
- **置信度过滤**：滑块筛选 confidence ≥ X 的事实
- **上下文悬停**：鼠标悬停事实时，弹出 evidence 原文高亮

## Impact on Spec

1. §7.3 "用户确认后才入库" 需要改为置信度分级自动入库
2. `kg_proposals` 表需要增加 `confidence` 字段
3. KG 节点需要增加 `approval_status` 属性（auto_approved / user_approved / auto_pending / rejected）
4. §16.2 的 KG diff 审阅交互需要加入批量操作和置信度过滤

## Recommendations

1. **采用置信度分级方案**：High 自动入库，Medium 自动入库待确认，Low 进待审队列
2. **生成时查询范围**：`approved` + `auto_approved` + `auto_pending`，不查询 `rejected`
3. **审阅 UI 支持批量操作**：按类型批量确认、快捷键、diff 视图
4. **章末提示而非阻断**：章完成后弹出 toast "本章抽取了 N 条新事实，M 条待确认"，不阻断用户写下一章
5. **回滚粒度**：支持"撤销本章所有 auto_approved"，回到上一章的 KG 状态
6. **LLM 抽取 prompt 要求输出 confidence 分数**（0~1），与规则校验分数加权平均

## Sources

- [Label Studio: 高效标注工具 UI 设计](https://labelstud.io/)
- [Prodigy: 高效人机协作标注](https://prodi.gy/)
- [NovelForge: KG 抽取审阅流程](https://github.com/RhythmicWave/NovelForge)
- [Human-in-the-loop Machine Learning (O'Reilly)](https://www.oreilly.com/library/view/human-in-the-loop-machine/9781617296741/)
