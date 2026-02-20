# DR-005: Lorebook 触发注入的预算截断策略

## Executive Summary

SillyTavern 和 NovelAI 均已实现成熟的 Lorebook 预算与激活系统，核心机制是「关键词扫描 → 候选集 → 优先级排序 → 预算截断」。语义相似度（embedding）匹配成本高且收益有限，MVP 应以关键词匹配为主，辅以手动 priority 设定；v2 再考虑 embedding 增强。

## Research Findings

### 1. SillyTavern World Info 激活机制

根据官方文档和 World Info Encyclopedia：

**扫描与激活**：
- `Scan Depth`：扫描最近 N 条消息（默认可配 1~10）寻找关键词
- 关键词匹配：条目的 `keys` 字段中任一关键词出现在扫描范围内即激活
- `Secondary Keys`：类似 NovelAI 的 AND 逻辑，主键 + 辅键同时命中才激活
- `Selective`：开启后需要主键 AND 辅键同时匹配
- 大小写敏感/不敏感可配
- 支持正则表达式作为关键词

**递归扫描（Recursive Scanning）**：
- 条目 A 被激活后，其 content 也纳入扫描范围
- 如果 A 的内容包含条目 B 的关键词，B 也会被激活
- 支持多级递归（可配置递归深度上限）
- 这是实现"知识关联自动展开"的核心机制

**预算控制**：
- `Token Budget`：WI 总预算（token 数）
- `Budget Cap`：预算上限（Context Percent 方式）
- 超出预算后的截断逻辑：
  1. Constant 条目（Always Active）最先占位
  2. 按 `Order` 值从高到低排列
  3. 直接关键词匹配 > 递归激活
  4. 预算耗尽则停止插入后续条目

### 2. NovelAI Lorebook 预算机制

**激活规则**：
- 支持多关键词 OR（任一匹配）
- 支持 `&` 操作符实现 AND 逻辑
- `Force Activation`：强制激活，不需要关键词匹配
- `Cascading Activation`：类似 SillyTavern 的递归扫描
- `Search Range`：向前搜索多远的文本（token 数）

**预算与截断**：
- `Token Budget`：全局条目预算上限
- `Reserved Tokens`：为条目预留的最小 token 数
- `Insertion Order`：数值越大越优先处理
- `Trim Direction`：超出预算时从 Top 或 Bottom 截断条目内容
- `Maximum Trim Type`：截断粒度（newline / sentence / token）
- Categories 可设独立子预算（Subcontext），实现分组预算隔离

### 3. 关键词匹配 vs 语义相似度

| 维度 | 关键词匹配 | 语义相似度（Embedding） |
|------|-----------|------------------------|
| 实现成本 | 极低（字符串搜索） | 高（需 embedding 模型 + 向量库） |
| 延迟 | <1ms | 50~200ms（API）/ 10~50ms（本地模型） |
| 精度 | 高（精确匹配） | 中（可能误召回） |
| 召回率 | 低（同义词/指代无法匹配） | 高（语义近似可召回） |
| 中文支持 | 简单（别名机制补偿） | 需要中文 embedding 模型（如 BGE-zh） |
| 运行成本 | 零 | API embedding ~$0.0001/次，本地模型需 GPU/CPU |

**结论**：对于 Lorebook 场景，关键词 + 别名（aliases）已覆盖 90%+ 的触发需求。语义匹配主要解决"同义词/隐含引用"问题，但在写小说场景中，作者通常会直接使用角色名/地名，关键词匹配已足够。

### 4. Priority 设定策略

**手动 Priority**（推荐 MVP）：
- 简单直观：用户为每个条目设 1~100 的优先级
- 建议默认值：主角 100，重要配角 80，地点/组织 60，背景设定 40，氛围/规则 20
- SillyTavern 和 NovelAI 均采用手动设定

**自动 Priority**（v2 考虑）：
- 基于出场频次：近 N 章出现越多，优先级越高
- 基于图谱距离：与当前场景角色的 KG 距离越近，优先级越高
- 基于触发频率：最近触发越多的条目适当降权（避免重复注入）

### 5. 截断后关键信息保护

**问题**：低优先级条目被截断后，可能丢失关键世界规则

**解决方案**：
- `Constant/Force Active` 标记：对核心世界规则强制注入（不受预算限制，但计入预算消耗）
- `Reserved Tokens`：为重要条目预留最小 token 数，保证至少部分内容注入
- `Trim Direction` 策略：从 Bottom 截断（保留条目开头的核心定义），或从 newline 截断（保留完整段落）
- 分级内容：条目内容按重要性排列，最关键的放前几行

## Impact on Spec

1. §7.2 的触发策略描述需要大幅扩充，加入 Scan Depth、递归激活、Secondary Keys 等机制
2. §7.2 的 `priority` 字段需要给出默认值建议和设定指南
3. §8.2 的 Lorebook 预算需要与 KG 注入预算统一管理
4. 需要新增「预算截断策略」小节（截断方向、粒度、保底机制）

## Recommendations

1. **MVP 激活机制**：关键词 OR 匹配 + aliases 别名扩展 + Scan Depth（默认扫描当前场景 + 前一场景）
2. **AND 逻辑**（`and_keywords`）排 v1，递归激活排 v1
3. **预算截断逻辑**：
   - Constant 条目最先插入
   - 按 priority DESC 排序
   - 同 priority 按关键词匹配精确度排序
   - 超出预算的条目从 Bottom 截断到 sentence 粒度
   - 截断后 token 数 < reserved 的条目整条移除
4. **Priority 默认值**：主角 100，配角 80，地点 60，规则 40，氛围 20
5. **条目内容写作指南**：告知用户"把最重要的信息放在前几行"（因为 Bottom trim）

## Sources

- [SillyTavern World Info 官方文档](https://docs.sillytavern.app/usage/core-concepts/worldinfo/)
- [World Info Encyclopedia by kingbri](https://rentry.co/world-info-encyclopedia)
- [NovelAI Lorebook 文档](https://docs.novelai.net/en/text/lorebook/)
- [AI Dynamic Storytelling Wiki: Lorebooks](https://aids.miraheze.org/wiki/Lorebooks)
- [NovelAI Advanced Settings: Context Budget](https://docs.novelai.net/en/text/editor/advancedsettings/)
