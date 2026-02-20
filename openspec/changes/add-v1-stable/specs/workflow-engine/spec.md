## ADDED Requirements

### Requirement: JSON DAG Workflow Engine
The system SHALL provide a lightweight workflow engine that parses JSON DAG definitions, executes nodes in topologically sorted parallel layers via asyncio, and persists node-level state to workflow_node_runs.

#### Scenario: Execute chapter completion pipeline
- **WHEN** chapter_mark_done event fires
- **THEN** the chapter_complete_pipeline workflow executes: summarize → (extract_kg || update_lore) → qa_check, with each node status tracked

### Requirement: Handler Registration
Workflow handlers SHALL be registered via `@engine.register("handler_name")` decorator (whitelist pattern, no code injection risk).

#### Scenario: Register custom handler
- **WHEN** a new handler is decorated with @engine.register("my_handler")
- **THEN** it becomes available for use in JSON workflow definitions

### Requirement: Node-level Progress and Resume
The system SHALL report node-level progress via SSE and support checkpoint resume from the last completed node.

#### Scenario: Resume after failure
- **WHEN** a workflow fails at node 3 of 5
- **THEN** resuming the workflow starts from node 3, not from the beginning
