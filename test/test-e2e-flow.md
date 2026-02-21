# 端到端完整流程测试

本文档描述一个完整的小说创作工作流，从创建项目到导出成品。

---

## 前置条件

- 后端运行: http://localhost:8000
- 前端运行: http://localhost:3000
- LLM API 配置完成（`.env` 中设置 `LLM_API_KEY` 和 `LLM_API_BASE`）

---

## 完整流程

### 第一步：创建项目结构

#### 1.1 创建项目
```bash
curl -s -X POST http://localhost:8000/api/projects \
  -H 'Content-Type: application/json' \
  -d '{"title": "星际远征", "description": "一部关于星际探索的科幻小说"}' | jq
```
记录返回的 `project_id`。

#### 1.2 创建书籍
```bash
curl -s -X POST http://localhost:8000/api/books \
  -H 'Content-Type: application/json' \
  -d '{"project_id": 1, "title": "第一卷 启航"}' | jq
```
记录 `book_id`。

#### 1.3 创建两个章节
```bash
# 第一章
curl -s -X POST http://localhost:8000/api/chapters \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1, "title": "第一章 飞船", "sort_order": 0}' | jq

# 第二章
curl -s -X POST http://localhost:8000/api/chapters \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1, "title": "第二章 星球", "sort_order": 1}' | jq
```

#### 1.4 为第一章创建场景
```bash
curl -s -X POST http://localhost:8000/api/scenes \
  -H 'Content-Type: application/json' \
  -d '{"chapter_id": 1, "title": "启航前夜", "sort_order": 0}' | jq
```

#### 1.5 验证项目树
```bash
curl -s http://localhost:8000/api/projects/1/tree | jq
```
**检查**: 树结构完整 `项目 → 书 → 2章 → 场景`

---

### 第二步：设定 Story Bible

#### 2.1 查看默认 Bible 字段
```bash
curl -s 'http://localhost:8000/api/bible?project_id=1' | jq '.[].key'
```
**检查**: 返回 9 个默认 key

#### 2.2 填写并锁定关键设定
```bash
# 假设 id=1 是"世界观"字段
curl -s -X PUT http://localhost:8000/api/bible/1 \
  -H 'Content-Type: application/json' \
  -d '{"value_md": "公元3050年，人类已掌握超光速引擎。星际联邦统治着银河系中心的500个星系。", "locked": true}' | jq

# 假设 id=2 是"主要人物"字段
curl -s -X PUT http://localhost:8000/api/bible/2 \
  -H 'Content-Type: application/json' \
  -d '{"value_md": "林远：28岁，星际联邦探索舰队少尉，性格沉稳但内心充满好奇心。", "locked": true}' | jq
```

#### 2.3 验证锁定字段
```bash
curl -s 'http://localhost:8000/api/bible/locked?project_id=1' | jq '.[].key'
```
**检查**: 返回刚锁定的字段

---

### 第三步：AI 生成第一章内容

> ⚠️ 此步需要有效的 LLM API

#### 3.1 生成场景卡
```bash
curl -s -X POST http://localhost:8000/api/generate/scene-card \
  -H 'Content-Type: application/json' \
  -d '{"chapter_id": 1, "scene_id": 1, "hints": "描写林远在启航前夜的紧张与期待"}' | jq
```
**检查**:
- 返回结构化 SceneCard
- `characters` 包含 "林远"（因为 Bible 锁定了主角设定）
- 场景与 hints 相关

#### 3.2 使用场景卡生成正文（SSE 流式）
```bash
# 将上一步返回的 SceneCard 粘贴到 scene_card 字段
curl -s -N -X POST http://localhost:8000/api/generate/scene-draft \
  -H 'Content-Type: application/json' \
  -d '{
    "scene_id": 1,
    "scene_card": {
      "title": "启航前夜",
      "location": "联邦旗舰 星辰号",
      "time": "公元3050年 启航前一晚",
      "characters": ["林远"],
      "conflict": "对未知星域的恐惧与探索的渴望",
      "turning_point": "收到神秘信号",
      "reveal": "",
      "target_chars": 800
    }
  }'
```
**检查**:
- SSE 事件逐行输出 `data: {"text": "..."}`
- 最后一个事件 `data: {"done": true, "char_count": N, "characters_present": [...]}`
- 文本中提到 "林远"

