# DR-002: 上下文拼装的 token 预算分配策略

## Executive Summary

SillyTavern 和 NovelAI 均已实现成熟的上下文预算分配系统，核心模式是「分区预算 + 优先级排序 + 动态截断」。规格书 §8 仅给出了分层顺序但缺少具体预算比例和溢出策略，需要补充明确的预算分配表和动态调整机制。

## Research Findings

### 1. SillyTavern 的上下文预算系统

根据 SillyTavern 官方文档和 World Info Encyclopedia（by kingbri）：

**全局预算控制**：
- `Context Size`：总上下文窗口大小（如 8192/16384/32768 tokens）
- `Token Budget`：World Info 可占用的最大 token 数，超出后不再激活新条目
- `Context Percent`：WI 预算占总上下文的百分比（替代固定数值）
- `Scan Depth`：扫描最近 N 条消息用于关键词匹配（默认 1~10 条）

**条目级优先级**：
- `Constant entries`（常驻条目）最先插入，不受关键词触发限制
- `Order` 数值越高优先级越高，预算不足时低 Order 条目被截断
- 直接关键词匹配 > 递归激活（被其他条目内容触发）
- 支持 `Sticky` 持续激活和 `Cooldown` 冷却机制

**插入位置**：
- 支持 `before_char`、`after_char`、`@D`（深度位置）等多种插入点
- 不同位置影响 AI 对信息的"注意力权重"

### 2. NovelAI 的上下文分配机制

根据 NovelAI 官方文档 Advanced Settings 页：

**Context Settings 窗口**：
- 提供可视化 `Context Bar`，按颜色区分各来源占比
- 每个上下文区域可独立设置：`Budget`（token 预算）、`Reserved Tokens`（预留）、`Insertion Position`、`Trim Direction`
- Lorebook 独立设置 `Token Budget` 和 `Reserved Tokens`

**Lorebook 预算**：
- `Token Budget`：所有激活条目的总预算上限
- `Reserved Tokens`：为单个条目预留的最小 token 数
- `Insertion Order`：决定多条目间的插入顺序（数值越大越先处理）
- `Trim Direction`：预算不足时从条目的 Top/Bottom 开始截断
- `Maximum Trim Type`：可设为 newline/sentence/token 级截断粒度

**Categories（分类子上下文）**：
- 条目可分组到 Category，每个 Category 有独立的子预算
- 子上下文作为整体插入主上下文，实现「组级预算隔离」

### 3. 业界推荐的预算分配比例

综合 SillyTavern 社区实践和 NovelAI 用户指南：

| 上下文层 | 建议占比 | 说明 |
|---------|---------|------|
| 系统约束（System Prompt） | 5~10% | 风格卡、POV、禁忌等，较稳定 |
| 长期记忆（Rolling Summary） | 10~15% | 主线摘要、阶段目标、未解线索 |
| 结构化事实（KG + Lorebook） | 15~25% | 按触发动态注入，此为预算上限 |
| 短期上下文（Recent Text） | 50~70% | 留给最近场景原文，保证续写连贯 |

**关键洞察**：短期上下文（最近原文）必须占大头（≥50%），否则续写会丧失连贯性。SillyTavern 社区普遍建议 WI 不超过总上下文的 25%。

### 4. 固定比例 vs 动态调整

**固定比例**：
- 优点：实现简单、可预测、调试方便
- 缺点：首章（无历史）和后期（信息密集）需求差异大

**动态调整策略**：
- **按阶段调整**：首章加大 System Prompt 和 Bible 占比（无历史可用）；中后期压缩 Bible、增加 KG/摘要
- **按触发密度调整**：如本章涉及角色少，Lorebook 实际占比低于预算，剩余配额回流给短期上下文
- **溢出降级**：预算不足时按优先级逐层降级（先截断低优先级 Lore，再压缩 Rolling Summary，最后缩短 Recent Text）

推荐：**固定基线 + 弹性溢出**。设置各层最大预算，未用完的预算自动分配给短期上下文。

## Impact on Spec

1. §8.2 需要补充具体预算比例表（不能只列分层顺序）
2. §8 需要新增「预算溢出策略」小节，定义降级顺序
3. §7.2 Lorebook 注入的 10%~20% 建议改为 15%~25%（与 KG 共享），并明确这是上限而非固定值
4. 需要定义「首章模式」和「常规模式」的预算差异

## Recommendations

1. **采用 SillyTavern 模式的分区预算设计**：每层设 `max_budget`（上限）和 `reserved`（保底），超出上限截断，低于保底强制保留
2. **默认预算表**（以 32K 上下文为例）：
   - System: max 2048 tokens (6%)
   - Long-term Memory: max 4096 tokens (13%)
   - KG + Lorebook: max 6144 tokens (19%)
   - Recent Text: 剩余全部 (~62%)
3. **条目级优先级**参考 NovelAI 的 `Insertion Order` + SillyTavern 的 `Order` 机制
4. **实现溢出回流**：各层未用完的 budget 自动归还给 Recent Text 池
5. **MVP 先实现固定比例**，v1 再加动态调整（按章节进度、触发密度）

## Sources

- [SillyTavern World Info 官方文档](https://docs.sillytavern.app/usage/core-concepts/worldinfo/)
- [World Info Encyclopedia by kingbri](https://rentry.co/world-info-encyclopedia)
- [SillyTavern Token Budget 讨论](https://www.reddit.com/r/PygmalionAI/comments/1350jz1/configure_tokens_sillytavernai/)
- [NovelAI Advanced Settings 文档](https://docs.novelai.net/en/text/editor/advancedsettings/)
- [NovelAI Lorebook 文档](https://docs.novelai.net/en/text/lorebook/)
- [AI Dynamic Storytelling Wiki: Lorebooks](https://aids.miraheze.org/wiki/Lorebooks)
