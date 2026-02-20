# DR-006: 一致性校验的自动化程度

## Executive Summary

一致性校验应采用「规则引擎 + LLM 推理」混合架构：结构化冲突（时间线、角色状态、持有物）用规则引擎检测（零成本、零误报），语义级冲突（设定矛盾、视角漂移、风格偏离）用 LLM 推理检测。MVP 先实现规则引擎覆盖的 4 类结构化检查，LLM 校验排 v1。

## Research Findings

### 1. 规则引擎 vs LLM 推理

| 维度 | 规则引擎 | LLM 推理 |
|------|---------|----------|
| 适用范围 | 结构化、可形式化的冲突 | 语义级、模糊的冲突 |
| 准确率 | 100%（规则正确即零误报） | 70~85%（取决于上下文和模型） |
| 误报率 | 0% | 15~30%（需人工复核） |
| 成本 | 零（本地计算） | ~$0.01~0.05/章（取决于模型和上下文长度） |
| 延迟 | <100ms | 5~30s/章 |
| 维护性 | 需手写规则，新冲突类型需新规则 | 通用，prompt 调整即可覆盖新场景 |

### 2. 可规则化的校验项（MVP 优先）

**角色状态冲突**：
- 规则：`IF character.status == 'dead' AND character APPEARS_IN chapter_N THEN conflict`
- 数据源：KG 节点的 `status` 属性
- 实现：SQL/Cypher 查询，零成本

**时间线冲突**：
- 规则：`IF event_A.time > event_B.time AND event_A CAUSES event_B THEN conflict`
- 数据源：KG Event 节点的 `time` 属性 + CAUSES 关系
- 需要规范化时间表示（叙事内时间线，如 Day1/Day2 或具体日期）

**持有物冲突**：
- 规则：`IF character_A OWNS item AND character_B OWNS item AND item.unique THEN conflict`
- 数据源：KG OWNS 关系

**线索状态冲突**：
- 规则：`IF plot_thread.status == 'resolved' AND plot_thread MENTIONED_AS 'unknown' IN chapter_N THEN conflict`
- 数据源：KG PlotThread 节点 status + 正文关键词匹配

### 3. 需要 LLM 推理的校验项（v1）

**设定矛盾**：
- 场景：正文描述与 Bible/Lore 的语义冲突（如 Lore 说"主角恐高"但正文写"主角在悬崖边毫不畏惧"）
- 方法：将 Lore 条目 + 相关正文段落送 LLM，prompt 要求找出矛盾
- 预估准确率：75~85%（依赖上下文完整度）

**视角漂移**：
- 场景：Bible 设定第一人称，但某段突然出现第三人称叙述
- 方法：可半规则化（检测"他/她想到"等第三人称标记 + LLM 确认）
- 预估准确率：80~90%

**重复表达/风格偏离**：
- 场景：连续重复词、句式模式异常
- 方法：
  - 重复检测：n-gram 频率统计（规则化，零成本）
  - 风格偏离：句长分布/标点密度等统计指标 + LLM 评估

### 4. 误报控制策略

- **置信度分级**：每个校验结果标注 confidence（规则引擎 = 1.0，LLM = 模型自评分 0~1）
- **严重度分级**：high（角色死而复生）、medium（持有物矛盾）、low（风格轻微偏离）
- **默认只展示 high + medium**，low 级问题折叠显示
- **用户反馈闭环**：标记"非问题"的条目训练排除规则，降低重复误报
- **批量确认**：同类问题可一键忽略

### 5. 成本估算（LLM 校验）

以一章 5000 字为例：
- 输入：正文 5000 字 + Bible/Lore 相关条目 ~2000 字 + KG 事实 ~1000 字 ≈ 8000 字 ≈ 4000 tokens
- 输出：校验报告 ~500 tokens
- 单次成本（Claude Sonnet）：~$0.02
- 百章成本：~$2.00

成本可接受，但需要控制调用频率（仅 chapter_mark_done 时触发，非实时）。

## Impact on Spec

1. §12 需要明确区分规则引擎校验（MVP）和 LLM 校验（v1）
2. §12.2 校验输出增加 `confidence` 字段和 `source`（rule/llm）字段
3. §9.1 阶段 6 的"校验 agent"需要分两阶段实现
4. 需要在 §6.1 中为时间线数据增加规范化时间字段

## Recommendations

1. **MVP 实现 4 类规则引擎校验**：角色状态、时间线、持有物、线索状态（数据源 = KG 查询）
2. **v1 增加 LLM 语义校验**：设定矛盾、视角漂移（prompt-based）
3. **n-gram 重复检测**可在 MVP 中实现（纯统计，零成本）
4. **校验结果统一输出格式**增加 `confidence` 和 `source` 字段
5. **时间线规范化**：要求 KG Event 节点存储 `narrative_day`（叙事天数）字段，作为时间线校验基础
6. **默认触发时机**：`chapter_mark_done` → 自动跑规则引擎；LLM 校验需用户手动触发或配置

## Sources

- [Grammarly 逻辑一致性检查功能](https://www.grammarly.com/)
- [ProWritingAid 一致性检查器](https://prowritingaid.com/)
- [Sudowrite Story Bible Tips: 一致性对生成质量的影响](https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/tips--tricks/eBjBne7foMi8uYFxWEPCai)
- [Aventuras: 风格重复分析](https://aventuras.ai/pages/features)
