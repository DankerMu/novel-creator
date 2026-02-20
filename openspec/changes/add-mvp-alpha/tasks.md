## 1. Project Scaffolding
- [x] 1.1 Initialize FastAPI backend project (uv + pyproject.toml)
- [x] 1.2 Initialize React/Next.js frontend project (pnpm + TypeScript)
- [x] 1.3 Configure SQLite + Alembic migrations
- [x] 1.4 Set up Docker Compose (api + web)
- [x] 1.5 Configure LLM provider abstraction (OpenAI-compatible endpoint)

## 2. Project Management CRUD
- [x] 2.1 Create SQLite tables: projects, books, chapters, scenes, scene_text_versions
- [x] 2.2 Implement CRUD API endpoints (POST/GET/PUT/DELETE)
- [x] 2.3 Build frontend project tree (left sidebar: Book → Chapter → Scene)
- [x] 2.4 Build scene text editor (center panel, Markdown support)
- [x] 2.5 Write API tests for all CRUD endpoints

## 3. Story Bible
- [x] 3.1 Create bible_fields table (id, project_id, key, value_md, locked, updated_at)
- [x] 3.2 Implement Bible CRUD API (GET /api/bible, PUT /api/bible/{key})
- [x] 3.3 Build Bible panel (right sidebar tab)
- [x] 3.4 Implement locked field toggle (locked fields inject as hard constraints)
- [x] 3.5 Write tests for Bible CRUD and lock behavior

## 4. AI Scene Generation
- [x] 4.1 Implement Instructor + Pydantic SceneCard model
- [x] 4.2 POST /api/generate/scene-card (non-streaming, structured JSON)
- [x] 4.3 Implement FastAPI SSE streaming for scene draft
- [x] 4.4 POST /api/generate/scene-draft (SSE streaming)
- [x] 4.5 Build basic Context Pack assembler (Bible locked fields + last N paragraphs)
- [x] 4.6 Build frontend streaming display (editor shows text as it generates)
- [x] 4.7 Write tests for scene card validation and streaming endpoint

## 5. Chapter Summary
- [x] 5.1 Create chapter_summaries table
- [x] 5.2 POST /api/extract/chapter-summary (auto-generate on chapter_mark_done)
- [x] 5.3 Integrate summary into Context Pack for next chapter
- [x] 5.4 Build summary display in right sidebar
- [x] 5.5 Write tests for summary generation and Context Pack integration

## 6. Export
- [ ] 6.1 GET /api/export/markdown (full book / single chapter)
- [ ] 6.2 GET /api/export/txt
- [ ] 6.3 Build export button in frontend
- [ ] 6.4 Write tests for export format correctness
