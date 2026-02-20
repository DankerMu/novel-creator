## ADDED Requirements

### Requirement: Rule Engine Consistency Check
The system SHALL detect 4 types of structural conflicts using rule-based queries against KG data: character status conflicts, timeline conflicts, possession conflicts, and plot thread status conflicts. Each result SHALL have confidence=1.0 and source=rule.

#### Scenario: Detect dead character appearing
- **WHEN** KG records character.status='dead' but character APPEARS_IN a later chapter
- **THEN** a conflict is reported with type=character_status, severity=high, evidence pointing to both the death scene and the reappearance

### Requirement: N-gram Repetition Detection
The system SHALL detect excessive word/phrase repetition using n-gram frequency analysis on generated text.

#### Scenario: Flag repeated phrase
- **WHEN** a 4-gram appears more than 3 times in a single scene
- **THEN** a warning is reported with type=repetition, severity=low, evidence highlighting each occurrence
