# API 端点测试

Base URL: `http://localhost:8000`

---

## 1. 健康检查

### 1.1 GET /health
```bash
curl -s http://localhost:8000/health | jq
```
**预期**: `{"status": "ok", "version": "0.1.0"}`

---

## 2. 项目管理 CRUD

### 2.1 创建项目
```bash
curl -s -X POST http://localhost:8000/api/projects \
  -H 'Content-Type: application/json' \
  -d '{"title": "测试小说", "description": "一部科幻小说"}' | jq
```
**预期**: 返回项目对象，含 `id`, `title`, `description`, `created_at`

### 2.2 获取项目列表
```bash
curl -s http://localhost:8000/api/projects | jq
```
**预期**: 返回数组，包含刚创建的项目

### 2.3 获取单个项目
```bash
curl -s http://localhost:8000/api/projects/1 | jq
```
**预期**: 返回项目详情

### 2.4 更新项目
```bash
curl -s -X PUT http://localhost:8000/api/projects/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "更新后的标题"}' | jq
```
**预期**: 返回更新后的项目，`title` 已变更

### 2.5 创建书籍
```bash
curl -s -X POST http://localhost:8000/api/books \
  -H 'Content-Type: application/json' \
  -d '{"project_id": 1, "title": "第一卷", "sort_order": 0}' | jq
```
**预期**: 返回书籍对象，含 `id`, `project_id`, `title`

### 2.6 创建章节
```bash
curl -s -X POST http://localhost:8000/api/chapters \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1, "title": "第一章 启程", "sort_order": 0}' | jq
```
**预期**: 返回章节对象，`status` 为 `"draft"`

### 2.7 创建场景
```bash
curl -s -X POST http://localhost:8000/api/scenes \
  -H 'Content-Type: application/json' \
  -d '{"chapter_id": 1, "title": "开篇场景", "sort_order": 0}' | jq
```
**预期**: 返回场景对象

### 2.8 创建场景文本版本
```bash
curl -s -X POST http://localhost:8000/api/scenes/1/versions \
  -H 'Content-Type: application/json' \
  -d '{"content_md": "林远站在飞船驾驶舱里，望着窗外的荒漠星球。", "created_by": "user"}' | jq
```
**预期**: 返回版本对象，`version=1`, `char_count` 正确

### 2.9 获取项目树
```bash
curl -s http://localhost:8000/api/projects/1/tree | jq
```
**预期**: 嵌套树结构 `project → books → chapters → scenes`

### 2.10 404 测试
```bash
curl -s http://localhost:8000/api/projects/9999 | jq
```
**预期**: HTTP 404, `{"detail": "Project not found"}`

---

## 3. Story Bible

### 3.1 获取 Bible 字段（自动创建默认值）
```bash
curl -s 'http://localhost:8000/api/bible?project_id=1' | jq
```
**预期**: 返回 9 个默认字段（世界观、主要人物、时代背景等），`locked=false`

### 3.2 更新 Bible 字段
```bash
curl -s -X PUT http://localhost:8000/api/bible/1 \
  -H 'Content-Type: application/json' \
  -d '{"value_md": "公元3050年，星际联邦时代", "locked": true}' | jq
```
**预期**: 返回更新后的字段，`value_md` 和 `locked` 已变更

### 3.3 获取锁定字段
```bash
curl -s 'http://localhost:8000/api/bible/locked?project_id=1' | jq
```
**预期**: 只返回 `locked=true` 的字段

### 3.4 Bible 404
```bash
curl -s -X PUT http://localhost:8000/api/bible/9999 \
  -H 'Content-Type: application/json' \
  -d '{"value_md": "test"}' | jq
```
**预期**: HTTP 404

---

## 4. AI 场景生成

> ⚠️ 需要有效的 LLM_API_KEY 配置

### 4.1 生成场景卡
```bash
curl -s -X POST http://localhost:8000/api/generate/scene-card \
  -H 'Content-Type: application/json' \
  -d '{"chapter_id": 1, "scene_id": 1, "hints": "要有紧迫感"}' | jq
```
**预期**: 返回 SceneCard JSON，含 `title`, `location`, `time`, `characters`, `conflict`, `target_chars`

