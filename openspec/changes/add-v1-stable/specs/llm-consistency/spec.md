## ADDED Requirements

### Requirement: LLM Setting Contradiction Detection
The system SHALL use LLM reasoning to detect semantic contradictions between prose and Bible/Lore entries. Results SHALL include confidence (0~1) and source=llm.

#### Scenario: Detect character trait contradiction
- **WHEN** Lore says character "恐高" but prose describes them "在悬崖边毫不畏惧"
- **THEN** a conflict is reported with type=setting_contradiction, severity=medium, confidence=0.8, with evidence from both Lore and prose

### Requirement: POV Drift Detection
The system SHALL detect point-of-view drift using semi-rule (third-person markers in first-person text) plus LLM confirmation.

#### Scenario: Detect POV switch
- **WHEN** Bible sets POV=first_person but a paragraph contains "他心想"
- **THEN** a conflict is reported with type=pov_drift, severity=medium
