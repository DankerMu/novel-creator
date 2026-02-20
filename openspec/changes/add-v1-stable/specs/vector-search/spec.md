## ADDED Requirements

### Requirement: sqlite-vec Vector Search
The system SHALL integrate sqlite-vec extension for paragraph-level vector search, using BGE-small-zh local embedding model (~200 chars per chunk).

#### Scenario: Semantic recall of similar scene
- **WHEN** generating a new scene about "雨夜追逐"
- **THEN** vector search retrieves the most similar past paragraphs (even if keywords differ) and injects them into the Context Pack supplementary layer (5~8% budget)
