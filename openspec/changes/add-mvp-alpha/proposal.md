# Change: Add MVP-α Core Writing Capabilities

## Why
项目从零开始，需要先建立核心写作骨架——让用户能创建项目、管理章节/场景、通过 AI 生成正文、自动生成摘要并导出成稿。这是后续所有一致性和高级功能的基础。

## What Changes
- 新增项目/Book/Chapter/Scene CRUD API 和前端项目树
- 新增 Story Bible 核心字段管理（CRUD + locked 开关）
- 新增 AI 场景卡生成（Instructor + Pydantic，非流式）和场景正文生成（FastAPI SSE 流式）
- 新增基础 Context Pack（Bible + 最近文本）
- 新增章节摘要自动生成
- 新增 Markdown/TXT 导出

## Impact
- Affected specs: project-management, story-bible, ai-generation, chapter-summary, export
- Affected code: 全新项目，所有代码为新增
- 预估工期：3~4 周（1 人全栈 + AI 辅助）
