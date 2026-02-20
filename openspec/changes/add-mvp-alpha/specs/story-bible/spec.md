## ADDED Requirements

### Requirement: Bible Field Management
The system SHALL provide a Story Bible with configurable fields (Genre, Style, POV, Tense, Synopsis, Characters, World Rules, Outline, Scenes).
Each field SHALL support hand-written, AI-generated, or instruction-rewritten content.

#### Scenario: Edit and lock a Bible field
- **WHEN** user edits the Style field and toggles the locked switch ON
- **THEN** the Style field content is persisted and injected as a hard constraint in all subsequent AI generation prompts

### Requirement: Bible Context Injection
Locked Bible fields SHALL be automatically included in the system constraint layer of the Context Pack for all AI generation requests.

#### Scenario: Locked fields appear in generation context
- **WHEN** a scene generation request is made
- **THEN** all locked Bible fields are present in the system constraint section of the prompt
