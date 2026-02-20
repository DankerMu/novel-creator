## ADDED Requirements

### Requirement: Scene Budget Word Count Control
The system SHALL support medium-constraint word count control: each scene has a target_chars budget; after generation, the system checks actual char count and offers expand/compress if deviation exceeds ±15%.

#### Scenario: Auto-suggest compression
- **WHEN** generated scene has 1200 chars but target is 800 (50% over)
- **THEN** the system suggests compression and provides a one-click compress API call
