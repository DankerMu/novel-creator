## ADDED Requirements

### Requirement: Prompt Template Versioning
The system SHALL provide a Prompt Workshop for managing prompt templates with group, key, template_md, version, and enabled fields.

#### Scenario: Switch active prompt version
- **WHEN** user selects version 3 of the "scene_generation" prompt template
- **THEN** all subsequent scene generation requests use version 3's template
