# Project Context

## Purpose
中文中长篇小说（10万～百万字）AI 写作 IDE（本地 Web 版）。
通过结构化创作工作流 + 多层记忆体系（Bible/Lorebook/KG/摘要）保证长篇一致性，把"写作"当作可迭代工程系统。

## Tech Stack
- **Backend**: Python 3.12+, FastAPI, SQLite, Alembic
- **Frontend**: TypeScript, React/Next.js, shadcn/ui, Tailwind CSS
- **AI Integration**: Instructor (Pydantic structured outputs), OpenAI-compatible endpoints
- **Optional Services**: Neo4j (KG, Docker), sqlite-vec (vector search), Qdrant (v2)
- **Dev Tools**: uv (Python), pnpm (Node), Docker Compose

## Project Conventions

### Code Style
- Python: Black + Ruff, type hints required, async-first
- TypeScript: ESLint + Prettier, strict mode
- Naming: snake_case (Python), camelCase (TypeScript)
- Max function length: 50 lines; max nesting: 3 levels

### Architecture Patterns
- Service layer pattern (FastAPI routers → services → repositories)
- Event-driven cross-module communication (asyncio.Queue)
- GraphService abstraction (SQLiteGraphAdapter / Neo4jAdapter)
- Schema-first AI outputs (Instructor + Pydantic models)
- SSE for streaming text, non-streaming for structured JSON

### Testing Strategy
- pytest (backend), Vitest (frontend)
- Requirement-driven tests: happy path + edge cases + error handling
- Coverage target: 80%+ for core services

### Git Workflow
- trunk-based: main + feature branches
- Conventional commits: feat/fix/refactor/docs/test
- PR required for main

## Domain Context
- 目标用户：精品长篇作者、IP/剧本创作者
- 核心价值：一致性管理 + 结构化创作工作流
- 写作单位层级：Series → Book → Volume → Chapter → Scene → Card
- 真相源优先级：Bible 锁定 > KG approved > Lore locked > 正文
- 上下文预算：System 5~10% / Long-term 10~15% / KG+Lore 15~25% / Recent ≥50%

## Important Constraints
- Local-first: 数据默认本地落盘，不依赖云服务
- 隐私：前端不落明文 API key，由后端代理调用 LLM
- AGPL 合规：借鉴 NovelForge/Aventuras 设计，不复制代码

## External Dependencies
- LLM: OpenAI-compatible API (configurable endpoint)
- Embedding: BGE-small-zh (local) or OpenAI text-embedding-3-small
- Neo4j: 可选，Docker 部署
- Qdrant: 可选（v2），Docker 部署
