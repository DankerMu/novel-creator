## ADDED Requirements

### Requirement: Lore Auto-Maintenance Agent
The system SHALL provide an autonomous agent that monitors chapter completions and proposes Lorebook entry updates (new entries, modifications, deprecations).

#### Scenario: Agent suggests new Lore entry
- **WHEN** a new character appears in chapter 15 that has no Lorebook entry
- **THEN** the agent proposes a new Lorebook entry with extracted details, pending user approval