### 4.2 流式生成场景正文
```bash
curl -s -N -X POST http://localhost:8000/api/generate/scene-draft \
  -H 'Content-Type: application/json' \
  -d '{
    "scene_id": 1,
    "scene_card": {
      "title": "飞船坠落",
      "location": "荒漠星球",
      "time": "公元3050年",
      "characters": ["林远"],
      "conflict": "引擎故障",
      "turning_point": "",
      "reveal": "",
      "target_chars": 500
    }
  }'
```
**预期**: SSE 流式输出，每个 `data:` 行含 `{"text": "..."}` 或最终 `{"done": true, "char_count": N}`

### 4.3 场景卡 404
```bash
curl -s -X POST http://localhost:8000/api/generate/scene-card \
  -H 'Content-Type: application/json' \
  -d '{"chapter_id": 9999, "scene_id": 9999}' | jq
```
**预期**: HTTP 404

---

## 5. 章节摘要

> ⚠️ mark-done 和 extract 端点需要有效的 LLM_API_KEY

### 5.1 标记章节完成（自动生成摘要）
```bash
curl -s -X POST http://localhost:8000/api/chapters/1/mark-done | jq
```
**预期**: 返回 ChapterSummary，含 `summary_md`, `key_events`, `keywords`, `entities`, `plot_threads`

### 5.2 获取章节摘要
```bash
curl -s http://localhost:8000/api/chapters/1/summary | jq
```
**预期**: 返回之前生成的摘要

### 5.3 手动提取摘要
```bash
curl -s -X POST http://localhost:8000/api/chapters/1/extract-summary | jq
```
**预期**: 返回更新后的摘要

### 5.4 幂等性：重复 mark-done 不重新调用 LLM
```bash
curl -s -X POST http://localhost:8000/api/chapters/1/mark-done | jq
```
**预期**: 直接返回已有摘要，不触发 LLM

### 5.5 空章节 mark-done 返回 400
```bash
# 先创建一个空章节（无场景文本）
curl -s -X POST http://localhost:8000/api/chapters \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1, "title": "空章节"}' | jq
# 然后 mark-done
curl -s -X POST http://localhost:8000/api/chapters/2/mark-done | jq
```
**预期**: HTTP 400, `"Chapter has no text content"`

### 5.6 摘要 404
```bash
curl -s http://localhost:8000/api/chapters/9999/summary | jq
```
**预期**: HTTP 404

---

## 6. 导出

### 6.1 Markdown 导出（整本书）
```bash
curl -s 'http://localhost:8000/api/export/markdown?book_id=1'
```
**预期**:
- Content-Type: `text/markdown; charset=utf-8`
- Content-Disposition: `attachment; filename*=UTF-8''...`
- 内容以 `# 第一卷` 开头
- 章节标题为 `## 第一章 启程`
- 包含场景文本

### 6.2 Markdown 导出（单章节）
```bash
curl -s 'http://localhost:8000/api/export/markdown?book_id=1&chapter_id=1'
```
**预期**: 以 `# 第一章 启程` 开头，只包含该章节内容

### 6.3 TXT 导出（整本书）
```bash
curl -s 'http://localhost:8000/api/export/txt?book_id=1'
```
**预期**:
- Content-Type: `text/plain; charset=utf-8`
- 标题下有 CJK 宽度的 `=` 下划线
- 无 Markdown 语法（无 `#`）

### 6.4 TXT 导出（单章节）
```bash
curl -s 'http://localhost:8000/api/export/txt?book_id=1&chapter_id=1'
```
**预期**: 只包含该章节内容

### 6.5 导出 404
```bash
curl -s 'http://localhost:8000/api/export/markdown?book_id=9999' | jq
curl -s 'http://localhost:8000/api/export/txt?book_id=9999' | jq
```
**预期**: 两个都返回 HTTP 404

### 6.6 空书导出
```bash
# 创建空书
curl -s -X POST http://localhost:8000/api/books \
  -H 'Content-Type: application/json' \
  -d '{"project_id": 1, "title": "空书"}' | jq
# 导出
curl -s 'http://localhost:8000/api/export/markdown?book_id=2'
```
**预期**: 只返回 `# 空书`
