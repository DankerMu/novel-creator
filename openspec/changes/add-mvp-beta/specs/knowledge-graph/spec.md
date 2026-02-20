## ADDED Requirements

### Requirement: KG Extraction with Confidence
The system SHALL extract entities, events, and relations from completed chapters using a Schema-first prompt. Each extracted fact SHALL include a confidence score (0~1).

#### Scenario: Extract KG facts from chapter
- **WHEN** chapter is marked done
- **THEN** kg_proposals are created with entities, events, relations, each having confidence scores and evidence references

### Requirement: Confidence-Based Auto Approval
The system SHALL auto-approve High confidence (≥0.9) facts, auto-approve-pending Medium (0.6~0.9) facts, and queue Low (<0.6) facts for manual review.

#### Scenario: High confidence auto-approval
- **WHEN** a KG fact has confidence 0.95
- **THEN** it is automatically inserted into the graph with approval_status = auto_approved

#### Scenario: Low confidence queued
- **WHEN** a KG fact has confidence 0.3
- **THEN** it remains in pending queue and is NOT inserted into the graph

### Requirement: KG Batch Review UI
The system SHALL provide a batch review interface with: category grouping, confidence slider filter, bulk approve/reject, keyboard shortcuts (A/R/→), diff view, and evidence hover highlight.

#### Scenario: Bulk approve by category
- **WHEN** user clicks "Approve All" for the "Character Appearances" category
- **THEN** all auto_pending facts in that category are updated to user_approved

### Requirement: GraphService Abstraction
The system SHALL abstract graph operations behind a GraphService interface with SQLiteGraphAdapter (Lite) and Neo4jAdapter (Full) implementations.

#### Scenario: Switch from Lite to Full mode
- **WHEN** deployment profile changes from Lite to Full
- **THEN** GraphService uses Neo4jAdapter without changes to upper-layer code
