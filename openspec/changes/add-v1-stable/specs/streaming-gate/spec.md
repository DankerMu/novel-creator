## ADDED Requirements

### Requirement: Streaming Gate Word Count Control
The system SHALL support strong word count control via streaming gate: soft_limit (N×0.9) triggers boundary seeking, hard_limit (N×1.1) forces cut. Boundary detection uses Chinese sentence-ending punctuation regex.

#### Scenario: Interrupt at sentence boundary
- **WHEN** streaming output reaches soft_limit
- **THEN** generation continues until the next sentence-ending punctuation (。？！), then pauses for continuation

#### Scenario: Multi-round continuation
- **WHEN** remaining chars > 0 after first round
- **THEN** a continuation prompt is sent with last 2-3 paragraphs as context, up to max 3 rounds
