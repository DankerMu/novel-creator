# DR-003: 字数控制"强约束(Streaming Gate)"的工程复杂度

## Executive Summary

流式输出中断续写在技术上可行（OpenAI/Anthropic 均支持 `max_tokens` + 续写），但中文语义边界检测和多轮续写连贯性是主要工程难点。推荐 MVP 采用「中约束（场景预算）」为默认，强约束作为 v1 高级功能，并给出具体实现方案。

## Research Findings

### 1. 流式中断的 API 支持

**OpenAI API**：
- `max_tokens` 参数限制单次输出长度
- `stop` 参数支持自定义停止序列（如 `\n\n`、`---`）
- 流式输出中可随时客户端断开（cancel stream）
- 续写时把前文作为 assistant message 继续生成

**Anthropic API**：
- `max_tokens` 同样支持
- 支持 `stop_sequences` 自定义停止
- 流式通过 SSE 逐 token 返回，客户端可中途关闭连接
- 续写：将前文放入 `assistant` 角色的 message content 前缀

两家 API 均原生支持"生成到 N tokens 后停止"的基本机制。

### 2. 中文语义边界检测

**核心难题**：按 token 数中断可能在句子中间截断，产生不完整的句子。

**解决方案**：
- **句号/问号/感叹号检测**：中文标点（。？！）是最可靠的句子边界。在流式接收时维护一个 buffer，记录最后一个完整句子的位置
- **段落边界**：检测 `\n` 或 `\n\n`，段落结尾是更安全的中断点
- **实现模式**：设 target = N 字，soft_limit = N * 0.9，hard_limit = N * 1.1
  - 到达 soft_limit 后，在下一个句号/段落处中断
  - 如果到达 hard_limit 仍无句号，强制在最近的逗号处中断

**中文分词库**（备选）：
- jieba：轻量，但做句子边界检测 overkill
- 正则匹配 `[。？！…」』）]` 足够覆盖 95% 的句子边界场景

### 3. 多轮续写连贯性

**风险**：中断后续写可能出现重复、风格漂移、遗忘前文

**缓解方案**：
- 续写 prompt 中注入："你正在续写以下段落，请从断点处自然衔接，不要重复已有内容"
- 将中断点前最后 2-3 段作为短期上下文
- 注入当前场景卡的 target_chars 和 remaining_chars
- 限制最大续写轮数（建议 ≤3 轮），超出则走人工介入

### 4. 状态机设计

```
IDLE → GENERATING → [soft_limit] → SEEKING_BOUNDARY → [boundary_found] → PAUSED
PAUSED → [remaining > 0] → GENERATING (round 2)
PAUSED → [remaining ≤ 0] → COMPLETED
GENERATING → [hard_limit] → FORCE_CUT → PAUSED
GENERATING → [error] → ERROR → RETRY_ONCE → GENERATING / FAILED
```

需要持久化状态：current_chars, total_target, round_number, last_text_snapshot

## Impact on Spec

1. §11.2 强约束描述过于简略，需要补充状态机和边界检测算法
2. 建议 §11.2 明确标注：强约束为 v1 功能，MVP 仅实现中约束
3. §9.1 阶段 4 的"达到阈值中断再续写"需要给出具体实现指引

## Recommendations

1. **MVP 默认中约束（Scene Budget）**：场景预算 + 生成后测字数 + 单轮扩写/压缩，工程成本低且效果好
2. **v1 实现强约束**时采用 soft/hard limit + 句号边界检测模式
3. **中文边界检测用正则**：`/[。？！…」』）\n]/`，不需要引入分词库
4. **续写最多 3 轮**，超出提示用户手动调整
5. **状态持久化到 `workflow_runs` 表**，支持中断恢复

## Sources

- [OpenAI API: Chat Completions - max_tokens / stop](https://platform.openai.com/docs/api-reference/chat/create)
- [Anthropic API: Messages - max_tokens / stop_sequences](https://docs.anthropic.com/en/api/messages)
- [NovelForge 后续规划: 章节字数约束思路](https://github.com/RhythmicWave/NovelForge)
- [Unicode 中文标点符号范围](https://www.unicode.org/charts/PDF/U3000.pdf)
