## ADDED Requirements

### Requirement: Lorebook Entry Management
The system SHALL provide CRUD operations for Lorebook entries with fields: type (Character/Location/Item/Concept/Rule/Organization/Event), title, aliases, content_md, secrets_md, triggers (keywords, and_keywords), priority, locked.

#### Scenario: Create and trigger a Lorebook entry
- **WHEN** user creates a Lorebook entry for character "张三" with aliases ["小张"] and keywords ["张三", "小张"]
- **AND** the current scene text contains "张三"
- **THEN** the entry's content_md is injected into the Context Pack's KG+Lore layer

### Requirement: Lorebook Budget Truncation
The system SHALL enforce a token budget for Lorebook injection (shared with KG, max 15~25% of total context). When budget is exceeded, entries SHALL be truncated by priority DESC, then by Bottom trim to sentence granularity.

#### Scenario: Budget overflow truncation
- **WHEN** 10 Lorebook entries are triggered but total tokens exceed budget
- **THEN** lowest priority entries are truncated from bottom first, and entries with remaining tokens < reserved are removed entirely

### Requirement: Lorebook Import/Export
The system SHALL support importing and exporting Lorebook entries in SillyTavern-compatible JSON format.

#### Scenario: Import SillyTavern JSON
- **WHEN** user uploads a SillyTavern World Info JSON file
- **THEN** all entries are imported with correct field mapping (keys → triggers.keywords, uid → ignored)
