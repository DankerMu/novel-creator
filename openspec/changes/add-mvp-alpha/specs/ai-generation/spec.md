## ADDED Requirements

### Requirement: Structured Scene Card Generation
The system SHALL generate scene cards as structured JSON validated against a Pydantic SceneCard model using Instructor.
The SceneCard model SHALL include: title, location, time, characters, conflict, turning_point, reveal, target_chars.

#### Scenario: Generate valid scene card
- **WHEN** user requests scene card generation with chapter context
- **THEN** the API returns a SceneCard JSON object that passes Pydantic validation

#### Scenario: Auto-retry on schema validation failure
- **WHEN** LLM output fails SceneCard validation
- **THEN** the system retries up to 3 times with error feedback before returning an error

### Requirement: Streaming Scene Draft Generation
The system SHALL generate scene prose via FastAPI SSE (Server-Sent Events) streaming.
Each SSE event SHALL contain a text chunk. The final event SHALL include a validation summary (char_count, characters_present).

#### Scenario: Stream scene draft to frontend
- **WHEN** user triggers scene draft generation
- **THEN** text appears progressively in the editor via SSE, and the final event contains char_count

### Requirement: Basic Context Pack Assembly
The system SHALL assemble a Context Pack containing: locked Bible fields (system layer) + chapter summaries (long-term layer) + last N paragraphs of current scene (short-term layer).

#### Scenario: Context Pack includes Bible and recent text
- **WHEN** a generation request is assembled
- **THEN** the Context Pack contains all locked Bible fields and the last 3 paragraphs of the current scene
