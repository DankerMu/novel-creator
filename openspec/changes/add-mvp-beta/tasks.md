## 1. Lorebook
- [ ] 1.1 Create lore_entries table (type, title, aliases_json, content_md, secrets_md, triggers_json, priority, locked)
- [ ] 1.2 Implement Lore CRUD API (GET/POST/PUT/DELETE /api/lore)
- [ ] 1.3 Implement keyword OR matching + aliases expansion
- [ ] 1.4 Implement Scan Depth configuration (current scene + previous scene)
- [ ] 1.5 Implement budget truncation (priority DESC + Bottom trim to sentence)
- [ ] 1.6 Implement Lore import/export (SillyTavern JSON format)
- [ ] 1.7 Build Lorebook panel (right sidebar tab)
- [ ] 1.8 Write tests for trigger matching, budget truncation, import/export

## 2. Knowledge Graph
- [ ] 2.1 Create kg_nodes + kg_edges tables (SQLite Lite mode)
- [ ] 2.2 Create kg_proposals + kg_evidence tables
- [ ] 2.3 Implement KG extraction prompt (Schema-first, output confidence 0~1)
- [ ] 2.4 Implement confidence-based auto-approval (High ≥0.9 auto, Medium 0.6~0.9 pending, Low <0.6 queue)
- [ ] 2.5 Implement GraphService abstraction interface (SQLiteGraphAdapter)
- [ ] 2.6 POST /api/extract/kg → kg_proposals
- [ ] 2.7 POST /api/kg/proposals/{id}/approve and /reject
- [ ] 2.8 Build KG batch review UI (category view, confidence filter, bulk approve/reject, shortcuts A/R/→)
- [ ] 2.9 Build evidence hover highlight
- [ ] 2.10 Write tests for extraction, confidence routing, approval workflow

## 3. Context Pack Enhancement
- [ ] 3.1 Implement partition budget system (System 5~10%, Long-term 10~15%, KG+Lore 15~25%, Recent ≥50%)
- [ ] 3.2 Implement overflow fallback (truncate low-priority Lore → compress Summary → shorten Recent)
- [ ] 3.3 Integrate Lorebook triggered entries into KG+Lore layer
- [ ] 3.4 Integrate KG facts (approved + auto_approved) into KG+Lore layer
- [ ] 3.5 Write tests for budget allocation and overflow scenarios

## 4. Consistency Check (Rule Engine)
- [ ] 4.1 Implement character status conflict detection (dead character appearing)
- [ ] 4.2 Implement timeline conflict detection (narrative_day field on KG Events)
- [ ] 4.3 Implement possession conflict detection (unique item owned by multiple)
- [ ] 4.4 Implement plot thread status conflict detection
- [ ] 4.5 Implement n-gram repetition detection
- [ ] 4.6 POST /api/qa/check (returns conflicts with type, severity, confidence=1.0, source=rule, evidence, suggest_fix)
- [ ] 4.7 Build conflict results panel (severity filter, evidence location)
- [ ] 4.8 Write tests for each conflict type

## 5. Word Count Control (Medium Constraint)
- [ ] 5.1 Implement scene target_chars budget allocation
- [ ] 5.2 Implement post-generation char count check
- [ ] 5.3 POST /api/generate/rewrite (expand/compress based on budget delta)
- [ ] 5.4 Write tests for budget check and rewrite triggering
