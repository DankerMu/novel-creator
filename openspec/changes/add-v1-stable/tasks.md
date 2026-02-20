## 1. Workflow Engine
- [ ] 1.1 Implement JSON DAG parser + topological sort
- [ ] 1.2 Implement async parallel executor (asyncio.gather per layer)
- [ ] 1.3 Implement @engine.register decorator for handler registration
- [ ] 1.4 Create workflow_node_runs table
- [ ] 1.5 Implement node-level progress reporting via SSE
- [ ] 1.6 Implement single-node retry + checkpoint resume
- [ ] 1.7 Register 5 default handlers: chapter_summary, kg_extraction, lore_suggestion, consistency_check, export_chapter
- [ ] 1.8 Wire chapter_mark_done event → chapter_complete_pipeline workflow
- [ ] 1.9 Build workflow progress UI (DAG visualization + node status)
- [ ] 1.10 Write tests for DAG parsing, parallel execution, retry, resume

## 2. Version Control
- [ ] 2.1 Implement scene version management (auto-version on save)
- [ ] 2.2 Implement chapter snapshot on chapter_mark_done
- [ ] 2.3 Implement named checkpoint API (manual save points)
- [ ] 2.4 Implement rollback to any snapshot/checkpoint
- [ ] 2.5 Build version history panel (timeline view + diff)
- [ ] 2.6 Write tests for versioning, snapshot, rollback

## 3. Streaming Gate (Strong Word Count)
- [ ] 3.1 Implement soft_limit / hard_limit calculation
- [ ] 3.2 Implement Chinese sentence boundary detection (regex: [。？！…」』）\n])
- [ ] 3.3 Implement multi-round continuation (max 3 rounds)
- [ ] 3.4 Persist streaming state to workflow_runs table
- [ ] 3.5 Write tests for boundary detection, continuation, state recovery

## 4. Vector Search (sqlite-vec)
- [ ] 4.1 Integrate sqlite-vec extension
- [ ] 4.2 Implement paragraph chunking (~200 chars/chunk)
- [ ] 4.3 Integrate BGE-small-zh local embedding model
- [ ] 4.4 Implement vector search API with deduplication against KG evidence
- [ ] 4.5 Add vector results to Context Pack (5~8% budget, supplementary layer)
- [ ] 4.6 Write tests for embedding, search, deduplication

## 5. LLM Consistency Check
- [ ] 5.1 Implement setting contradiction detection (Bible/Lore vs prose, LLM-based)
- [ ] 5.2 Implement POV drift detection (semi-rule + LLM confirmation)
- [ ] 5.3 Add confidence and source=llm to check results
- [ ] 5.4 Write tests with known contradiction fixtures

## 6. Prompt Workshop
- [ ] 6.1 Implement prompts table (group, key, template_md, version, enabled)
- [ ] 6.2 Build prompt editor UI with version history
- [ ] 6.3 Implement prompt A/B testing (select active version per group)
- [ ] 6.4 Write tests for prompt CRUD and version switching
