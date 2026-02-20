## ADDED Requirements

### Requirement: Scene Versioning
The system SHALL create a new version record for each scene save, with version number, content, char_count, and timestamp.

#### Scenario: View version history
- **WHEN** user opens version history for a scene
- **THEN** all versions are listed with timestamps, and diff between any two versions is available

### Requirement: Chapter Snapshots
The system SHALL auto-create a snapshot when a chapter is marked done, capturing all scene versions at that point.

#### Scenario: Rollback to snapshot
- **WHEN** user selects a previous chapter snapshot and confirms rollback
- **THEN** all scenes revert to their versions at snapshot time

### Requirement: Named Checkpoints
Users SHALL be able to manually create named checkpoints at any point, preserving the full project state.

#### Scenario: Create and restore checkpoint
- **WHEN** user creates checkpoint named "Act 2 Complete"
- **THEN** the checkpoint is saved and can be restored later, reverting all data to that state
