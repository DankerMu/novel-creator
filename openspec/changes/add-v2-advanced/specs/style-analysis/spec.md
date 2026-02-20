## ADDED Requirements

### Requirement: Style Fingerprint
The system SHALL automatically compute a style fingerprint from written chapters: sentence length distribution, punctuation density, dialogue ratio, connector word preferences.

#### Scenario: Generate style deviation report
- **WHEN** a new chapter is completed
- **THEN** a deviation report compares the chapter's style metrics to the rolling fingerprint, highlighting significant shifts
