## ADDED Requirements

### Requirement: Project CRUD
The system SHALL provide full CRUD operations for Projects, Books, Chapters, and Scenes.
Each Scene SHALL support multiple text versions (scene_text_versions) with char_count tracking.

#### Scenario: Create project with nested structure
- **WHEN** user creates a new project and adds a book, chapter, and scene
- **THEN** all entities are persisted in SQLite with correct parent-child relationships

#### Scenario: Scene version management
- **WHEN** user saves a scene edit
- **THEN** a new scene_text_version is created with incremented version number and accurate char_count

### Requirement: Project Tree Navigation
The frontend SHALL display a hierarchical project tree (Book → Chapter → Scene) in the left sidebar.
Users SHALL be able to select any scene to load its content in the center editor.

#### Scenario: Navigate to scene
- **WHEN** user clicks a scene in the project tree
- **THEN** the scene's latest text version loads in the center editor panel