#### 3.3 保存生成的文本为场景版本
```bash
# 将生成的完整文本保存
curl -s -X POST http://localhost:8000/api/scenes/1/versions \
  -H 'Content-Type: application/json' \
  -d '{"content_md": "[将上面SSE输出的完整文本粘贴到这里]", "created_by": "ai"}' | jq
```
**检查**: 版本创建成功，`version=2`（因为已有 version=1）

---

### 第四步：完成第一章并生成摘要

#### 4.1 标记章节完成
```bash
curl -s -X POST http://localhost:8000/api/chapters/1/mark-done | jq
```
**检查**:
- 返回 ChapterSummary
- `summary_md` 包含章节叙事总结
- `key_events` 列出关键事件
- `keywords` 和 `entities` 非空

#### 4.2 验证章节状态
```bash
curl -s http://localhost:8000/api/chapters/1 | jq '.status'
```
**检查**: `"done"`

#### 4.3 验证摘要持久化
```bash
curl -s http://localhost:8000/api/chapters/1/summary | jq
```
**检查**: 返回之前生成的摘要

---

### 第五步：Context Pack 验证

验证第二章的 AI 生成能获取第一章的摘要作为长期记忆。

#### 5.1 为第二章创建场景
```bash
curl -s -X POST http://localhost:8000/api/scenes \
  -H 'Content-Type: application/json' \
  -d '{"chapter_id": 2, "title": "降落", "sort_order": 0}' | jq
```

#### 5.2 生成第二章场景卡
```bash
curl -s -X POST http://localhost:8000/api/generate/scene-card \
  -H 'Content-Type: application/json' \
  -d '{"chapter_id": 2, "scene_id": 2, "hints": "飞船降落在未知星球"}' | jq
```
**关键检查**: AI 应能感知第一章的上下文（通过 Context Pack 注入的 Bible 锁定字段 + 第一章摘要），生成的场景卡应延续第一章的故事线。

---

### 第六步：导出

#### 6.1 Markdown 导出整本书
```bash
curl -s 'http://localhost:8000/api/export/markdown?book_id=1' -o 星际远征.md
cat 星际远征.md
```
**检查**:
- 文件以 `# 第一卷 启航` 开头
- 包含 `## 第一章 飞船` 和 `## 第二章 星球`
- 第一章包含 AI 生成的场景正文
- Markdown 格式正确

#### 6.2 TXT 导出整本书
```bash
curl -s 'http://localhost:8000/api/export/txt?book_id=1' -o 星际远征.txt
cat 星际远征.txt
```
**检查**:
- 标题有 CJK 宽度的 `=` 下划线
- 章节标题有 `-` 下划线
- 纯文本，无 Markdown 语法

#### 6.3 单章导出
```bash
curl -s 'http://localhost:8000/api/export/markdown?book_id=1&chapter_id=1' -o 第一章.md
cat 第一章.md
```
**检查**: 只包含第一章内容

---

## 通过标准

| 步骤 | 验证项 | 通过? |
|------|--------|------|
| 1. 创建项目 | 项目树完整 | ☐ |
| 2. Story Bible | 字段锁定生效 | ☐ |
| 3. AI 生成 | 场景卡 + 流式正文 | ☐ |
| 4. 章节摘要 | mark-done + 结构化摘要 | ☐ |
| 5. Context Pack | 第二章感知第一章上下文 | ☐ |
| 6. 导出 | MD + TXT 格式正确 | ☐ |

**全部 ☐ 变为 ☑ 即为 MVP-α 测试通过。**
