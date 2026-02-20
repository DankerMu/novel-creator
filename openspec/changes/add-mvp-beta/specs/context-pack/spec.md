## ADDED Requirements

### Requirement: Partition Budget System
The Context Pack SHALL allocate token budgets by layer: System (5~10%), Long-term (10~15%), KG+Lore (15~25%), Recent Text (≥50%). Unused budget SHALL flow back to Recent Text.

#### Scenario: Budget allocation with overflow
- **WHEN** KG+Lore layer uses only 10% of total context
- **THEN** the remaining 5~15% flows to Recent Text, giving it 55~65% effective budget

### Requirement: Overflow Degradation Strategy
When total context exceeds the model's limit, the system SHALL degrade in order: truncate low-priority Lore entries → compress Rolling Summary → shorten Recent Text.

#### Scenario: Graceful degradation
- **WHEN** total assembled context exceeds 32K tokens
- **THEN** low-priority Lore entries are removed first, then Rolling Summary is compressed, Recent Text shortened as last resort
