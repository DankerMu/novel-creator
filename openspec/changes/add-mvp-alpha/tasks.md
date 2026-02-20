## 1. Project Scaffolding
- [ ] 1.1 Initialize FastAPI backend project (uv + pyproject.toml)
- [ ] 1.2 Initialize React/Next.js frontend project (pnpm + TypeScript)
- [ ] 1.3 Configure SQLite + Alembic migrations
- [ ] 1.4 Set up Docker Compose (api + web)
- [ ] 1.5 Configure LLM provider abstraction (OpenAI-compatible endpoint)

## 2. Project Management CRUD
- [ ] 2.1 Create SQLite tables: projects, books, chapters, scenes, scene_text_versions
- [ ] 2.2 Implement CRUD API endpoints (POST/GET/PUT/DELETE)
- [ ] 2.3 Build frontend project tree (left sidebar: Book → Chapter → Scene)
- [ ] 2.4 Build scene text editor (center panel, Markdown support)
- [ ] 2.5 Write API tests for all CRUD endpoints

## 3. Story Bible
- [ ] 3.1 Create bible_fields table (id, project_id, key, value_md, locked, updated_at)
- [ ] 3.2 Implement Bible CRUD API (GET /api/bible, PUT /api/bible/{key})
- [ ] 3.3 Build Bible panel (right sidebar tab)
- [ ] 3.4 Implement locked field toggle (locked fields inject as hard constraints)
- [ ] 3.5 Write tests for Bible CRUD and lock behavior

## 4. AI Scene Generation
- [ ] 4.1 Implement Instructor + Pydantic SceneCard model
- [ ] 4.2 POST /api/generate/scene-card (non-streaming, structured JSON)
- [ ] 4.3 Implement FastAPI SSE streaming for scene draft
- [ ] 4.4 POST /api/generate/scene-draft (SSE streaming)
- [ ] 4.5 Build basic Context Pack assembler (Bible locked fields + last N paragraphs)
- [ ] 4.6 Build frontend streaming display (editor shows text as it generates)
- [ ] 4.7 Write tests for scene card validation and streaming endpoint

## 5. Chapter Summary
- [ ] 5.1 Create chapter_summaries table
- [ ] 5.2 POST /api/extract/chapter-summary (auto-generate on chapter_mark_done)
- [ ] 5.3 Integrate summary into Context Pack for next chapter
- [ ] 5.4 Build summary display in right sidebar
- [ ] 5.5 Write tests for summary generation and Context Pack integration

## 6. Export
- [ ] 6.1 GET /api/export/markdown (full book / single chapter)
- [ ] 6.2 GET /api/export/txt
- [ ] 6.3 Build export button in frontend
- [ ] 6.4 Write tests for export format correctness
